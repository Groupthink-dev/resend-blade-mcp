"""Bearer token authentication middleware for HTTP transport.

When ``RESEND_MCP_API_TOKEN`` is set, every HTTP request must carry a matching
``Authorization: Bearer <token>`` header. Requests without a valid token
receive a ``401 Unauthorized`` JSON response.

If the env var is unset or empty, this middleware is a transparent pass-through.
"""

from __future__ import annotations

import json
import logging
import os
import secrets

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

_cached_token: str | None = None
_token_loaded = False


def get_bearer_token() -> str | None:
    """Get the bearer token from env. Cached after first call."""
    global _cached_token, _token_loaded
    if not _token_loaded:
        _cached_token = os.environ.get("RESEND_MCP_API_TOKEN", "").strip() or None
        _token_loaded = True
    return _cached_token


class BearerAuthMiddleware:
    """Starlette-compatible ASGI middleware for Bearer token auth."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        expected = get_bearer_token()
        if expected is None:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_value = headers.get(b"authorization", b"").decode("latin-1")

        provided = ""
        if auth_value.lower().startswith("bearer "):
            provided = auth_value[7:]

        if provided and secrets.compare_digest(provided, expected):
            await self.app(scope, receive, send)
            return

        body = json.dumps({"error": "Unauthorized"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
