"""E2E read-only tests against the live Resend API.

Run with: RESEND_E2E=1 RESEND_API_KEY=re_xxx make test-e2e
"""

from __future__ import annotations

import pytest

from resend_blade_mcp.client import ResendClient


@pytest.mark.e2e
class TestE2EDomains:
    def test_list_domains(self, live_client: ResendClient) -> None:
        result = live_client.list_domains()
        assert isinstance(result, dict)
        assert "data" in result

    def test_list_domains_returns_list(self, live_client: ResendClient) -> None:
        result = live_client.list_domains()
        assert isinstance(result["data"], list)


@pytest.mark.e2e
class TestE2EEmails:
    def test_list_emails(self, live_client: ResendClient) -> None:
        result = live_client.list_emails(limit=5)
        assert isinstance(result, dict)


@pytest.mark.e2e
class TestE2EWebhooks:
    def test_list_webhooks(self, live_client: ResendClient) -> None:
        result = live_client.list_webhooks()
        assert isinstance(result, dict)


@pytest.mark.e2e
class TestE2ETemplates:
    def test_list_templates(self, live_client: ResendClient) -> None:
        result = live_client.list_templates()
        assert isinstance(result, dict)
