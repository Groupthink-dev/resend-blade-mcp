"""E2E test fixtures — requires live Resend API key."""

from __future__ import annotations

import os

import pytest

from resend_blade_mcp.client import ResendClient


@pytest.fixture(scope="session")
def live_client() -> ResendClient:
    """Create a ResendClient with a live API key for E2E testing."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        pytest.skip("RESEND_API_KEY not set")
    return ResendClient(api_key=api_key)
