"""Tests for token-efficient formatters."""

from __future__ import annotations

from resend_blade_mcp.formatters import (
    format_batch_result,
    format_broadcast,
    format_broadcast_list,
    format_cancel_result,
    format_contact_list,
    format_contact_result,
    format_domain,
    format_domain_list,
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


class TestSendFormatters:
    def test_format_send_result(self) -> None:
        result = format_send_result({"id": "em_abc123"})
        assert "em_abc123" in result
        assert "Sent" in result

    def test_format_batch_result(self) -> None:
        result = format_batch_result({"data": [{"id": "em_1"}, {"id": "em_2"}]})
        assert "2 emails" in result
        assert "em_1" in result
        assert "em_2" in result

    def test_format_batch_result_empty(self) -> None:
        result = format_batch_result({"data": []})
        assert "Batch sent" in result

    def test_format_cancel_result(self) -> None:
        result = format_cancel_result({"id": "em_abc123"})
        assert "Cancelled" in result
        assert "em_abc123" in result


class TestEmailFormatters:
    def test_format_email(self, sample_email: dict) -> None:
        result = format_email(sample_email)
        assert "em_abc123" in result
        assert "sender@example.com" in result
        assert "Test email" in result
        assert "delivered" in result

    def test_format_email_with_body(self, sample_email: dict) -> None:
        result = format_email(sample_email)
        assert "<p>Hello</p>" in result

    def test_format_email_list(self, sample_email_list: list[dict]) -> None:
        result = format_email_list(sample_email_list)
        assert "em_abc123" in result
        assert "em_def456" in result
        assert "|" in result

    def test_format_email_list_empty(self) -> None:
        assert "No emails found" in format_email_list([])

    def test_format_email_list_capped(self) -> None:
        emails = [
            {"id": f"em_{i}", "from": "a@b.com", "subject": f"Test {i}", "created_at": "2026-04-01T10:00:00"}
            for i in range(25)
        ]
        result = format_email_list(emails, total=25, limit=20)
        assert "5 more" in result


class TestContactFormatters:
    def test_format_contact_list(self, sample_contacts: list[dict]) -> None:
        result = format_contact_list(sample_contacts)
        assert "alice@example.com" in result
        assert "bob@example.com" in result
        assert "Alice" in result
        assert "unsubscribed" in result

    def test_format_contact_list_empty(self) -> None:
        assert "No contacts found" in format_contact_list([])

    def test_format_contact_result(self) -> None:
        result = format_contact_result({"id": "ct_abc123"})
        assert "ct_abc123" in result


class TestSegmentFormatters:
    def test_format_segment_list(self, sample_segments: list[dict]) -> None:
        result = format_segment_list(sample_segments)
        assert "Newsletter subscribers" in result
        assert "Premium users" in result

    def test_format_segment_list_empty(self) -> None:
        assert "No segments found" in format_segment_list([])

    def test_format_segment_result(self) -> None:
        result = format_segment_result({"id": "seg_abc123"})
        assert "seg_abc123" in result


class TestBroadcastFormatters:
    def test_format_broadcast(self, sample_broadcast: dict) -> None:
        result = format_broadcast(sample_broadcast)
        assert "March newsletter" in result
        assert "draft" in result

    def test_format_broadcast_list(self, sample_broadcasts: list[dict]) -> None:
        result = format_broadcast_list(sample_broadcasts)
        assert "March newsletter" in result
        assert "April preview" in result

    def test_format_broadcast_list_empty(self) -> None:
        assert "No broadcasts found" in format_broadcast_list([])


class TestTemplateFormatters:
    def test_format_template_detail(self, sample_template: dict) -> None:
        result = format_template_detail(sample_template)
        assert "Welcome email" in result
        assert "published" in result
        assert "Welcome" in result  # HTML body

    def test_format_template_list(self, sample_templates: list[dict]) -> None:
        result = format_template_list(sample_templates)
        assert "Welcome email" in result
        assert "Password reset" in result

    def test_format_template_list_empty(self) -> None:
        assert "No templates found" in format_template_list([])

    def test_format_template_result(self) -> None:
        result = format_template_result({"id": "tpl_abc123"})
        assert "tpl_abc123" in result


class TestDomainFormatters:
    def test_format_domain_with_records(self, sample_domain: dict) -> None:
        result = format_domain(sample_domain)
        assert "example.com" in result
        assert "verified" in result
        assert "DNS records" in result
        assert "SPF" in result
        assert "DKIM" in result

    def test_format_domain_list(self, sample_domains: list[dict]) -> None:
        result = format_domain_list(sample_domains)
        assert "example.com" in result
        assert "staging.example.com" in result
        assert "pending" in result

    def test_format_domain_list_empty(self) -> None:
        assert "No domains found" in format_domain_list([])


class TestWebhookFormatters:
    def test_format_webhook_list(self, sample_webhooks: list[dict]) -> None:
        result = format_webhook_list(sample_webhooks)
        assert "hooks.example.com/resend" in result
        assert "email.delivered" in result

    def test_format_webhook_list_empty(self) -> None:
        assert "No webhooks found" in format_webhook_list([])

    def test_format_webhook_result_with_secret(self, sample_webhook: dict) -> None:
        result = format_webhook_result(sample_webhook)
        assert "wh_abc123" in result
        assert "whsec_test_secret_123" in result
        assert "shown only once" in result


class TestLogFormatters:
    def test_format_log_list(self, sample_logs: list[dict]) -> None:
        result = format_log_list(sample_logs)
        assert "POST /emails" in result
        assert "GET /domains" in result
        assert "200" in result

    def test_format_log_list_empty(self) -> None:
        assert "No logs found" in format_log_list([])
