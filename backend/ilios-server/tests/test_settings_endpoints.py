"""Tests for the superuser-only System Settings endpoints.

Covers:
- Audit Logs read endpoint (shape, pagination bounds, 403 for non-superuser).
- Third-party Service Health dashboard (honest states, no secret values, 403).
- Architecture database introspection + allowlisted docs (traversal-safe, 403).
"""
from contextlib import contextmanager
from types import SimpleNamespace

from app.helpers.authentication import get_current_user
from app.helpers.authorization.module_based.base import get_current_admin_user

SUPERUSER = SimpleNamespace(id=1, has_platform_bypass=True)
NON_SUPERUSER = SimpleNamespace(id=2, has_platform_bypass=False)


@contextmanager
def _as_superuser(client):
    client.app.dependency_overrides[get_current_admin_user] = lambda: SUPERUSER
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(get_current_admin_user, None)


@contextmanager
def _as_non_superuser(client):
    # Let the real get_current_admin_user run against a non-bypass user -> 403.
    client.app.dependency_overrides[get_current_user] = lambda: NON_SUPERUSER
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)


# --- Audit Logs ------------------------------------------------------------------
def test_audit_logs_shape_and_pagination(client):
    with _as_superuser(client):
        resp = client.get("/api/settings/audit-logs/?skip=0&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body["skip"] == 0
    assert body["limit"] == 5
    assert isinstance(body["total"], int)
    assert isinstance(body["items"], list)
    for item in body["items"]:
        assert set(item).issuperset(
            {"id", "user_name", "user_email", "source", "action", "is_success", "details", "created_at"}
        )


def test_audit_logs_rejects_out_of_range_params(client):
    with _as_superuser(client):
        assert client.get("/api/settings/audit-logs/?limit=9999").status_code == 422
        assert client.get("/api/settings/audit-logs/?skip=-1").status_code == 422
        assert client.get("/api/settings/audit-logs/?limit=0").status_code == 422


def test_audit_logs_forbidden_for_non_superuser(client):
    with _as_non_superuser(client):
        assert client.get("/api/settings/audit-logs/").status_code == 403


# --- Service Health --------------------------------------------------------------
def test_service_health_shape_and_honesty(client):
    with _as_superuser(client):
        resp = client.get("/api/settings/service-health/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == len(body["services"])
    keys = {s["key"] for s in body["services"]}
    # Core infra + key external providers must be represented.
    assert {"postgres", "redis", "object_storage", "mailgun", "powerbi", "rombus"} <= keys

    for svc in body["services"]:
        assert set(svc).issuperset(
            {"key", "name", "purpose", "category", "required", "configured", "config_source", "reachable"}
        )
        # reachable is tri-state: True / False / None (never fabricated).
        assert svc["reachable"] in (True, False, None)
        assert isinstance(svc["config_source"], list)

    # Postgres is probed via the live test session -> reachable True.
    postgres = next(s for s in body["services"] if s["key"] == "postgres")
    assert postgres["reachable"] is True
    assert postgres["required"] is True

    # External providers report configuration-only (not probed).
    mailgun = next(s for s in body["services"] if s["key"] == "mailgun")
    assert mailgun["reachable"] is None


def test_service_health_never_leaks_secret_values(client):
    """config_source must contain env/setting NAMES only, never resolved values."""
    from app.settings import settings

    sensitive_values = [
        v
        for v in (
            getattr(settings, "mailgun_api_key", None),
            getattr(settings, "rombus_api_key", None),
            getattr(settings, "ml_api_key", None),
            getattr(settings, "pbi_client_secret", None),
        )
        if v
    ]
    with _as_superuser(client):
        raw = client.get("/api/settings/service-health/").text
    for secret in sensitive_values:
        assert secret not in raw


def test_service_health_forbidden_for_non_superuser(client):
    with _as_non_superuser(client):
        assert client.get("/api/settings/service-health/").status_code == 403


def test_service_health_sanitizes_probe_error_text(client, monkeypatch):
    """A probe exception that embeds a secret must never reach the response body."""
    from app.routers.settings import service_health

    leaked = "api_key=SUPER_SECRET_TOKEN_abc123 postgres://user:hunter2@db:5432"

    def _boom() -> tuple:
        raise RuntimeError(leaked)

    # Force storage to be "configured" so the probe runs, then make it explode.
    monkeypatch.setattr(service_health, "_bucket_id", lambda: "test-bucket")
    monkeypatch.setattr(service_health, "_probe_storage", _boom)

    with _as_superuser(client):
        resp = client.get("/api/settings/service-health/")
    assert resp.status_code == 200
    assert "SUPER_SECRET_TOKEN_abc123" not in resp.text
    assert "hunter2" not in resp.text

    storage = next(s for s in resp.json()["services"] if s["key"] == "object_storage")
    assert storage["reachable"] is False
    # Generic, secret-free message only.
    assert storage["error_summary"] == "Object storage probe failed (see server logs)."


def test_redact_masks_common_secret_shapes():
    """Server-log redaction must scrub URL creds, key=value secrets and Bearer tokens."""
    from app.routers.settings.service_health import _redact

    out = _redact(
        "api_key=SUPER_SECRET_TOKEN_abc123 "
        "Authorization: Bearer eyJhbGciOi.JZ.sig "
        "client_secret = topsecret99 "
        "postgres://user:hunter2@db:5432/app"
    )
    assert "SUPER_SECRET_TOKEN_abc123" not in out
    assert "eyJhbGciOi.JZ.sig" not in out
    assert "topsecret99" not in out
    assert "hunter2" not in out
    # Key names are retained for debuggability.
    assert "api_key=" in out
    assert "client_secret" in out


def test_service_health_probe_timeout_is_bounded(client, monkeypatch):
    """A hung probe must not block the request beyond the probe timeout."""
    import time

    from app.routers.settings import service_health

    def _hang() -> tuple:
        time.sleep(2.0)
        return True, None

    monkeypatch.setattr(service_health, "_PROBE_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(service_health, "_bucket_id", lambda: "test-bucket")
    monkeypatch.setattr(service_health, "_probe_storage", _hang)

    started = time.monotonic()
    with _as_superuser(client):
        resp = client.get("/api/settings/service-health/")
    elapsed = time.monotonic() - started

    assert resp.status_code == 200
    # Returned well before the 2s hang (timeout 0.2s + small overhead).
    assert elapsed < 1.5
    storage = next(s for s in resp.json()["services"] if s["key"] == "object_storage")
    assert storage["reachable"] is False
    assert storage["error_summary"].startswith("Probe timed out")


# --- Architecture ----------------------------------------------------------------
def test_architecture_database_structure(client):
    with _as_superuser(client):
        resp = client.get("/api/settings/architecture/database")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_name"] == "public"
    assert body["table_count"] == len(body["tables"])
    assert body["table_count"] > 0
    sample = body["tables"][0]
    assert {"name", "column_count", "columns"} <= set(sample)
    if sample["columns"]:
        assert {"name", "data_type", "is_nullable"} <= set(sample["columns"][0])


def test_architecture_docs_list_and_read(client):
    with _as_superuser(client):
        listing = client.get("/api/settings/architecture/docs")
        assert listing.status_code == 200
        docs = listing.json()["documents"]
        assert len(docs) > 0
        key = docs[0]["key"]
        content_resp = client.get(f"/api/settings/architecture/docs/{key}")
    assert content_resp.status_code == 200
    content = content_resp.json()
    assert content["key"] == key
    assert isinstance(content["content"], str)
    assert "truncated" in content


def test_architecture_doc_unknown_key_is_404(client):
    with _as_superuser(client):
        assert client.get("/api/settings/architecture/docs/not-a-real-doc").status_code == 404


def test_architecture_forbidden_for_non_superuser(client):
    with _as_non_superuser(client):
        assert client.get("/api/settings/architecture/database").status_code == 403
        assert client.get("/api/settings/architecture/docs").status_code == 403
