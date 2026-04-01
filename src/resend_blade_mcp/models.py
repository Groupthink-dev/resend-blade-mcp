"""Shared constants, write-gate, credential scrubbing, and attachment validation."""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# Resend API
BASE_URL = "https://api.resend.com"
USER_AGENT = "resend-blade-mcp/0.1.0"

# Default limit for list operations (token efficiency)
DEFAULT_LIMIT = 20

# Maximum batch size for send_batch
MAX_BATCH_SIZE = 100

# Template/email body truncation limit (characters)
MAX_BODY_CHARS = 50_000

# Rate limit (informational — Resend enforces 5 req/s per team)
RATE_LIMIT_RPS = 5

# Webhook event types (for validation and documentation)
WEBHOOK_EVENTS = [
    "email.sent",
    "email.delivered",
    "email.bounced",
    "email.complained",
    "email.delivery_delayed",
    "email.failed",
    "email.opened",
    "email.clicked",
    "email.received",
    "email.scheduled",
    "email.suppressed",
    "domain.created",
    "domain.updated",
    "domain.deleted",
    "contact.created",
    "contact.updated",
    "contact.deleted",
]

# Resend API key pattern for credential scrubbing
_RE_API_KEY_PATTERN = re.compile(r"re_[a-zA-Z0-9_]{8,}")
_BEARER_PATTERN = re.compile(r"Bearer\s+re_[a-zA-Z0-9_]{8,}", re.IGNORECASE)

# Filesystem path patterns to reject in attachments
_FILESYSTEM_PATTERNS = [
    re.compile(r"^/"),  # Unix absolute
    re.compile(r"^~"),  # Home directory
    re.compile(r"^\./"),  # Relative current
    re.compile(r"^\.\./"),  # Relative parent
    re.compile(r"^[A-Za-z]:\\"),  # Windows drive
    re.compile(r"^\\\\"),  # UNC path
]


def is_write_enabled() -> bool:
    """Check if write operations are enabled via env var."""
    return os.environ.get("RESEND_WRITE_ENABLED", "").lower() == "true"


def require_write() -> str | None:
    """Return an error message if writes are disabled, else None."""
    if not is_write_enabled():
        return "Error: Write operations are disabled. Set RESEND_WRITE_ENABLED=true to enable."
    return None


def scrub_secrets(text: str) -> str:
    """Remove Resend API keys and bearer tokens from text to prevent leakage."""
    text = _BEARER_PATTERN.sub("Bearer re_****", text)
    text = _RE_API_KEY_PATTERN.sub("re_****", text)
    return text


def validate_attachment(attachment: dict[str, str]) -> str | None:
    """Validate an attachment dict. Returns error message or None if valid.

    Accepts:
      - {"content": "<base64>", "filename": "name.pdf"}
      - {"path": "https://example.com/file.pdf", "filename": "name.pdf"}

    Rejects filesystem paths in the ``path`` field to prevent exfiltration.
    """
    if "filename" not in attachment:
        return "Error: Attachment missing required 'filename' field."

    if "content" in attachment:
        return None  # base64 content is always safe

    if "path" in attachment:
        path = attachment["path"]
        # Allowlist: only HTTP(S) URLs
        if path.startswith(("http://", "https://")):
            return None
        # Reject anything that looks like a filesystem path
        for pattern in _FILESYSTEM_PATTERNS:
            if pattern.match(path):
                return (
                    "Error: Filesystem paths are not allowed in attachments (security). "
                    f"Use base64 'content' or an HTTPS URL. Rejected: {path[:50]}"
                )
        # Reject anything else that isn't a URL
        return f"Error: Attachment 'path' must be an HTTPS URL. Got: {path[:50]}"

    return "Error: Attachment must have either 'content' (base64) or 'path' (HTTPS URL)."
