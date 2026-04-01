"""Shared test fixtures and sample data for Resend Blade MCP tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from resend_blade_mcp.client import ResendClient


@pytest.fixture
def mock_httpx_client() -> MagicMock:
    """Patch httpx.Client and return the mock instance."""
    with patch("resend_blade_mcp.client.httpx.Client") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def client(mock_httpx_client: MagicMock) -> ResendClient:
    """Create a ResendClient with mocked httpx."""
    from resend_blade_mcp.client import ResendClient

    return ResendClient(api_key="re_test_123456789")


@pytest.fixture
def mock_server_client() -> MagicMock:
    """Patch _get_client in server module to return a mock ResendClient."""
    with patch("resend_blade_mcp.server._get_client") as mock_get:
        mock = MagicMock()
        mock_get.return_value = mock
        yield mock


# ===================================================================
# Sample API response fixtures
# ===================================================================


@pytest.fixture
def sample_email() -> dict:
    """Sample email response from GET /emails/{id}."""
    return {
        "object": "email",
        "id": "em_abc123",
        "to": ["user@example.com"],
        "from": "sender@example.com",
        "created_at": "2026-04-01T10:00:00.000Z",
        "subject": "Test email",
        "html": "<p>Hello</p>",
        "text": "Hello",
        "bcc": [],
        "cc": [],
        "reply_to": [],
        "last_event": "delivered",
        "scheduled_at": None,
        "tags": [{"name": "category", "value": "test"}],
    }


@pytest.fixture
def sample_email_list() -> list[dict]:
    """Sample email list response."""
    return [
        {
            "id": "em_abc123",
            "from": "sender@example.com",
            "to": ["user@example.com"],
            "subject": "Test email 1",
            "created_at": "2026-04-01T10:00:00.000Z",
            "last_event": "delivered",
        },
        {
            "id": "em_def456",
            "from": "sender@example.com",
            "to": ["other@example.com"],
            "subject": "Test email 2",
            "created_at": "2026-04-01T09:00:00.000Z",
            "last_event": "sent",
        },
    ]


@pytest.fixture
def sample_contact() -> dict:
    """Sample contact response."""
    return {
        "object": "contact",
        "id": "ct_abc123",
        "email": "user@example.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "created_at": "2026-04-01T10:00:00.000Z",
        "unsubscribed": False,
    }


@pytest.fixture
def sample_contacts() -> list[dict]:
    """Sample contact list."""
    return [
        {
            "id": "ct_abc123",
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "unsubscribed": False,
        },
        {
            "id": "ct_def456",
            "email": "bob@example.com",
            "first_name": "Bob",
            "last_name": None,
            "unsubscribed": True,
        },
    ]


@pytest.fixture
def sample_segment() -> dict:
    """Sample segment response."""
    return {
        "object": "segment",
        "id": "seg_abc123",
        "name": "Newsletter subscribers",
        "created_at": "2026-04-01T10:00:00.000Z",
    }


@pytest.fixture
def sample_segments() -> list[dict]:
    """Sample segment list."""
    return [
        {"id": "seg_abc123", "name": "Newsletter subscribers", "created_at": "2026-04-01T10:00:00.000Z"},
        {"id": "seg_def456", "name": "Premium users", "created_at": "2026-03-15T10:00:00.000Z"},
    ]


@pytest.fixture
def sample_broadcast() -> dict:
    """Sample broadcast response."""
    return {
        "id": "bc_abc123",
        "name": "March newsletter",
        "subject": "Your monthly update",
        "status": "draft",
        "created_at": "2026-04-01T10:00:00.000Z",
        "sent_at": None,
        "scheduled_at": None,
    }


@pytest.fixture
def sample_broadcasts() -> list[dict]:
    """Sample broadcast list."""
    return [
        {
            "id": "bc_abc123",
            "name": "March newsletter",
            "subject": "Your monthly update",
            "status": "sent",
            "sent_at": "2026-03-31T12:00:00.000Z",
        },
        {
            "id": "bc_def456",
            "name": "April preview",
            "subject": "Coming soon",
            "status": "draft",
            "created_at": "2026-04-01T10:00:00.000Z",
        },
    ]


@pytest.fixture
def sample_template() -> dict:
    """Sample template response."""
    return {
        "object": "template",
        "id": "tpl_abc123",
        "name": "Welcome email",
        "subject": "Welcome, {{{FIRST_NAME}}}!",
        "html": "<h1>Welcome {{{FIRST_NAME|friend}}}!</h1><p>Thanks for joining.</p>",
        "text": "Welcome! Thanks for joining.",
        "status": "published",
    }


@pytest.fixture
def sample_templates() -> list[dict]:
    """Sample template list."""
    return [
        {"id": "tpl_abc123", "name": "Welcome email", "subject": "Welcome!", "status": "published"},
        {"id": "tpl_def456", "name": "Password reset", "subject": "Reset your password", "status": "draft"},
    ]


@pytest.fixture
def sample_domain() -> dict:
    """Sample domain response with DNS records."""
    return {
        "id": "dom_abc123",
        "name": "example.com",
        "status": "verified",
        "region": "us-east-1",
        "records": [
            {
                "record": "SPF",
                "name": "send",
                "type": "MX",
                "value": "feedback-smtp.us-east-1.amazonses.com",
                "status": "verified",
                "ttl": "Auto",
                "priority": 10,
            },
            {
                "record": "DKIM",
                "name": "abc._domainkey",
                "type": "CNAME",
                "value": "abc.dkim.amazonses.com",
                "status": "verified",
                "ttl": "Auto",
            },
        ],
    }


@pytest.fixture
def sample_domains() -> list[dict]:
    """Sample domain list."""
    return [
        {"id": "dom_abc123", "name": "example.com", "status": "verified", "region": "us-east-1"},
        {"id": "dom_def456", "name": "staging.example.com", "status": "pending", "region": "eu-west-1"},
    ]


@pytest.fixture
def sample_webhook() -> dict:
    """Sample webhook response."""
    return {
        "object": "webhook",
        "id": "wh_abc123",
        "endpoint": "https://hooks.example.com/resend",
        "events": ["email.delivered", "email.bounced"],
        "status": "enabled",
        "signing_secret": "whsec_test_secret_123",
    }


@pytest.fixture
def sample_webhooks() -> list[dict]:
    """Sample webhook list."""
    return [
        {
            "id": "wh_abc123",
            "endpoint": "https://hooks.example.com/resend",
            "events": ["email.delivered", "email.bounced"],
            "status": "enabled",
        },
        {
            "id": "wh_def456",
            "endpoint": "https://hooks.example.com/contacts",
            "events": ["contact.created"],
            "status": "disabled",
        },
    ]


@pytest.fixture
def sample_logs() -> list[dict]:
    """Sample log list."""
    return [
        {
            "id": "log_abc123",
            "created_at": "2026-04-01T10:00:00.000Z",
            "endpoint": "/emails",
            "method": "POST",
            "response_status": 200,
        },
        {
            "id": "log_def456",
            "created_at": "2026-04-01T09:55:00.000Z",
            "endpoint": "/domains",
            "method": "GET",
            "response_status": 200,
        },
    ]
