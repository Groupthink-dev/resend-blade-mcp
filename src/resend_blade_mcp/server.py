"""Resend Blade MCP server — 28 tools for transactional email operations.

Write operations require ``RESEND_WRITE_ENABLED=true``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from resend_blade_mcp.client import ResendClient, ResendError
from resend_blade_mcp.formatters import (
    format_batch_result,
    format_broadcast_list,
    format_broadcast_result,
    format_cancel_result,
    format_contact_list,
    format_contact_result,
    format_domain,
    format_domain_list,
    format_domain_result,
    format_email,
    format_email_list,
    format_log_list,
    format_segment_list,
    format_segment_result,
    format_send_result,
    format_template_detail,
    format_template_list,
    format_template_result,
    format_webhook_list,
    format_webhook_result,
)
from resend_blade_mcp.models import DEFAULT_LIMIT, require_write

logger = logging.getLogger(__name__)

# Transport config from env
TRANSPORT = os.environ.get("RESEND_MCP_TRANSPORT", "stdio")
HTTP_HOST = os.environ.get("RESEND_MCP_HOST", "127.0.0.1")
HTTP_PORT = int(os.environ.get("RESEND_MCP_PORT", "8770"))

mcp = FastMCP(
    "ResendBlade",
    instructions=(
        "Resend transactional email operations — send, manage contacts, broadcasts, templates, domains, webhooks. "
        "Write operations require RESEND_WRITE_ENABLED=true."
    ),
)

# Lazy singleton
_client: ResendClient | None = None


def _get_client() -> ResendClient:
    """Get or create the ResendClient singleton."""
    global _client
    if _client is None:
        _client = ResendClient()
        logger.info("ResendClient initialised")
    return _client


def _error_response(e: ResendError) -> str:
    """Format a ResendError as a tool response string."""
    return f"Error: {e}"


async def _run(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a blocking client method in a thread."""
    return await asyncio.to_thread(fn, *args, **kwargs)


# ===================================================================
# SENDING
# ===================================================================


@mcp.tool
async def resend_send(
    from_addr: Annotated[str, Field(description="Sender email (e.g. 'Name <user@example.com>')")],
    to: Annotated[str, Field(description="Recipient(s), comma-separated")],
    subject: Annotated[str, Field(description="Email subject line")],
    html: Annotated[str | None, Field(description="HTML body")] = None,
    text: Annotated[str | None, Field(description="Plain text body")] = None,
    cc: Annotated[str | None, Field(description="CC recipients, comma-separated")] = None,
    bcc: Annotated[str | None, Field(description="BCC recipients, comma-separated")] = None,
    reply_to: Annotated[str | None, Field(description="Reply-to address(es), comma-separated")] = None,
    attachments_json: Annotated[
        str | None,
        Field(
            description=(
                'JSON array of attachments. Each: {"content": "<base64>", "filename": "name.pdf"} '
                'or {"path": "https://url", "filename": "name.pdf"}. '
                "Filesystem paths are NOT allowed."
            )
        ),
    ] = None,
    tags_json: Annotated[
        str | None, Field(description='JSON array of tags. Each: {"name": "key", "value": "val"}')
    ] = None,
    scheduled_at: Annotated[
        str | None, Field(description="ISO 8601 datetime to schedule (e.g. '2026-04-02T10:00:00Z')")
    ] = None,
    idempotency_key: Annotated[
        str | None, Field(description="Unique key to prevent duplicate sends on retry (max 256 chars, 24h expiry)")
    ] = None,
) -> str:
    """Send a transactional email via Resend. Requires RESEND_WRITE_ENABLED=true.

    Use ``resend_list_domains`` to verify your sending domain is verified.
    Supports scheduled sending via ``scheduled_at`` and idempotent retries via ``idempotency_key``.
    """
    if err := require_write():
        return err
    try:
        attachments = json.loads(attachments_json) if attachments_json else None
        tags = json.loads(tags_json) if tags_json else None
        result = await _run(
            _get_client().send_email,
            from_addr=from_addr,
            to=[addr.strip() for addr in to.split(",")],
            subject=subject,
            html=html,
            text=text,
            cc=[addr.strip() for addr in cc.split(",")] if cc else None,
            bcc=[addr.strip() for addr in bcc.split(",")] if bcc else None,
            reply_to=[addr.strip() for addr in reply_to.split(",")] if reply_to else None,
            attachments=attachments,
            tags=tags,
            scheduled_at=scheduled_at,
            idempotency_key=idempotency_key,
        )
        return format_send_result(result)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in attachments or tags — {e}"
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_send")
        return f"Error: {e}"


@mcp.tool
async def resend_send_batch(
    emails_json: Annotated[
        str,
        Field(
            description=(
                "JSON array of email objects (max 100). Each: "
                '{"from": "...", "to": ["..."], "subject": "...", "html": "..."}'
            )
        ),
    ],
    idempotency_key: Annotated[str | None, Field(description="Unique key to prevent duplicate batch")] = None,
) -> str:
    """Send a batch of up to 100 emails. Requires RESEND_WRITE_ENABLED=true.

    More efficient than individual sends for bulk transactional email.
    Attachments and scheduled_at are NOT supported in batch mode.
    """
    if err := require_write():
        return err
    try:
        emails = json.loads(emails_json)
        if not isinstance(emails, list):
            return "Error: emails_json must be a JSON array."
        result = await _run(_get_client().send_batch, emails=emails, idempotency_key=idempotency_key)
        return format_batch_result(result)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON — {e}"
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_send_batch")
        return f"Error: {e}"


@mcp.tool
async def resend_get_email(
    email_id: Annotated[str, Field(description="Email ID to retrieve")],
) -> str:
    """Retrieve a sent email by ID. Returns headers, status, and body."""
    try:
        result = await _run(_get_client().get_email, email_id)
        return format_email(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_get_email")
        return f"Error: {e}"


@mcp.tool
async def resend_list_emails(
    limit: Annotated[int, Field(description="Max results to return")] = DEFAULT_LIMIT,
) -> str:
    """List sent emails. Returns: date | from | subject | status | id."""
    try:
        result = await _run(_get_client().list_emails, limit=limit)
        data = result.get("data", []) if isinstance(result, dict) else result
        return format_email_list(data, limit=limit)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_list_emails")
        return f"Error: {e}"


@mcp.tool
async def resend_cancel_scheduled(
    email_id: Annotated[str, Field(description="ID of the scheduled email to cancel")],
) -> str:
    """Cancel a scheduled email before it sends. Requires RESEND_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().cancel_scheduled, email_id)
        return format_cancel_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_cancel_scheduled")
        return f"Error: {e}"


# ===================================================================
# CONTACTS
# ===================================================================


@mcp.tool
async def resend_create_contact(
    email: Annotated[str, Field(description="Contact email address")],
    first_name: Annotated[str | None, Field(description="First name")] = None,
    last_name: Annotated[str | None, Field(description="Last name")] = None,
    unsubscribed: Annotated[bool | None, Field(description="Global unsubscribe status")] = None,
) -> str:
    """Create a contact. Requires RESEND_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        result = await _run(
            _get_client().create_contact,
            email=email,
            first_name=first_name,
            last_name=last_name,
            unsubscribed=unsubscribed,
        )
        return format_contact_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_create_contact")
        return f"Error: {e}"


@mcp.tool
async def resend_list_contacts(
    limit: Annotated[int, Field(description="Max results")] = DEFAULT_LIMIT,
) -> str:
    """List contacts. Returns: email | name | status | id."""
    try:
        result = await _run(_get_client().list_contacts, limit=limit)
        data = result.get("data", []) if isinstance(result, dict) else result
        return format_contact_list(data, limit=limit)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_list_contacts")
        return f"Error: {e}"


@mcp.tool
async def resend_update_contact(
    contact_id: Annotated[str, Field(description="Contact ID to update")],
    first_name: Annotated[str | None, Field(description="New first name")] = None,
    last_name: Annotated[str | None, Field(description="New last name")] = None,
    unsubscribed: Annotated[bool | None, Field(description="Set unsubscribe status")] = None,
) -> str:
    """Update a contact's properties. Requires RESEND_WRITE_ENABLED=true.

    Use ``resend_list_contacts`` to find contact IDs.
    """
    if err := require_write():
        return err
    try:
        result = await _run(
            _get_client().update_contact,
            contact_id,
            first_name=first_name,
            last_name=last_name,
            unsubscribed=unsubscribed,
        )
        return format_contact_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_update_contact")
        return f"Error: {e}"


@mcp.tool
async def resend_delete_contact(
    contact_id: Annotated[str, Field(description="Contact ID to delete")],
) -> str:
    """Delete a contact. Requires RESEND_WRITE_ENABLED=true.

    Use ``resend_list_contacts`` to find contact IDs.
    """
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().delete_contact, contact_id)
        return format_contact_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_delete_contact")
        return f"Error: {e}"


# ===================================================================
# SEGMENTS
# ===================================================================


@mcp.tool
async def resend_create_segment(
    name: Annotated[str, Field(description="Segment name")],
) -> str:
    """Create a segment for organising contacts. Requires RESEND_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().create_segment, name=name)
        return format_segment_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_create_segment")
        return f"Error: {e}"


@mcp.tool
async def resend_list_segments() -> str:
    """List all segments. Returns: name | id | created."""
    try:
        result = await _run(_get_client().list_segments)
        data = result.get("data", []) if isinstance(result, dict) else result
        return format_segment_list(data)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_list_segments")
        return f"Error: {e}"


@mcp.tool
async def resend_delete_segment(
    segment_id: Annotated[str, Field(description="Segment ID to delete")],
) -> str:
    """Delete a segment. Requires RESEND_WRITE_ENABLED=true.

    Use ``resend_list_segments`` to find segment IDs.
    """
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().delete_segment, segment_id)
        return format_segment_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_delete_segment")
        return f"Error: {e}"


# ===================================================================
# BROADCASTS
# ===================================================================


@mcp.tool
async def resend_create_broadcast(
    segment_id: Annotated[str, Field(description="Target segment ID (use resend_list_segments)")],
    from_addr: Annotated[str, Field(description="Sender email address")],
    subject: Annotated[str, Field(description="Broadcast subject line")],
    html: Annotated[str | None, Field(description="HTML body")] = None,
    text: Annotated[str | None, Field(description="Plain text body")] = None,
    name: Annotated[str | None, Field(description="Internal reference name")] = None,
    reply_to: Annotated[str | None, Field(description="Reply-to address")] = None,
) -> str:
    """Create a broadcast (draft). Requires RESEND_WRITE_ENABLED=true.

    Use ``resend_send_broadcast`` to send it, or pass ``scheduled_at`` there to schedule.
    """
    if err := require_write():
        return err
    try:
        result = await _run(
            _get_client().create_broadcast,
            segment_id=segment_id,
            from_addr=from_addr,
            subject=subject,
            html=html,
            text=text,
            name=name,
            reply_to=reply_to,
        )
        return format_broadcast_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_create_broadcast")
        return f"Error: {e}"


@mcp.tool
async def resend_send_broadcast(
    broadcast_id: Annotated[str, Field(description="Broadcast ID to send")],
    scheduled_at: Annotated[
        str | None, Field(description="ISO 8601 datetime to schedule instead of sending immediately")
    ] = None,
) -> str:
    """Send a draft broadcast immediately or schedule it. Requires RESEND_WRITE_ENABLED=true.

    Use ``resend_list_broadcasts`` to find draft broadcast IDs.
    """
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().send_broadcast, broadcast_id, scheduled_at=scheduled_at)
        return format_broadcast_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_send_broadcast")
        return f"Error: {e}"


@mcp.tool
async def resend_list_broadcasts() -> str:
    """List broadcasts with status. Returns: name | subject | status | date | id."""
    try:
        result = await _run(_get_client().list_broadcasts)
        data = result.get("data", []) if isinstance(result, dict) else result
        return format_broadcast_list(data)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_list_broadcasts")
        return f"Error: {e}"


@mcp.tool
async def resend_delete_broadcast(
    broadcast_id: Annotated[str, Field(description="Broadcast ID to delete (draft or scheduled only)")],
) -> str:
    """Delete a draft or scheduled broadcast. Requires RESEND_WRITE_ENABLED=true."""
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().delete_broadcast, broadcast_id)
        return format_broadcast_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_delete_broadcast")
        return f"Error: {e}"


# ===================================================================
# TEMPLATES
# ===================================================================


@mcp.tool
async def resend_create_template(
    name: Annotated[str, Field(description="Template name")],
    subject: Annotated[str, Field(description="Default subject (can use {{{VARIABLE}}} placeholders)")],
    html: Annotated[str, Field(description="HTML content with {{{VARIABLE}}} placeholders")],
) -> str:
    """Create an email template. Requires RESEND_WRITE_ENABLED=true.

    Use ``resend_publish_template`` to make it available for sending.
    Template variables use triple braces: ``{{{FIRST_NAME}}}`` with optional fallback ``{{{FIRST_NAME|friend}}}``.
    """
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().create_template, name=name, subject=subject, html=html)
        return format_template_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_create_template")
        return f"Error: {e}"


@mcp.tool
async def resend_list_templates() -> str:
    """List templates. Returns: name | subject | status | id."""
    try:
        result = await _run(_get_client().list_templates)
        data = result.get("data", []) if isinstance(result, dict) else result
        return format_template_list(data)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_list_templates")
        return f"Error: {e}"


@mcp.tool
async def resend_get_template(
    template_id: Annotated[str, Field(description="Template ID (or alias)")],
) -> str:
    """Retrieve a template with its HTML content.

    Use ``resend_list_templates`` to find template IDs.
    """
    try:
        result = await _run(_get_client().get_template, template_id)
        return format_template_detail(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_get_template")
        return f"Error: {e}"


@mcp.tool
async def resend_publish_template(
    template_id: Annotated[str, Field(description="Template ID to publish")],
) -> str:
    """Publish a template so it can be used in email sends. Requires RESEND_WRITE_ENABLED=true.

    Templates must be published before they can be referenced via ``template`` in ``resend_send``.
    """
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().publish_template, template_id)
        return format_template_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_publish_template")
        return f"Error: {e}"


# ===================================================================
# DOMAINS
# ===================================================================


@mcp.tool
async def resend_add_domain(
    name: Annotated[str, Field(description="Domain name (e.g. 'example.com')")],
    region: Annotated[
        str | None,
        Field(description="AWS region: us-east-1 (default), eu-west-1, sa-east-1, ap-northeast-1"),
    ] = None,
) -> str:
    """Register a sending domain. Requires RESEND_WRITE_ENABLED=true.

    Returns DNS records (SPF, DKIM) that must be added to your DNS provider.
    Use ``resend_verify_domain`` after adding records.
    """
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().add_domain, name=name, region=region)
        return format_domain_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_add_domain")
        return f"Error: {e}"


@mcp.tool
async def resend_list_domains() -> str:
    """List sending domains with verification status. Returns: name | status | region | id."""
    try:
        result = await _run(_get_client().list_domains)
        data = result.get("data", []) if isinstance(result, dict) else result
        return format_domain_list(data)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_list_domains")
        return f"Error: {e}"


@mcp.tool
async def resend_get_domain(
    domain_id: Annotated[str, Field(description="Domain ID to retrieve")],
) -> str:
    """Retrieve a domain with its DNS records and verification status.

    Use ``resend_list_domains`` to find domain IDs.
    """
    try:
        result = await _run(_get_client().get_domain, domain_id)
        return format_domain(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_get_domain")
        return f"Error: {e}"


@mcp.tool
async def resend_verify_domain(
    domain_id: Annotated[str, Field(description="Domain ID to verify")],
) -> str:
    """Trigger DNS verification for a domain. Requires RESEND_WRITE_ENABLED=true.

    Run this after adding SPF/DKIM records to your DNS provider.
    Use ``resend_get_domain`` to check current record status.
    """
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().verify_domain, domain_id)
        return format_domain_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_verify_domain")
        return f"Error: {e}"


# ===================================================================
# WEBHOOKS
# ===================================================================


@mcp.tool
async def resend_create_webhook(
    endpoint_url: Annotated[str, Field(description="HTTPS URL to receive webhook events")],
    events: Annotated[
        str,
        Field(
            description=(
                "Comma-separated event types. Available: "
                "email.sent, email.delivered, email.bounced, email.complained, "
                "email.delivery_delayed, email.failed, email.opened, email.clicked, "
                "email.received, email.scheduled, email.suppressed, "
                "domain.created, domain.updated, domain.deleted, "
                "contact.created, contact.updated, contact.deleted"
            )
        ),
    ],
) -> str:
    """Create a webhook endpoint. Requires RESEND_WRITE_ENABLED=true.

    Returns a signing secret (``whsec_...``) for verifying webhook payloads — save it immediately,
    it is only shown once. Use Svix for signature verification.
    """
    if err := require_write():
        return err
    try:
        event_list = [e.strip() for e in events.split(",")]
        result = await _run(_get_client().create_webhook, endpoint_url=endpoint_url, events=event_list)
        return format_webhook_result(result)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_create_webhook")
        return f"Error: {e}"


@mcp.tool
async def resend_list_webhooks() -> str:
    """List webhook endpoints. Returns: endpoint | events | status | id."""
    try:
        result = await _run(_get_client().list_webhooks)
        data = result.get("data", []) if isinstance(result, dict) else result
        return format_webhook_list(data)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_list_webhooks")
        return f"Error: {e}"


@mcp.tool
async def resend_delete_webhook(
    webhook_id: Annotated[str, Field(description="Webhook ID to delete")],
) -> str:
    """Delete a webhook endpoint. Requires RESEND_WRITE_ENABLED=true.

    Use ``resend_list_webhooks`` to find webhook IDs.
    """
    if err := require_write():
        return err
    try:
        result = await _run(_get_client().delete_webhook, webhook_id)
        return f"Deleted. id={result.get('id', webhook_id)}"
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_delete_webhook")
        return f"Error: {e}"


# ===================================================================
# LOGS
# ===================================================================


@mcp.tool
async def resend_list_logs(
    limit: Annotated[int, Field(description="Max results")] = DEFAULT_LIMIT,
) -> str:
    """List recent API request logs. Returns: timestamp | method endpoint | status | id."""
    try:
        result = await _run(_get_client().list_logs, limit=limit)
        data = result.get("data", []) if isinstance(result, dict) else result
        return format_log_list(data)
    except ResendError as e:
        return _error_response(e)
    except Exception as e:
        logger.exception("Unexpected error in resend_list_logs")
        return f"Error: {e}"


# ===================================================================
# ENTRY POINT
# ===================================================================


def main() -> None:
    """Start the Resend Blade MCP server."""
    if TRANSPORT == "http":
        from starlette.middleware import Middleware

        from resend_blade_mcp.auth import BearerAuthMiddleware, get_bearer_token

        bearer = get_bearer_token()
        logger.info("Starting HTTP transport on %s:%s", HTTP_HOST, HTTP_PORT)
        if bearer:
            logger.info("Bearer token auth enabled")
        else:
            logger.info("Bearer token auth disabled (RESEND_MCP_API_TOKEN not set)")

        mcp.run(
            transport="streamable-http",
            host=HTTP_HOST,
            port=HTTP_PORT,
            middleware=[Middleware(BearerAuthMiddleware)],
        )
    else:
        mcp.run()
