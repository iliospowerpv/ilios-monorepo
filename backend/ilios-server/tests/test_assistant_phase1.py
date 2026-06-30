"""Phase 1 tests for the AI Assistant's per-domain workspace-summary tools.

Pure unit style (Mock/monkeypatch, no live DB rows), mirroring tests/test_assistant_mvp.py.
Proves, for the 7 new site-scoped summary tools, that: (1) each wraps EXACTLY ONE existing read
service and returns its model_dump; (2) authorization is reproduced at the tool layer — an
out-of-scope/unknown site_id yields an honest 'unavailable' envelope and the wrapped service is
NEVER called; (3) diligence-derived tools additionally require Diligence view; (4) windowed tools
disclose and clamp their resolved window; (5) every new tool performs ZERO DB writes; (6) the new
names are catalogued, labelled, and pass the read-only guardrail.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from app.services.assistant import assistant_service, guardrails, tools


# --- Fakes -----------------------------------------------------------------------------------------

_SITE_TOOLS = [
    "get_site_telemetry_health",
    "get_site_diligence_reconciliation",
    "get_site_weather_readiness",
    "get_site_active_facts",
    "get_site_expected_summary",
    "get_site_inventory_reconciliation",
    "get_site_device_eligibility",
]
_DILIGENCE_TOOLS = ["get_site_diligence_reconciliation", "get_site_active_facts"]
_WINDOW_TOOLS = ["get_site_weather_readiness", "get_site_expected_summary"]

# tool name -> the tools.* attribute name of the single read service it wraps.
_WRAPPED = {
    "get_site_telemetry_health": "compute_site_telemetry_health",
    "get_site_diligence_reconciliation": "build_site_reconciliation",
    "get_site_weather_readiness": "compute_weather_readiness",
    "get_site_active_facts": "ProjectFactsService",
    "get_site_expected_summary": "compute_site_expected_period_effective",
    "get_site_inventory_reconciliation": "build_site_inventory_reconciliation",
    "get_site_device_eligibility": "compute_site_eligibility_diagnostics",
}


def _site():
    return SimpleNamespace(id=42, company_id=7, name="Acme PV")


def _user():
    return SimpleNamespace(id=1, has_platform_bypass=False)


def _no_write_db():
    return MagicMock(name="db_session")


def _assert_no_writes(db):
    for method in ("add", "add_all", "commit", "flush", "delete", "merge", "execute", "bulk_save_objects"):
        getattr(db, method).assert_not_called()


def _model(payload):
    """A stand-in pydantic response exposing ``model_dump(mode=...)``."""
    return SimpleNamespace(model_dump=lambda mode=None: dict(payload))


def _patch_visible_site(monkeypatch, site):
    monkeypatch.setattr(tools, "resolve_candidate_sites", lambda *a, **k: [site] if site else [])


def _patch_service_ok(monkeypatch, tool_name, recorder=None):
    """Monkeypatch the single service wrapped by ``tool_name`` with a recording fake."""
    attr = _WRAPPED[tool_name]
    if tool_name == "get_site_active_facts":
        class _FakeFactsService:
            def __init__(self, db):
                self.db = db

            def get_active_facts(self, site_id):
                if recorder is not None:
                    recorder["called_with"] = {"site_id": site_id}
                return [{"field": "dc_capacity_kw", "value": {"v": "5000"}}]

        monkeypatch.setattr(tools, attr, _FakeFactsService)
        return

    def _fake(*args, **kwargs):
        if recorder is not None:
            recorder["called_with"] = {"args": args, "kwargs": kwargs}
        return _model({"ok": tool_name})

    monkeypatch.setattr(tools, attr, _fake)


# --- 1. Catalog / guardrail / labels ---------------------------------------------------------------


def test_new_tools_are_catalogued_labelled_and_not_prohibited():
    for name in _SITE_TOOLS:
        assert name in tools.ALLOWED_TOOLS
        assert name in tools.TOOL_HANDLERS
        assert not guardrails.is_prohibited(name)
        assert name in assistant_service._TOOL_SOURCE_LABELS
        guardrails.assert_tool_allowed(name, tools.ALLOWED_TOOLS)  # must not raise


def test_new_specs_require_site_id():
    by_name = {s["function"]["name"]: s for s in tools.TOOL_SPECS}
    for name in _SITE_TOOLS:
        params = by_name[name]["function"]["parameters"]
        assert params.get("required") == ["site_id"]
        assert "site_id" in params["properties"]


# --- 2. Happy path: each tool wraps its one service and returns model_dump --------------------------


@pytest.mark.parametrize("name", _SITE_TOOLS)
def test_tool_dispatches_wrapped_service(monkeypatch, name):
    db = _no_write_db()
    site = _site()
    _patch_visible_site(monkeypatch, site)
    if name in _DILIGENCE_TOOLS:
        monkeypatch.setattr(tools, "can_view_diligence", lambda *a, **k: True)
    rec = {}
    _patch_service_ok(monkeypatch, name, rec)

    result = tools.dispatch_tool(db, _user(), name, {"site_id": 42})

    assert isinstance(result, dict)
    assert result.get("available") is not False  # not a denial envelope
    assert rec.get("called_with") is not None  # the wrapped service actually ran
    _assert_no_writes(db)


def test_active_facts_returns_site_scoped_envelope(monkeypatch):
    db = _no_write_db()
    site = _site()
    _patch_visible_site(monkeypatch, site)
    monkeypatch.setattr(tools, "can_view_diligence", lambda *a, **k: True)
    _patch_service_ok(monkeypatch, "get_site_active_facts")

    result = tools.dispatch_tool(db, _user(), "get_site_active_facts", {"site_id": 42})

    assert result["site_id"] == 42
    assert isinstance(result["facts"], list) and result["facts"]
    _assert_no_writes(db)


# --- 3. Authz reproduced: unknown/out-of-scope site never reaches the service ----------------------


@pytest.mark.parametrize("name", _SITE_TOOLS)
def test_out_of_scope_site_returns_envelope_and_never_calls_service(monkeypatch, name):
    db = _no_write_db()
    _patch_visible_site(monkeypatch, None)  # caller cannot see the requested id -> fail-closed
    service = Mock(name=_WRAPPED[name])
    monkeypatch.setattr(tools, _WRAPPED[name], service)

    result = tools.dispatch_tool(db, _user(), name, {"site_id": 999})

    assert result == {"available": False, "reason": "not_authorized_or_not_found", "site_id": 999}
    service.assert_not_called()
    _assert_no_writes(db)


@pytest.mark.parametrize("name", _SITE_TOOLS)
def test_missing_site_id_returns_unavailable(monkeypatch, name):
    db = _no_write_db()
    # resolve_candidate_sites must never even be consulted when no site_id is supplied.
    resolve = Mock(name="resolve_candidate_sites")
    monkeypatch.setattr(tools, "resolve_candidate_sites", resolve)
    service = Mock(name=_WRAPPED[name])
    monkeypatch.setattr(tools, _WRAPPED[name], service)

    result = tools.dispatch_tool(db, _user(), name, {})

    assert result["available"] is False
    assert result["site_id"] is None
    resolve.assert_not_called()
    service.assert_not_called()
    _assert_no_writes(db)


# --- 4. Diligence gate -----------------------------------------------------------------------------


@pytest.mark.parametrize("name", _DILIGENCE_TOOLS)
def test_diligence_denied_returns_not_permitted_and_never_calls_service(monkeypatch, name):
    db = _no_write_db()
    site = _site()
    _patch_visible_site(monkeypatch, site)
    monkeypatch.setattr(tools, "can_view_diligence", lambda *a, **k: False)
    service = Mock(name=_WRAPPED[name])
    monkeypatch.setattr(tools, _WRAPPED[name], service)

    result = tools.dispatch_tool(db, _user(), name, {"site_id": 42})

    assert result == {"available": False, "reason": "diligence_view_not_permitted", "site_id": 42}
    service.assert_not_called()
    _assert_no_writes(db)


# --- 5. Windowed tools: clamp + disclose -----------------------------------------------------------


def test_resolve_window_defaults_and_clamps():
    s, e, bucket, days = tools._resolve_window({})
    assert days == tools._DEFAULT_WINDOW_DAYS and bucket == tools._DEFAULT_BUCKET
    assert e.tzinfo is None and s.tzinfo is None  # naive-UTC (matches the wrapped endpoints)
    assert abs((e - s) - timedelta(days=days)) < timedelta(seconds=5)

    _, _, bucket2, days2 = tools._resolve_window({"days": 999, "bucket_size": "bogus"})
    assert days2 == tools._MAX_WINDOW_DAYS and bucket2 == tools._DEFAULT_BUCKET

    _, _, bucket3, days3 = tools._resolve_window({"days": 7, "bucket_size": "1d"})
    assert days3 == 7 and bucket3 == "1d"


@pytest.mark.parametrize("name", _WINDOW_TOOLS)
def test_windowed_tool_discloses_window_and_passes_naive_utc(monkeypatch, name):
    db = _no_write_db()
    site = _site()
    _patch_visible_site(monkeypatch, site)
    rec = {}
    _patch_service_ok(monkeypatch, name, rec)

    result = tools.dispatch_tool(db, _user(), name, {"site_id": 42, "days": 7, "bucket_size": "1d"})

    assert result["window"] == {
        "days": 7,
        "bucket_size": "1d",
        "start": result["window"]["start"],
        "end": result["window"]["end"],
    }
    kwargs = rec["called_with"]["kwargs"]
    assert kwargs["bucket_size"] == "1d"
    assert isinstance(kwargs["start"], datetime) and kwargs["start"].tzinfo is None
    assert isinstance(kwargs["end"], datetime) and kwargs["end"].tzinfo is None
    assert abs((kwargs["end"] - kwargs["start"]) - timedelta(days=7)) < timedelta(seconds=5)
    _assert_no_writes(db)


# --- 6. Zero-write proof across every new tool -----------------------------------------------------


def test_all_new_tools_perform_zero_writes(monkeypatch):
    db = _no_write_db()
    site = _site()
    _patch_visible_site(monkeypatch, site)
    monkeypatch.setattr(tools, "can_view_diligence", lambda *a, **k: True)
    for name in _SITE_TOOLS:
        _patch_service_ok(monkeypatch, name)
        result = tools.dispatch_tool(db, _user(), name, {"site_id": 42})
        assert isinstance(result, dict)
    _assert_no_writes(db)
