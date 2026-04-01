"""Synchronous httpx client wrapping the Resend REST API.

All methods are synchronous — the server bridges to async via ``asyncio.to_thread()``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from resend_blade_mcp.models import (
    BASE_URL,
    DEFAULT_LIMIT,
    MAX_BATCH_SIZE,
    USER_AGENT,
    scrub_secrets,
    validate_attachment,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class ResendError(Exception):
    """Base exception for Resend API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthError(ResendError):
    """Authentication or authorisation failure (401/403)."""


class NotFoundError(ResendError):
    """Resource not found (404)."""


class ValidationError(ResendError):
    """Invalid request parameters (422/400)."""


class RateLimitError(ResendError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ConnectionError(ResendError):  # noqa: A001
    """Network connectivity failure."""


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


def _classify_http_error(status_code: int, body: dict[str, Any], retry_after: float | None = None) -> ResendError:
    """Map HTTP status codes to typed exceptions."""
    message = body.get("message", "") or body.get("error", "") or f"HTTP {status_code}"
    message = scrub_secrets(str(message))

    if status_code in (401, 403):
        return AuthError(message, status_code=status_code)
    if status_code == 404:
        return NotFoundError(message, status_code=status_code)
    if status_code == 429:
        return RateLimitError(message, retry_after=retry_after)
    if status_code in (400, 422):
        return ValidationError(message, status_code=status_code)
    return ResendError(message, status_code=status_code)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class ResendClient:
    """Synchronous client for the Resend REST API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("RESEND_API_KEY", "")
        if not self._api_key:
            raise AuthError("RESEND_API_KEY not set. Provide via env var or constructor.")

        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=httpx.Timeout(30.0),
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    # -------------------------------------------------------------------
    # Internal request helper
    # -------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Execute an HTTP request and return parsed JSON."""
        try:
            kwargs: dict[str, Any] = {}
            if json_body is not None:
                kwargs["json"] = json_body
            if params:
                kwargs["params"] = {k: v for k, v in params.items() if v is not None}

            headers = dict(extra_headers) if extra_headers else {}
            if headers:
                kwargs["headers"] = headers

            resp = self._http.request(method, path, **kwargs)
        except httpx.ConnectError as e:
            raise ConnectionError(scrub_secrets(f"Connection failed: {e}")) from e
        except httpx.TimeoutException as e:
            raise ConnectionError(scrub_secrets(f"Request timed out: {e}")) from e

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = {"message": resp.text[:500]}
            retry_after = None
            if resp.status_code == 429:
                ra = resp.headers.get("retry-after")
                if ra:
                    try:
                        retry_after = float(ra)
                    except ValueError:
                        pass
            raise _classify_http_error(resp.status_code, body, retry_after)

        if resp.status_code == 204 or not resp.content:
            return {}

        return resp.json()  # type: ignore[no-any-return]

    # ===================================================================
    # SENDING
    # ===================================================================

    def send_email(
        self,
        *,
        from_addr: str,
        to: list[str],
        subject: str,
        html: str | None = None,
        text: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: list[str] | None = None,
        attachments: list[dict[str, str]] | None = None,
        tags: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
        scheduled_at: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Send a single email. POST /emails."""
        # Validate attachments
        if attachments:
            for att in attachments:
                err = validate_attachment(att)
                if err:
                    raise ValidationError(err)

        body: dict[str, Any] = {"from": from_addr, "to": to, "subject": subject}
        if html is not None:
            body["html"] = html
        if text is not None:
            body["text"] = text
        if cc:
            body["cc"] = cc
        if bcc:
            body["bcc"] = bcc
        if reply_to:
            body["reply_to"] = reply_to
        if attachments:
            body["attachments"] = attachments
        if tags:
            body["tags"] = tags
        if headers:
            body["headers"] = headers
        if scheduled_at:
            body["scheduled_at"] = scheduled_at

        extra: dict[str, str] = {}
        if idempotency_key:
            extra["Idempotency-Key"] = idempotency_key

        result = self._request("POST", "/emails", json_body=body, extra_headers=extra or None)
        return result  # type: ignore[return-value]

    def send_batch(
        self,
        *,
        emails: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Send a batch of emails (max 100). POST /emails/batch."""
        if len(emails) > MAX_BATCH_SIZE:
            raise ValidationError(f"Batch size {len(emails)} exceeds maximum {MAX_BATCH_SIZE}.")

        for email in emails:
            if "attachments" in email:
                for att in email["attachments"]:
                    err = validate_attachment(att)
                    if err:
                        raise ValidationError(err)

        extra: dict[str, str] = {}
        if idempotency_key:
            extra["Idempotency-Key"] = idempotency_key

        result = self._request("POST", "/emails/batch", json_body=emails, extra_headers=extra or None)
        return result  # type: ignore[return-value]

    def get_email(self, email_id: str) -> dict[str, Any]:
        """Retrieve a sent email by ID. GET /emails/{id}."""
        result = self._request("GET", f"/emails/{email_id}")
        return result  # type: ignore[return-value]

    def list_emails(self, *, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
        """List sent emails. GET /emails."""
        result = self._request("GET", "/emails", params={"limit": limit})
        return result  # type: ignore[return-value]

    def cancel_scheduled(self, email_id: str) -> dict[str, Any]:
        """Cancel a scheduled email. POST /emails/{id}/cancel."""
        result = self._request("POST", f"/emails/{email_id}/cancel")
        return result  # type: ignore[return-value]

    # ===================================================================
    # CONTACTS
    # ===================================================================

    def create_contact(
        self,
        *,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        unsubscribed: bool | None = None,
    ) -> dict[str, Any]:
        """Create a contact. POST /contacts."""
        body: dict[str, Any] = {"email": email}
        if first_name is not None:
            body["first_name"] = first_name
        if last_name is not None:
            body["last_name"] = last_name
        if unsubscribed is not None:
            body["unsubscribed"] = unsubscribed
        result = self._request("POST", "/contacts", json_body=body)
        return result  # type: ignore[return-value]

    def list_contacts(self, *, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
        """List contacts. GET /contacts."""
        result = self._request("GET", "/contacts", params={"limit": limit})
        return result  # type: ignore[return-value]

    def get_contact(self, contact_id: str) -> dict[str, Any]:
        """Retrieve a contact. GET /contacts/{id}."""
        result = self._request("GET", f"/contacts/{contact_id}")
        return result  # type: ignore[return-value]

    def update_contact(
        self,
        contact_id: str,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        unsubscribed: bool | None = None,
    ) -> dict[str, Any]:
        """Update a contact. PATCH /contacts/{id}."""
        body: dict[str, Any] = {}
        if first_name is not None:
            body["first_name"] = first_name
        if last_name is not None:
            body["last_name"] = last_name
        if unsubscribed is not None:
            body["unsubscribed"] = unsubscribed
        result = self._request("PATCH", f"/contacts/{contact_id}", json_body=body)
        return result  # type: ignore[return-value]

    def delete_contact(self, contact_id: str) -> dict[str, Any]:
        """Delete a contact. DELETE /contacts/{id}."""
        result = self._request("DELETE", f"/contacts/{contact_id}")
        return result  # type: ignore[return-value]

    # ===================================================================
    # SEGMENTS
    # ===================================================================

    def create_segment(self, *, name: str) -> dict[str, Any]:
        """Create a segment. POST /segments."""
        result = self._request("POST", "/segments", json_body={"name": name})
        return result  # type: ignore[return-value]

    def list_segments(self) -> dict[str, Any]:
        """List segments. GET /segments."""
        result = self._request("GET", "/segments")
        return result  # type: ignore[return-value]

    def delete_segment(self, segment_id: str) -> dict[str, Any]:
        """Delete a segment. DELETE /segments/{id}."""
        result = self._request("DELETE", f"/segments/{segment_id}")
        return result  # type: ignore[return-value]

    # ===================================================================
    # BROADCASTS
    # ===================================================================

    def create_broadcast(
        self,
        *,
        segment_id: str,
        from_addr: str,
        subject: str,
        html: str | None = None,
        text: str | None = None,
        name: str | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Create a broadcast. POST /broadcasts."""
        body: dict[str, Any] = {"segmentId": segment_id, "from": from_addr, "subject": subject}
        if html is not None:
            body["html"] = html
        if text is not None:
            body["text"] = text
        if name is not None:
            body["name"] = name
        if reply_to is not None:
            body["reply_to"] = reply_to
        result = self._request("POST", "/broadcasts", json_body=body)
        return result  # type: ignore[return-value]

    def send_broadcast(self, broadcast_id: str, *, scheduled_at: str | None = None) -> dict[str, Any]:
        """Send a draft broadcast. POST /broadcasts/{id}/send."""
        body: dict[str, Any] = {}
        if scheduled_at:
            body["scheduledAt"] = scheduled_at
        result = self._request("POST", f"/broadcasts/{broadcast_id}/send", json_body=body or None)
        return result  # type: ignore[return-value]

    def list_broadcasts(self) -> dict[str, Any]:
        """List broadcasts. GET /broadcasts."""
        result = self._request("GET", "/broadcasts")
        return result  # type: ignore[return-value]

    def delete_broadcast(self, broadcast_id: str) -> dict[str, Any]:
        """Delete a draft/scheduled broadcast. DELETE /broadcasts/{id}."""
        result = self._request("DELETE", f"/broadcasts/{broadcast_id}")
        return result  # type: ignore[return-value]

    # ===================================================================
    # TEMPLATES
    # ===================================================================

    def create_template(
        self,
        *,
        name: str,
        subject: str,
        html: str,
    ) -> dict[str, Any]:
        """Create a template. POST /templates."""
        body: dict[str, Any] = {"name": name, "subject": subject, "html": html}
        result = self._request("POST", "/templates", json_body=body)
        return result  # type: ignore[return-value]

    def list_templates(self) -> dict[str, Any]:
        """List templates. GET /templates."""
        result = self._request("GET", "/templates")
        return result  # type: ignore[return-value]

    def get_template(self, template_id: str) -> dict[str, Any]:
        """Retrieve a template. GET /templates/{id}."""
        result = self._request("GET", f"/templates/{template_id}")
        return result  # type: ignore[return-value]

    def publish_template(self, template_id: str) -> dict[str, Any]:
        """Publish a template for use. POST /templates/{id}/publish."""
        result = self._request("POST", f"/templates/{template_id}/publish")
        return result  # type: ignore[return-value]

    # ===================================================================
    # DOMAINS
    # ===================================================================

    def add_domain(self, *, name: str, region: str | None = None) -> dict[str, Any]:
        """Register a sending domain. POST /domains."""
        body: dict[str, Any] = {"name": name}
        if region:
            body["region"] = region
        result = self._request("POST", "/domains", json_body=body)
        return result  # type: ignore[return-value]

    def list_domains(self) -> dict[str, Any]:
        """List domains. GET /domains."""
        result = self._request("GET", "/domains")
        return result  # type: ignore[return-value]

    def get_domain(self, domain_id: str) -> dict[str, Any]:
        """Retrieve a domain with DNS records. GET /domains/{id}."""
        result = self._request("GET", f"/domains/{domain_id}")
        return result  # type: ignore[return-value]

    def verify_domain(self, domain_id: str) -> dict[str, Any]:
        """Trigger domain verification. POST /domains/{id}/verify."""
        result = self._request("POST", f"/domains/{domain_id}/verify")
        return result  # type: ignore[return-value]

    # ===================================================================
    # WEBHOOKS
    # ===================================================================

    def create_webhook(self, *, endpoint_url: str, events: list[str]) -> dict[str, Any]:
        """Create a webhook. POST /webhooks."""
        body: dict[str, Any] = {"endpoint": endpoint_url, "events": events}
        result = self._request("POST", "/webhooks", json_body=body)
        return result  # type: ignore[return-value]

    def list_webhooks(self) -> dict[str, Any]:
        """List webhooks. GET /webhooks."""
        result = self._request("GET", "/webhooks")
        return result  # type: ignore[return-value]

    def delete_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Delete a webhook. DELETE /webhooks/{id}."""
        result = self._request("DELETE", f"/webhooks/{webhook_id}")
        return result  # type: ignore[return-value]

    # ===================================================================
    # LOGS
    # ===================================================================

    def list_logs(self, *, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
        """List API request logs. GET /logs."""
        result = self._request("GET", "/logs", params={"limit": limit})
        return result  # type: ignore[return-value]
