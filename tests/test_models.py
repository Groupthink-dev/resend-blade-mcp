"""Tests for models: write gate, credential scrubbing, attachment validation."""

from __future__ import annotations

from unittest.mock import patch

from resend_blade_mcp.models import (
    is_write_enabled,
    require_write,
    scrub_secrets,
    validate_attachment,
)


class TestWriteGate:
    def test_disabled_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert not is_write_enabled()

    def test_disabled_when_false(self) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            assert not is_write_enabled()

    def test_enabled_when_true(self) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            assert is_write_enabled()

    def test_enabled_case_insensitive(self) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "True"}):
            assert is_write_enabled()
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "TRUE"}):
            assert is_write_enabled()

    def test_require_write_returns_error_when_disabled(self) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "false"}):
            result = require_write()
            assert result is not None
            assert "Error:" in result
            assert "RESEND_WRITE_ENABLED" in result

    def test_require_write_returns_none_when_enabled(self) -> None:
        with patch.dict("os.environ", {"RESEND_WRITE_ENABLED": "true"}):
            assert require_write() is None


class TestScrubSecrets:
    def test_scrubs_api_key(self) -> None:
        text = "Auth failed with key re_abc123XYZ_long_key"
        result = scrub_secrets(text)
        assert "re_abc123XYZ_long_key" not in result
        assert "re_****" in result

    def test_scrubs_bearer_token(self) -> None:
        text = "Authorization: Bearer re_test_key_12345678"
        result = scrub_secrets(text)
        assert "re_test_key_12345678" not in result
        assert "Bearer re_****" in result

    def test_preserves_non_secret_text(self) -> None:
        text = "Connection timed out to api.resend.com"
        assert scrub_secrets(text) == text

    def test_scrubs_multiple_keys(self) -> None:
        text = "Keys: re_key_one_abcdef and re_key_two_ghijkl"
        result = scrub_secrets(text)
        assert "re_key_one_abcdef" not in result
        assert "re_key_two_ghijkl" not in result


class TestValidateAttachment:
    def test_accepts_base64_content(self) -> None:
        att = {"content": "SGVsbG8=", "filename": "test.txt"}
        assert validate_attachment(att) is None

    def test_accepts_https_url(self) -> None:
        att = {"path": "https://example.com/file.pdf", "filename": "file.pdf"}
        assert validate_attachment(att) is None

    def test_accepts_http_url(self) -> None:
        att = {"path": "http://example.com/file.pdf", "filename": "file.pdf"}
        assert validate_attachment(att) is None

    def test_rejects_absolute_unix_path(self) -> None:
        att = {"path": "/etc/passwd", "filename": "passwd"}
        result = validate_attachment(att)
        assert result is not None
        assert "Error:" in result
        assert "Filesystem" in result

    def test_rejects_home_path(self) -> None:
        att = {"path": "~/secrets.txt", "filename": "secrets.txt"}
        result = validate_attachment(att)
        assert result is not None
        assert "Error:" in result

    def test_rejects_relative_path(self) -> None:
        att = {"path": "./local.txt", "filename": "local.txt"}
        result = validate_attachment(att)
        assert result is not None
        assert "Error:" in result

    def test_rejects_parent_relative_path(self) -> None:
        att = {"path": "../../../etc/passwd", "filename": "passwd"}
        result = validate_attachment(att)
        assert result is not None
        assert "Error:" in result

    def test_rejects_windows_path(self) -> None:
        att = {"path": "C:\\Windows\\system.ini", "filename": "system.ini"}
        result = validate_attachment(att)
        assert result is not None
        assert "Error:" in result

    def test_rejects_unc_path(self) -> None:
        att = {"path": "\\\\server\\share\\file.txt", "filename": "file.txt"}
        result = validate_attachment(att)
        assert result is not None
        assert "Error:" in result

    def test_rejects_missing_filename(self) -> None:
        att = {"content": "SGVsbG8="}
        result = validate_attachment(att)
        assert result is not None
        assert "filename" in result

    def test_rejects_no_content_or_path(self) -> None:
        att = {"filename": "test.txt"}
        result = validate_attachment(att)
        assert result is not None
        assert "Error:" in result

    def test_rejects_non_url_string(self) -> None:
        att = {"path": "just-a-string", "filename": "test.txt"}
        result = validate_attachment(att)
        assert result is not None
        assert "HTTPS URL" in result
