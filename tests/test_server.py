"""Tests for MCP server tool functions — mocked client, no network required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from resend_blade_mcp.client import AuthError, NotFoundError, ResendError

# ===================================================================
# SENDING
# ===================================================================


class TestResendSend:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_send

            result = await resend_send(from_addr="a@b.com", to="c@d.com", subject="Test")
            assert "Error:" in result
            assert "RESEND_WRITE_ENABLED" in result
            mock_server_client.send_email.assert_not_called()

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_send

            mock_server_client.send_email.return_value = {"id": "em_abc123"}
            result = await resend_send(from_addr="a@b.com", to="c@d.com", subject="Test", html="<p>Hi</p>")
            assert "em_abc123" in result
            assert "Sent" in result

    async def test_error_propagation(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_send

            mock_server_client.send_email.side_effect = ResendError("Bad request")
            result = await resend_send(from_addr="a@b.com", to="c@d.com", subject="Test")
            assert "Error:" in result

    async def test_invalid_attachments_json(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_send

            result = await resend_send(
                from_addr="a@b.com",
                to="c@d.com",
                subject="Test",
                attachments_json="not valid json",
            )
            assert "Error:" in result
            assert "JSON" in result


class TestResendSendBatch:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_send_batch

            result = await resend_send_batch(emails_json='[{"from": "a@b.com"}]')
            assert "Error:" in result
            assert "RESEND_WRITE_ENABLED" in result

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_send_batch

            mock_server_client.send_batch.return_value = {"data": [{"id": "em_1"}]}
            result = await resend_send_batch(emails_json='[{"from": "a@b.com", "to": ["c@d.com"], "subject": "Test"}]')
            assert "1 emails" in result


class TestResendGetEmail:
    async def test_success(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_get_email

        mock_server_client.get_email.return_value = {
            "id": "em_abc123",
            "from": "a@b.com",
            "to": ["c@d.com"],
            "subject": "Test",
            "last_event": "delivered",
            "created_at": "2026-04-01T10:00:00",
        }
        result = await resend_get_email(email_id="em_abc123")
        assert "em_abc123" in result
        assert "delivered" in result

    async def test_not_found(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_get_email

        mock_server_client.get_email.side_effect = NotFoundError("Not found")
        result = await resend_get_email(email_id="em_nonexistent")
        assert "Error:" in result


class TestResendListEmails:
    async def test_success(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_list_emails

        mock_server_client.list_emails.return_value = {
            "data": [{"id": "em_1", "from": "a@b.com", "subject": "Test", "created_at": "2026-04-01T10:00:00"}]
        }
        result = await resend_list_emails()
        assert "em_1" in result


class TestResendCancelScheduled:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_cancel_scheduled

            result = await resend_cancel_scheduled(email_id="em_abc123")
            assert "Error:" in result

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_cancel_scheduled

            mock_server_client.cancel_scheduled.return_value = {"id": "em_abc123"}
            result = await resend_cancel_scheduled(email_id="em_abc123")
            assert "Cancelled" in result


# ===================================================================
# CONTACTS
# ===================================================================


class TestResendCreateContact:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_create_contact

            result = await resend_create_contact(email="user@example.com")
            assert "Error:" in result

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_create_contact

            mock_server_client.create_contact.return_value = {"id": "ct_abc123"}
            result = await resend_create_contact(email="user@example.com", first_name="Alice")
            assert "ct_abc123" in result


class TestResendListContacts:
    async def test_success(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_list_contacts

        mock_server_client.list_contacts.return_value = {
            "data": [{"id": "ct_1", "email": "a@b.com", "first_name": "Alice"}]
        }
        result = await resend_list_contacts()
        assert "a@b.com" in result


class TestResendDeleteContact:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_delete_contact

            result = await resend_delete_contact(contact_id="ct_abc123")
            assert "Error:" in result


# ===================================================================
# SEGMENTS
# ===================================================================


class TestResendCreateSegment:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_create_segment

            result = await resend_create_segment(name="Test segment")
            assert "Error:" in result

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_create_segment

            mock_server_client.create_segment.return_value = {"id": "seg_abc123"}
            result = await resend_create_segment(name="Test segment")
            assert "seg_abc123" in result


class TestResendListSegments:
    async def test_success(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_list_segments

        mock_server_client.list_segments.return_value = {
            "data": [{"id": "seg_1", "name": "Newsletter", "created_at": "2026-04-01T10:00:00"}]
        }
        result = await resend_list_segments()
        assert "Newsletter" in result


# ===================================================================
# BROADCASTS
# ===================================================================


class TestResendCreateBroadcast:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_create_broadcast

            result = await resend_create_broadcast(segment_id="seg_1", from_addr="a@b.com", subject="Test")
            assert "Error:" in result

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_create_broadcast

            mock_server_client.create_broadcast.return_value = {"id": "bc_abc123"}
            result = await resend_create_broadcast(segment_id="seg_1", from_addr="a@b.com", subject="Test")
            assert "bc_abc123" in result


class TestResendSendBroadcast:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_send_broadcast

            result = await resend_send_broadcast(broadcast_id="bc_1")
            assert "Error:" in result


# ===================================================================
# TEMPLATES
# ===================================================================


class TestResendCreateTemplate:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_create_template

            result = await resend_create_template(name="Test", subject="Hi", html="<p>Hello</p>")
            assert "Error:" in result

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_create_template

            mock_server_client.create_template.return_value = {"id": "tpl_abc123"}
            result = await resend_create_template(name="Test", subject="Hi", html="<p>Hello</p>")
            assert "tpl_abc123" in result


class TestResendListTemplates:
    async def test_success(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_list_templates

        mock_server_client.list_templates.return_value = {
            "data": [{"id": "tpl_1", "name": "Welcome", "subject": "Hi", "status": "published"}]
        }
        result = await resend_list_templates()
        assert "Welcome" in result


class TestResendPublishTemplate:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_publish_template

            result = await resend_publish_template(template_id="tpl_1")
            assert "Error:" in result


# ===================================================================
# DOMAINS
# ===================================================================


class TestResendAddDomain:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_add_domain

            result = await resend_add_domain(name="example.com")
            assert "Error:" in result

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_add_domain

            mock_server_client.add_domain.return_value = {
                "id": "dom_abc123",
                "name": "example.com",
                "status": "not_started",
                "records": [],
            }
            result = await resend_add_domain(name="example.com")
            assert "example.com" in result


class TestResendListDomains:
    async def test_success(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_list_domains

        mock_server_client.list_domains.return_value = {
            "data": [{"id": "dom_1", "name": "example.com", "status": "verified"}]
        }
        result = await resend_list_domains()
        assert "example.com" in result


class TestResendVerifyDomain:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_verify_domain

            result = await resend_verify_domain(domain_id="dom_1")
            assert "Error:" in result


# ===================================================================
# WEBHOOKS
# ===================================================================


class TestResendCreateWebhook:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_create_webhook

            result = await resend_create_webhook(endpoint_url="https://example.com/hook", events="email.delivered")
            assert "Error:" in result

    async def test_success(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            from resend_blade_mcp.server import resend_create_webhook

            mock_server_client.create_webhook.return_value = {"id": "wh_abc123", "signing_secret": "whsec_test"}
            result = await resend_create_webhook(
                endpoint_url="https://example.com/hook", events="email.delivered,email.bounced"
            )
            assert "wh_abc123" in result
            assert "whsec_test" in result


class TestResendListWebhooks:
    async def test_success(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_list_webhooks

        mock_server_client.list_webhooks.return_value = {
            "data": [{"id": "wh_1", "endpoint": "https://example.com/hook", "events": ["email.delivered"]}]
        }
        result = await resend_list_webhooks()
        assert "example.com/hook" in result


class TestResendDeleteWebhook:
    async def test_write_gate_blocks(self, mock_server_client: MagicMock) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            from resend_blade_mcp.server import resend_delete_webhook

            result = await resend_delete_webhook(webhook_id="wh_1")
            assert "Error:" in result


# ===================================================================
# LOGS
# ===================================================================


class TestResendListLogs:
    async def test_success(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_list_logs

        mock_server_client.list_logs.return_value = {
            "data": [
                {
                    "id": "log_1",
                    "method": "POST",
                    "endpoint": "/emails",
                    "response_status": 200,
                    "created_at": "2026-04-01T10:00:00",
                }
            ]
        }
        result = await resend_list_logs()
        assert "POST /emails" in result

    async def test_error(self, mock_server_client: MagicMock) -> None:
        from resend_blade_mcp.server import resend_list_logs

        mock_server_client.list_logs.side_effect = AuthError("Unauthorized")
        result = await resend_list_logs()
        assert "Error:" in result
