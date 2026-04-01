# Resend Blade MCP

Security-first MCP server for [Resend](https://resend.com) transactional email — send, manage contacts, broadcasts, templates, domains, and webhooks with programmatic safety controls.

Built on [FastMCP 2.0](https://github.com/jlowin/fastmcp) and [httpx](https://www.python-httpx.org/). Designed for agentic workflows where LLMs operate autonomously.

## Why not the official Resend MCP?

The [official resend-mcp](https://github.com/resend/resend-mcp) covers the full API but was designed for human-supervised chat, not autonomous agents. In agentic contexts, its security model breaks down:

| Capability | resend-blade-mcp | Official resend-mcp | Generic vendor MCPs |
|---|---|---|---|
| **Write gating** | Programmatic env var gate | Prompt engineering only | Usually none |
| **Filesystem access** | **None** — base64/URL only | `filePath` reads any file | Varies |
| **API key management** | **Excluded entirely** | Full CRUD exposed to agent | Often exposed |
| **Credential scrubbing** | All error paths scrubbed | Not implemented | Rarely |
| **Tool count** | 28 focused | 60+ (context window bloat) | Varies |
| **Output format** | Pipe-delimited, null omission | Raw JSON responses | Raw JSON |
| **HTTP transport auth** | Built-in bearer middleware | Per-session key only | Rarely |
| **Idempotency** | Native `Idempotency-Key` header | Not exposed as parameter | Rarely |
| **Rate limit handling** | Typed `RateLimitError` with retry-after | Raw error passthrough | Varies |

### The filesystem problem

The official MCP accepts `filePath` in attachments, calling `fs.readFile()` with no path validation. An autonomous agent could read `/etc/passwd`, `~/.ssh/id_rsa`, or any file on the host and attach it to an email sent to any address. **resend-blade-mcp** rejects all filesystem paths — only base64 content and HTTPS URLs are permitted.

### The API key problem

The official MCP exposes `create-api-key` and `remove-api-key` tools. An agent could create a full-access API key and exfiltrate it, or delete existing keys to disrupt services. **resend-blade-mcp** excludes API key management entirely — these are privileged operations that belong out-of-band.

## Features

- **28 tools** across 8 categories: sending, contacts, segments, broadcasts, templates, domains, webhooks, logs
- **Write-gate** — all mutating operations disabled by default (`RESEND_WRITE_ENABLED=true` to enable)
- **No filesystem access** — attachments via base64 content or HTTPS URL only
- **No API key CRUD** — excluded by design, not just gated
- **Credential scrubbing** — `re_*` API keys stripped from all error output
- **Token-efficient** — pipe-delimited output, null-field omission, capped lists
- **Idempotent sends** — native `Idempotency-Key` support prevents duplicate emails on retry
- **Webhook management** — create, list, delete webhook endpoints for event-driven architectures
- **Sidereal Marketplace** — native plugin manifest for one-click install

## Requirements

- macOS (tested) or Linux
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Resend account with API key ([get one here](https://resend.com/api-keys))

## Quick Start

```bash
# Clone and install
git clone https://github.com/Groupthink-dev/resend-blade-mcp.git
cd resend-blade-mcp
uv sync

# Set your API key
export RESEND_API_KEY=re_xxxxxxxx

# Run (stdio transport)
uv run resend-blade-mcp
```

### Claude Code

```bash
claude mcp add resend-blade -- uv run --directory ~/src/resend-blade-mcp resend-blade-mcp
```

### Claude Desktop (claude_desktop_config.json)

```json
{
  "mcpServers": {
    "resend-blade": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/resend-blade-mcp", "resend-blade-mcp"],
      "env": {
        "RESEND_API_KEY": "re_xxxxxxxx",
        "RESEND_WRITE_ENABLED": "false"
      }
    }
  }
}
```

## Tools (28)

### Sending (5)

| Tool | Gate | Description |
|------|------|-------------|
| `resend_send` | write | Send email (HTML/text, attachments, scheduled, idempotent) |
| `resend_send_batch` | write | Batch send up to 100 emails |
| `resend_get_email` | read | Retrieve sent email by ID |
| `resend_list_emails` | read | List sent emails with status |
| `resend_cancel_scheduled` | write | Cancel a scheduled email |

### Contacts (4)

| Tool | Gate | Description |
|------|------|-------------|
| `resend_create_contact` | write | Create a contact with properties |
| `resend_list_contacts` | read | List contacts |
| `resend_update_contact` | write | Update contact properties |
| `resend_delete_contact` | write | Delete a contact |

### Segments (3)

| Tool | Gate | Description |
|------|------|-------------|
| `resend_create_segment` | write | Create a segment |
| `resend_list_segments` | read | List segments |
| `resend_delete_segment` | write | Delete a segment |

### Broadcasts (4)

| Tool | Gate | Description |
|------|------|-------------|
| `resend_create_broadcast` | write | Create a broadcast (draft) |
| `resend_send_broadcast` | write | Send or schedule a draft broadcast |
| `resend_list_broadcasts` | read | List broadcasts with status |
| `resend_delete_broadcast` | write | Delete a draft/scheduled broadcast |

### Templates (4)

| Tool | Gate | Description |
|------|------|-------------|
| `resend_create_template` | write | Create template with variables |
| `resend_list_templates` | read | List templates |
| `resend_get_template` | read | Get template with HTML content |
| `resend_publish_template` | write | Publish template for use in sends |

### Domains (4)

| Tool | Gate | Description |
|------|------|-------------|
| `resend_add_domain` | write | Register a sending domain (returns DNS records) |
| `resend_list_domains` | read | List domains with verification status |
| `resend_get_domain` | read | Get domain with DNS record details |
| `resend_verify_domain` | write | Trigger DNS verification |

### Webhooks (3)

| Tool | Gate | Description |
|------|------|-------------|
| `resend_create_webhook` | write | Create webhook endpoint (returns signing secret) |
| `resend_list_webhooks` | read | List webhook endpoints |
| `resend_delete_webhook` | write | Delete a webhook |

### Logs (1)

| Tool | Gate | Description |
|------|------|-------------|
| `resend_list_logs` | read | List recent API request logs |

## Security

| Layer | Control |
|-------|---------|
| API key | `RESEND_API_KEY` from env (never logged, scrubbed from errors) |
| Transport | stdio default (no network exposure) |
| Write gate | `RESEND_WRITE_ENABLED` default `false` — blocks all 17 write tools |
| Attachments | Base64 content or HTTPS URL only — filesystem paths rejected |
| API key CRUD | Excluded — no tool can create, list, or delete API keys |
| Batch limits | `resend_send_batch` capped at 100 (Resend API maximum) |
| Credential scrubbing | `re_*` patterns removed from all error output |
| HTTP auth | Optional bearer token middleware (`RESEND_MCP_API_TOKEN`) |
| Rate limits | 429 responses surface as typed `RateLimitError` with retry-after |

## HTTP Transport

```bash
export RESEND_MCP_TRANSPORT=http
export RESEND_MCP_HOST=127.0.0.1
export RESEND_MCP_PORT=8770
export RESEND_MCP_API_TOKEN=your-secret-token

uv run resend-blade-mcp
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RESEND_API_KEY` | (required) | Resend API key |
| `RESEND_WRITE_ENABLED` | `false` | Enable write operations |
| `RESEND_MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `http` |
| `RESEND_MCP_HOST` | `127.0.0.1` | HTTP bind host |
| `RESEND_MCP_PORT` | `8770` | HTTP bind port |
| `RESEND_MCP_API_TOKEN` | (none) | Bearer token for HTTP auth |

## Development

```bash
make install-dev    # Install with dev dependencies
make test           # Run unit tests (mocked, no Resend needed)
make test-e2e       # Run E2E tests (requires live API key)
make check          # Lint + format + type-check
make run            # Start the server
```

## License

MIT
