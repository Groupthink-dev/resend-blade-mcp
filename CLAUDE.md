# Resend Blade MCP — Development Guide

## Ecosystem context

This repo is part of the `Groupthink-dev` platform. It wraps the Resend
transactional email API as an MCP server for the Sidereal Marketplace.

## Project overview

MCP server wrapping the Resend REST API via `httpx`. Each tool is a precision
"blade" for email operations — send, manage contacts/broadcasts/templates, domain
management, webhook configuration. Write operations are gated behind
`RESEND_WRITE_ENABLED=true`. Filesystem access is blocked in attachments.

## Project structure

```
src/resend_blade_mcp/
├── __init__.py       — Version
├── __main__.py       — python -m entry
├── server.py         — FastMCP server + @mcp.tool decorators (28 tools)
├── client.py         — ResendClient wrapping httpx (typed exceptions, error classification)
├── formatters.py     — Token-efficient output formatters
├── models.py         — Constants, write-gate, credential scrubbing, attachment validation
└── auth.py           — Bearer token auth (HTTP transport)
```

- `server.py` defines MCP tools and delegates to `client.py` methods
- `client.py` uses synchronous `httpx.Client` — server bridges via `asyncio.to_thread()`
- All tools return strings (MCP convention) — formatters handle presentation
- Errors are caught and returned as `Error: ...` strings, not raised

## Key commands

```bash
make install-dev   # Install with dev + test dependencies
make test          # Run unit tests (mocked httpx, no Resend needed)
make test-e2e      # Run E2E tests (requires RESEND_E2E=1 + live API key)
make check         # Run all quality checks (lint + format + type-check)
make lint          # Ruff linting
make format        # Ruff formatting
make type-check    # mypy
make run           # Start the MCP server (stdio transport)
```

## Testing

- **Unit tests** (`tests/test_*.py`): Mock httpx.Client. No Resend account needed.
- **E2E tests** (`tests/e2e/`): Require live API key. Run with `make test-e2e`.
- Pattern: `@patch("resend_blade_mcp.server._get_client")` for server tool tests.
- Pattern: `mock_httpx_client` fixture for client tests.

## Code conventions

- **Python 3.12+** — use modern syntax (PEP 604 unions, etc.)
- **Type hints everywhere** — mypy enforced
- **Ruff** for linting and formatting (line length 120)
- **FastMCP 2.0** — `@mcp.tool` decorator, `Annotated[type, Field(...)]` params
- **Token efficiency** — concise output default, limit= on lists, null omission
- **SSH commit signing** via 1Password (no GPG)
- **uv** as package manager, `uv.lock` committed
- Conventional-ish commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`

## Architecture notes

- httpx client (sync, lazy singleton) — all HTTP requests through `_request()` method
- Write-gate: `RESEND_WRITE_ENABLED` env var checked before all 17 write tools
- Attachment security: `validate_attachment()` rejects filesystem paths, allows base64/URL
- API key CRUD excluded entirely — no code path exists
- Credential scrubbing: `re_*` patterns removed from all error messages
- Typed exception hierarchy: AuthError, NotFoundError, RateLimitError, ValidationError, ConnectionError
- 28 tools across 8 categories: sending, contacts, segments, broadcasts, templates, domains, webhooks, logs
- Idempotency-Key header on send operations for safe retries
- User-Agent header mandatory (Resend returns 403 without it)
