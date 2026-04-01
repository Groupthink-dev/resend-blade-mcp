---
name: resend-blade
description: Resend transactional email — send, contacts, broadcasts, templates, domains, webhooks
version: 0.1.0
permissions:
  read:
    - resend_get_email
    - resend_list_emails
    - resend_list_contacts
    - resend_list_segments
    - resend_list_broadcasts
    - resend_list_templates
    - resend_get_template
    - resend_list_domains
    - resend_get_domain
    - resend_list_webhooks
    - resend_list_logs
  write:
    - resend_send
    - resend_send_batch
    - resend_cancel_scheduled
    - resend_create_contact
    - resend_update_contact
    - resend_delete_contact
    - resend_create_segment
    - resend_delete_segment
    - resend_create_broadcast
    - resend_send_broadcast
    - resend_delete_broadcast
    - resend_create_template
    - resend_publish_template
    - resend_add_domain
    - resend_verify_domain
    - resend_create_webhook
    - resend_delete_webhook
---

# Resend Blade MCP — Skill Guide

## Token Efficiency Rules (MANDATORY)

1. Use `resend_list_*` before `resend_get_*` — list views are compact, detail views include full content
2. Never fetch all emails then filter — use server-side `limit` parameter
3. Use `resend_send_batch` instead of multiple `resend_send` calls for bulk transactional email
4. Template IDs can be passed to `resend_send` — don't fetch template HTML to inline it
5. Check `resend_list_domains` before sending — a verified domain is required
6. Use `idempotency_key` on sends to safely retry without duplicates
7. Pipe-delimited output is already token-efficient — don't reformat it
8. Webhook signing secrets are shown only once at creation — capture them immediately

## Quick Start — 5 Most Common Operations

```
# 1. Send a transactional email
resend_send(from_addr="you@verified-domain.com", to="user@example.com", subject="Welcome!", html="<h1>Hello</h1>")

# 2. List sent emails
resend_list_emails(limit=10)

# 3. Check domain verification status
resend_list_domains()

# 4. Create a webhook for delivery events
resend_create_webhook(endpoint_url="https://hooks.example.com/resend", events="email.delivered,email.bounced")

# 5. List contacts
resend_list_contacts(limit=20)
```

## Tool Reference

### Sending
- `resend_send` — Send email (HTML/text, CC/BCC, attachments, scheduled, idempotent)
- `resend_send_batch` — Batch send up to 100 emails (no attachments, no scheduling)
- `resend_get_email` — Retrieve sent email by ID (headers + body + status)
- `resend_list_emails` — List sent emails (date | from | subject | status | id)
- `resend_cancel_scheduled` — Cancel a scheduled email before it sends

### Contacts
- `resend_create_contact` — Create with email, name, subscribe status
- `resend_list_contacts` — List (email | name | status | id)
- `resend_update_contact` — Update name or unsubscribe status
- `resend_delete_contact` — Remove a contact

### Segments
- `resend_create_segment` — Create a named segment
- `resend_list_segments` — List (name | id | created)
- `resend_delete_segment` — Remove a segment

### Broadcasts
- `resend_create_broadcast` — Create a draft targeting a segment
- `resend_send_broadcast` — Send immediately or schedule
- `resend_list_broadcasts` — List (name | subject | status | date | id)
- `resend_delete_broadcast` — Delete draft/scheduled only

### Templates
- `resend_create_template` — Create with `{{{VARIABLE}}}` placeholders
- `resend_list_templates` — List (name | subject | status | id)
- `resend_get_template` — Retrieve with HTML content
- `resend_publish_template` — Must publish before use in sends

### Domains
- `resend_add_domain` — Register (returns DNS records to add)
- `resend_list_domains` — List (name | status | region | id)
- `resend_get_domain` — Detail with DNS record status
- `resend_verify_domain` — Trigger verification after DNS setup

### Webhooks
- `resend_create_webhook` — Create endpoint (returns signing secret once)
- `resend_list_webhooks` — List (endpoint | events | status | id)
- `resend_delete_webhook` — Remove endpoint

### Logs
- `resend_list_logs` — Recent API request logs (timestamp | method | status | id)

## Workflow Examples

### Send a transactional email with template
1. `resend_list_templates` — find the template ID
2. `resend_list_domains` — verify sending domain is active
3. `resend_send` with `from_addr` on verified domain, `to`, `subject`, `html`

### Set up domain and verify
1. `resend_add_domain(name="example.com")` — returns DNS records
2. Add SPF + DKIM records at your DNS provider
3. `resend_verify_domain(domain_id="dom_xxx")` — triggers verification
4. `resend_get_domain(domain_id="dom_xxx")` — check record status

### Create and send a broadcast
1. `resend_list_segments` — find or create target segment
2. `resend_create_broadcast(segment_id="seg_xxx", from_addr="...", subject="...", html="...")`
3. `resend_send_broadcast(broadcast_id="bc_xxx")` — send immediately
4. Or: `resend_send_broadcast(broadcast_id="bc_xxx", scheduled_at="2026-04-05T10:00:00Z")`

### Set up webhook for delivery tracking
1. `resend_create_webhook(endpoint_url="https://hooks.example.com/resend", events="email.delivered,email.bounced,email.complained")`
2. Save the `signing_secret` from the response
3. Verify webhook payloads using Svix signature verification

## Common Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `from_addr` | Sender email (must be on verified domain) | `"Support <support@example.com>"` |
| `to` | Recipient(s), comma-separated | `"a@b.com, c@d.com"` |
| `scheduled_at` | ISO 8601 datetime | `"2026-04-05T10:00:00Z"` |
| `idempotency_key` | Unique retry key (24h expiry) | `"order-123-welcome"` |
| `limit` | Max results for list operations | `20` (default) |
| `events` | Webhook events, comma-separated | `"email.delivered,email.bounced"` |

## Security Notes

- All write tools require `RESEND_WRITE_ENABLED=true` — disabled by default
- Attachments accept only base64 content or HTTPS URLs — filesystem paths are rejected
- API key create/list/delete operations are intentionally excluded
- API keys (`re_*`) are scrubbed from all error messages
- Webhook signing secrets are shown only at creation — store them securely
