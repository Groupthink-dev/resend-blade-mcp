"""Token-efficient output formatters for Resend API responses.

Design principles:
- Concise by default (one line per item)
- Null fields omitted
- Lists capped and annotated with total count
- Pipe-delimited fields for compact representation
"""

from __future__ import annotations

from typing import Any

from resend_blade_mcp.models import DEFAULT_LIMIT, MAX_BODY_CHARS


def _truncate(text: str, max_chars: int = MAX_BODY_CHARS) -> str:
    """Truncate text with annotation if too long."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n… truncated ({len(text)} chars total)"


def _cap_list(lines: list[str], total: int | None, limit: int) -> list[str]:
    """Append cap annotation if more items exist."""
    actual = total if total is not None else len(lines)
    if actual > limit:
        lines.append(f"… {actual - limit} more (use limit= to see more)")
    return lines


# ===================================================================
# SENDING
# ===================================================================


def format_send_result(result: dict[str, Any]) -> str:
    """Format send response: single line with ID."""
    email_id = result.get("id", "?")
    return f"Sent. id={email_id}"


def format_batch_result(result: dict[str, Any]) -> str:
    """Format batch send response."""
    data = result.get("data", [])
    if not data:
        return "Batch sent (no IDs returned)."
    ids = [d.get("id", "?") for d in data]
    return f"Sent {len(ids)} emails. IDs: {', '.join(ids)}"


def format_email(email: dict[str, Any]) -> str:
    """Format a single email for detail view."""
    parts: list[str] = []
    parts.append(f"id={email.get('id', '?')}")
    if email.get("from"):
        parts.append(f"from: {email['from']}")
    if email.get("to"):
        to_list = email["to"] if isinstance(email["to"], list) else [email["to"]]
        parts.append(f"to: {', '.join(to_list)}")
    if email.get("subject"):
        parts.append(f"subject: {email['subject']}")
    if email.get("last_event"):
        parts.append(f"status: {email['last_event']}")
    if email.get("created_at"):
        parts.append(f"created: {email['created_at'][:16]}")
    if email.get("scheduled_at"):
        parts.append(f"scheduled: {email['scheduled_at'][:16]}")

    result = " | ".join(parts)

    # Append body if present
    if email.get("html"):
        result += f"\n\n{_truncate(email['html'])}"
    elif email.get("text"):
        result += f"\n\n{_truncate(email['text'])}"

    return result


def format_email_list(emails: list[dict[str, Any]], total: int | None = None, limit: int = DEFAULT_LIMIT) -> str:
    """Format email list: date | from | subject | status | id."""
    if not emails:
        return "No emails found."

    shown = emails[:limit]
    lines: list[str] = []
    for e in shown:
        parts: list[str] = []
        if e.get("created_at"):
            parts.append(e["created_at"][:16])
        parts.append(e.get("from", "?"))
        parts.append(e.get("subject", "(no subject)"))
        if e.get("last_event"):
            parts.append(e["last_event"])
        parts.append(f"id={e.get('id', '?')}")
        lines.append(" | ".join(parts))

    return "\n".join(_cap_list(lines, total, limit))


def format_cancel_result(result: dict[str, Any]) -> str:
    """Format cancel response."""
    email_id = result.get("id", "?")
    return f"Cancelled. id={email_id}"


# ===================================================================
# CONTACTS
# ===================================================================


def format_contact(contact: dict[str, Any]) -> str:
    """Format a single contact."""
    parts: list[str] = []
    parts.append(contact.get("email", "?"))
    name_parts = []
    if contact.get("first_name"):
        name_parts.append(contact["first_name"])
    if contact.get("last_name"):
        name_parts.append(contact["last_name"])
    if name_parts:
        parts.append(" ".join(name_parts))
    if contact.get("unsubscribed"):
        parts.append("unsubscribed")
    parts.append(f"id={contact.get('id', '?')}")
    return " | ".join(parts)


def format_contact_list(contacts: list[dict[str, Any]], total: int | None = None, limit: int = DEFAULT_LIMIT) -> str:
    """Format contact list: email | name | status | id."""
    if not contacts:
        return "No contacts found."

    shown = contacts[:limit]
    lines = [format_contact(c) for c in shown]
    return "\n".join(_cap_list(lines, total, limit))


def format_contact_result(result: dict[str, Any]) -> str:
    """Format contact create/update/delete response."""
    contact_id = result.get("id", "?")
    return f"OK. id={contact_id}"


# ===================================================================
# SEGMENTS
# ===================================================================


def format_segment(segment: dict[str, Any]) -> str:
    """Format a single segment."""
    parts: list[str] = []
    parts.append(segment.get("name", "?"))
    parts.append(f"id={segment.get('id', '?')}")
    if segment.get("created_at"):
        parts.append(f"created: {segment['created_at'][:10]}")
    return " | ".join(parts)


def format_segment_list(segments: list[dict[str, Any]]) -> str:
    """Format segment list."""
    if not segments:
        return "No segments found."
    return "\n".join(format_segment(s) for s in segments)


def format_segment_result(result: dict[str, Any]) -> str:
    """Format segment create/delete response."""
    segment_id = result.get("id", "?")
    return f"OK. id={segment_id}"


# ===================================================================
# BROADCASTS
# ===================================================================


def format_broadcast(broadcast: dict[str, Any]) -> str:
    """Format a single broadcast."""
    parts: list[str] = []
    if broadcast.get("name"):
        parts.append(broadcast["name"])
    parts.append(broadcast.get("subject", "(no subject)"))
    parts.append(broadcast.get("status", "?"))
    if broadcast.get("sent_at"):
        parts.append(f"sent: {broadcast['sent_at'][:16]}")
    elif broadcast.get("scheduled_at"):
        parts.append(f"scheduled: {broadcast['scheduled_at'][:16]}")
    elif broadcast.get("created_at"):
        parts.append(f"created: {broadcast['created_at'][:16]}")
    parts.append(f"id={broadcast.get('id', '?')}")
    return " | ".join(parts)


def format_broadcast_list(broadcasts: list[dict[str, Any]]) -> str:
    """Format broadcast list."""
    if not broadcasts:
        return "No broadcasts found."
    return "\n".join(format_broadcast(b) for b in broadcasts)


def format_broadcast_result(result: dict[str, Any]) -> str:
    """Format broadcast create/send/delete response."""
    broadcast_id = result.get("id", "?")
    return f"OK. id={broadcast_id}"


# ===================================================================
# TEMPLATES
# ===================================================================


def format_template_summary(template: dict[str, Any]) -> str:
    """Format template for list view (no body)."""
    parts: list[str] = []
    parts.append(template.get("name", "?"))
    if template.get("subject"):
        parts.append(f"subject: {template['subject']}")
    if template.get("status"):
        parts.append(template["status"])
    parts.append(f"id={template.get('id', '?')}")
    return " | ".join(parts)


def format_template_detail(template: dict[str, Any]) -> str:
    """Format template for detail view (includes body)."""
    header = format_template_summary(template)
    body = ""
    if template.get("html"):
        body = f"\n\n{_truncate(template['html'], 2000)}"
    return header + body


def format_template_list(templates: list[dict[str, Any]]) -> str:
    """Format template list (compact, no body)."""
    if not templates:
        return "No templates found."
    items = templates if isinstance(templates, list) else templates.get("data", [])
    return "\n".join(format_template_summary(t) for t in items)


def format_template_result(result: dict[str, Any]) -> str:
    """Format template create/publish response."""
    template_id = result.get("id", "?")
    return f"OK. id={template_id}"


# ===================================================================
# DOMAINS
# ===================================================================


def format_domain(domain: dict[str, Any]) -> str:
    """Format a single domain with DNS records."""
    parts: list[str] = []
    parts.append(domain.get("name", "?"))
    parts.append(f"status: {domain.get('status', '?')}")
    if domain.get("region"):
        parts.append(f"region: {domain['region']}")
    parts.append(f"id={domain.get('id', '?')}")

    result = " | ".join(parts)

    # Append DNS records if present
    records = domain.get("records", [])
    if records:
        result += f"\n  DNS records ({len(records)}):"
        for r in records:
            rec_type = r.get("type", "?")
            rec_name = r.get("name", "?")
            rec_value = r.get("value", "?")
            rec_status = r.get("status", "?")
            result += f"\n    {r.get('record', '?')} {rec_type} {rec_name} → {rec_value} [{rec_status}]"

    return result


def format_domain_list(domains: list[dict[str, Any]]) -> str:
    """Format domain list (compact, no DNS records)."""
    if not domains:
        return "No domains found."
    items = domains if isinstance(domains, list) else domains.get("data", [])
    lines: list[str] = []
    for d in items:
        parts: list[str] = []
        parts.append(d.get("name", "?"))
        parts.append(f"status: {d.get('status', '?')}")
        if d.get("region"):
            parts.append(f"region: {d['region']}")
        parts.append(f"id={d.get('id', '?')}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def format_domain_result(result: dict[str, Any]) -> str:
    """Format domain add/verify response."""
    return format_domain(result)


# ===================================================================
# WEBHOOKS
# ===================================================================


def format_webhook(webhook: dict[str, Any]) -> str:
    """Format a single webhook."""
    parts: list[str] = []
    parts.append(webhook.get("endpoint", "?"))
    events = webhook.get("events", [])
    if events:
        parts.append(f"events: {', '.join(events)}")
    if webhook.get("status"):
        parts.append(webhook["status"])
    parts.append(f"id={webhook.get('id', '?')}")
    return " | ".join(parts)


def format_webhook_list(webhooks: list[dict[str, Any]]) -> str:
    """Format webhook list."""
    if not webhooks:
        return "No webhooks found."
    items = webhooks if isinstance(webhooks, list) else webhooks.get("data", [])
    return "\n".join(format_webhook(w) for w in items)


def format_webhook_result(result: dict[str, Any]) -> str:
    """Format webhook create response (includes signing secret)."""
    parts: list[str] = []
    parts.append(f"id={result.get('id', '?')}")
    if result.get("signing_secret"):
        parts.append(f"signing_secret={result['signing_secret']}")
        parts.append("(save this — shown only once)")
    return " | ".join(parts)


# ===================================================================
# LOGS
# ===================================================================


def format_log_list(logs: list[dict[str, Any]]) -> str:
    """Format API log list."""
    if not logs:
        return "No logs found."
    items = logs if isinstance(logs, list) else logs.get("data", [])
    lines: list[str] = []
    for log in items:
        parts: list[str] = []
        if log.get("created_at"):
            parts.append(log["created_at"][:19])
        parts.append(f"{log.get('method', '?')} {log.get('endpoint', '?')}")
        if log.get("response_status"):
            parts.append(str(log["response_status"]))
        parts.append(f"id={log.get('id', '?')}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)
