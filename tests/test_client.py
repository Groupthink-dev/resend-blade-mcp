"""Tests for ResendClient — mocked httpx, no network required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from resend_blade_mcp.client import (
    AuthError,
    NotFoundError,
    RateLimitError,
    ResendClient,
    ResendError,
    ValidationError,
)


class TestClientInit:
    def test_init_with_key(self, mock_httpx_client: MagicMock) -> None:
        client = ResendClient(api_key="re_test_123")
        assert client is not None

    def test_init_from_env(self, mock_httpx_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_API_KEY": "re_env_key_123"}):
            client = ResendClient()
            assert client is not None

    def test_init_without_key_raises(self, mock_httpx_client: MagicMock) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthError, match="RESEND_API_KEY"):
                ResendClient()


class TestSendEmail:
    def test_success(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "em_abc123"}'
        mock_resp.json.return_value = {"id": "em_abc123"}
        mock_httpx_client.request.return_value = mock_resp

        result = client.send_email(
            from_addr="sender@example.com",
            to=["user@example.com"],
            subject="Test",
            html="<p>Hello</p>",
        )
        assert result["id"] == "em_abc123"
        mock_httpx_client.request.assert_called_once()

    def test_with_idempotency_key(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "em_abc123"}'
        mock_resp.json.return_value = {"id": "em_abc123"}
        mock_httpx_client.request.return_value = mock_resp

        client.send_email(
            from_addr="sender@example.com",
            to=["user@example.com"],
            subject="Test",
            html="<p>Hello</p>",
            idempotency_key="unique-key-123",
        )
        call_kwargs = mock_httpx_client.request.call_args
        assert "headers" in call_kwargs.kwargs or any("Idempotency-Key" in str(a) for a in call_kwargs.args)

    def test_rejects_filesystem_attachment(self, client: ResendClient) -> None:
        with pytest.raises(ValidationError, match="Filesystem"):
            client.send_email(
                from_addr="sender@example.com",
                to=["user@example.com"],
                subject="Test",
                attachments=[{"path": "/etc/passwd", "filename": "passwd"}],
            )

    def test_accepts_base64_attachment(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "em_abc123"}'
        mock_resp.json.return_value = {"id": "em_abc123"}
        mock_httpx_client.request.return_value = mock_resp

        result = client.send_email(
            from_addr="sender@example.com",
            to=["user@example.com"],
            subject="Test",
            attachments=[{"content": "SGVsbG8=", "filename": "test.txt"}],
        )
        assert result["id"] == "em_abc123"

    def test_accepts_url_attachment(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "em_abc123"}'
        mock_resp.json.return_value = {"id": "em_abc123"}
        mock_httpx_client.request.return_value = mock_resp

        result = client.send_email(
            from_addr="sender@example.com",
            to=["user@example.com"],
            subject="Test",
            attachments=[{"path": "https://example.com/file.pdf", "filename": "file.pdf"}],
        )
        assert result["id"] == "em_abc123"


class TestSendBatch:
    def test_success(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"data": [{"id": "em_1"}, {"id": "em_2"}]}'
        mock_resp.json.return_value = {"data": [{"id": "em_1"}, {"id": "em_2"}]}
        mock_httpx_client.request.return_value = mock_resp

        result = client.send_batch(
            emails=[
                {"from": "a@b.com", "to": ["c@d.com"], "subject": "Test 1", "html": "<p>1</p>"},
                {"from": "a@b.com", "to": ["e@f.com"], "subject": "Test 2", "html": "<p>2</p>"},
            ]
        )
        assert len(result["data"]) == 2

    def test_exceeds_max_batch_size(self, client: ResendClient) -> None:
        emails = [{"from": "a@b.com", "to": ["c@d.com"], "subject": f"Test {i}"} for i in range(101)]
        with pytest.raises(ValidationError, match="exceeds maximum"):
            client.send_batch(emails=emails)


class TestGetEmail:
    def test_success(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "em_abc123", "subject": "Test"}'
        mock_resp.json.return_value = {"id": "em_abc123", "subject": "Test"}
        mock_httpx_client.request.return_value = mock_resp

        result = client.get_email("em_abc123")
        assert result["id"] == "em_abc123"

    def test_not_found(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"message": "Not found"}
        mock_httpx_client.request.return_value = mock_resp

        with pytest.raises(NotFoundError):
            client.get_email("em_nonexistent")


class TestErrorClassification:
    def test_401_auth_error(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"message": "Missing API key"}
        mock_httpx_client.request.return_value = mock_resp

        with pytest.raises(AuthError):
            client.list_domains()

    def test_403_auth_error(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"message": "Invalid API key"}
        mock_httpx_client.request.return_value = mock_resp

        with pytest.raises(AuthError):
            client.list_domains()

    def test_404_not_found(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"message": "Not found"}
        mock_httpx_client.request.return_value = mock_resp

        with pytest.raises(NotFoundError):
            client.get_email("em_none")

    def test_422_validation_error(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.json.return_value = {"message": "Invalid email address"}
        mock_httpx_client.request.return_value = mock_resp

        with pytest.raises(ValidationError):
            client.send_email(from_addr="bad", to=["user@example.com"], subject="Test")

    def test_429_rate_limit(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"retry-after": "2"}
        mock_resp.json.return_value = {"message": "Rate limit exceeded"}
        mock_httpx_client.request.return_value = mock_resp

        with pytest.raises(RateLimitError) as exc_info:
            client.list_emails()
        assert exc_info.value.retry_after == 2.0

    def test_500_generic_error(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"message": "Internal server error"}
        mock_httpx_client.request.return_value = mock_resp

        with pytest.raises(ResendError):
            client.list_domains()


class TestCredentialScrubbing:
    def test_api_key_scrubbed_from_errors(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"message": "Invalid key: re_live_key_abc123def456"}
        mock_httpx_client.request.return_value = mock_resp

        with pytest.raises(AuthError) as exc_info:
            client.list_domains()
        assert "re_live_key_abc123def456" not in str(exc_info.value)
        assert "re_****" in str(exc_info.value)


class TestDomains:
    def test_list_domains(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"data": [{"id": "dom_1", "name": "example.com"}]}'
        mock_resp.json.return_value = {"data": [{"id": "dom_1", "name": "example.com"}]}
        mock_httpx_client.request.return_value = mock_resp

        result = client.list_domains()
        assert "data" in result

    def test_get_domain(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "dom_1", "name": "example.com", "records": []}'
        mock_resp.json.return_value = {"id": "dom_1", "name": "example.com", "records": []}
        mock_httpx_client.request.return_value = mock_resp

        result = client.get_domain("dom_1")
        assert result["name"] == "example.com"


class TestWebhooks:
    def test_create_webhook(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "wh_1", "signing_secret": "whsec_test"}'
        mock_resp.json.return_value = {"id": "wh_1", "signing_secret": "whsec_test"}
        mock_httpx_client.request.return_value = mock_resp

        result = client.create_webhook(endpoint_url="https://example.com/hook", events=["email.delivered"])
        assert result["signing_secret"] == "whsec_test"

    def test_list_webhooks(self, client: ResendClient, mock_httpx_client: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"data": []}'
        mock_resp.json.return_value = {"data": []}
        mock_httpx_client.request.return_value = mock_resp

        result = client.list_webhooks()
        assert "data" in result
