"""Unit tests for credential redaction (no DB / no FastAPI)."""
import logging

from app.security import redaction
from app.security.redaction import (
    REDACTED,
    RedactingFilter,
    fingerprint,
    is_secret_key,
    redact_mapping,
    redact_text,
)


class TestFingerprint:
    def test_none_or_empty_is_redacted(self):
        assert fingerprint(None) == REDACTED
        assert fingerprint("") == REDACTED

    def test_short_value_does_not_leak(self):
        out = fingerprint("abc")
        assert "abc" not in out
        assert "len=3" in out

    def test_long_value_keeps_only_tail(self):
        token = "supersecretvalue1234"
        out = fingerprint(token)
        assert token not in out
        assert out.endswith("1234(len=20)")
        assert "***" in out


class TestSecretKeyDetection:
    def test_obvious_secret_keys(self):
        for key in ("token", "password", "api_key", "Authorization", "SECRET"):
            assert is_secret_key(key), key

    def test_non_secret_keys(self):
        for key in ("name", "id", "company_id", "site_id", ""):
            assert not is_secret_key(key), key


class TestRedactMapping:
    def test_top_level_secret(self):
        out = redact_mapping({"token": "abc123", "name": "ok"})
        assert out["token"] == REDACTED
        assert out["name"] == "ok"

    def test_nested_dict_redacted(self):
        out = redact_mapping(
            {"credentials": {"token": "abc123", "username": "joe"}, "id": 1}
        )
        assert out["credentials"]["token"] == REDACTED
        # Nested non-secret keys preserved
        assert out["credentials"]["username"] == "joe"
        assert out["id"] == 1

    def test_list_of_dicts(self):
        out = redact_mapping(
            {"items": [{"api_key": "k1", "name": "a"}, {"name": "b"}]}
        )
        assert out["items"][0]["api_key"] == REDACTED
        assert out["items"][0]["name"] == "a"
        assert out["items"][1]["name"] == "b"


class TestRedactText:
    def test_inline_kv(self):
        msg = "calling provider with token=abc123def and id=5"
        out = redact_text(msg)
        assert "abc123def" not in out
        assert "token=" + REDACTED in out
        assert "id=5" in out

    def test_bearer_header(self):
        msg = "Authorization: Bearer veryLongTokenString12345"
        out = redact_text(msg)
        assert "veryLongTokenString12345" not in out
        assert "Bearer " + REDACTED in out

    def test_basic_header(self):
        msg = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
        out = redact_text(msg)
        assert "dXNlcjpwYXNzd29yZA==" not in out
        assert "Basic " + REDACTED in out


class TestRedactingFilter:
    def test_filter_scrubs_string_message(self):
        flt = RedactingFilter()
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname=__file__, lineno=1,
            msg="login token=mySecretValue42 ok", args=(), exc_info=None,
        )
        assert flt.filter(record) is True
        assert "mySecretValue42" not in record.getMessage()
        assert REDACTED in record.getMessage()

    def test_filter_scrubs_dict_args(self):
        flt = RedactingFilter()
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname=__file__, lineno=1,
            msg="payload=%s", args=({"token": "abc", "name": "x"},), exc_info=None,
        )
        flt.filter(record)
        # args was scrubbed
        assert record.args[0]["token"] == REDACTED
        assert record.args[0]["name"] == "x"

    def test_filter_never_raises(self, monkeypatch):
        # Even if redact_text blows up, filter must return True silently.
        def boom(_msg):
            raise RuntimeError("explode")

        monkeypatch.setattr(redaction, "redact_text", boom)
        flt = RedactingFilter()
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname=__file__, lineno=1,
            msg="hello", args=(), exc_info=None,
        )
        assert flt.filter(record) is True


class TestConfigureRedactionIdempotent:
    def test_double_install_attaches_filter_only_once(self):
        # configure_redaction is module-global; only assert root has at least one filter
        # and that re-running it does not stack duplicates beyond the singleton.
        redaction.configure_redaction()
        root = logging.getLogger()
        count_before = sum(1 for f in root.filters if isinstance(f, RedactingFilter))
        redaction.configure_redaction()
        count_after = sum(1 for f in root.filters if isinstance(f, RedactingFilter))
        assert count_after == count_before
        assert count_after >= 1
