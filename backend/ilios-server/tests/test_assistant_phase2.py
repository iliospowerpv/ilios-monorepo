"""Phase 2 tests for the AI Assistant's Data Room awareness tools (Task #93).

Pure unit style (Mock/monkeypatch, no live DB rows), mirroring tests/test_assistant_phase1.py.
Proves, for the 4 new Data-Room site-scoped tools, that: (1) each is catalogued, labelled, spec'd
with a required site_id, and passes the read-only guardrail; (2) authorization is reproduced at the
tool layer — an out-of-scope/unknown site_id yields an honest 'unavailable' envelope and the wrapped
service is NEVER called; (3) every one additionally requires Diligence view; (4) the happy path
wraps its one read service and discloses site scope; (5) every new tool performs ZERO DB writes.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from app.services.assistant import assistant_service, guardrails, tools


_DATA_ROOM_TOOLS = [
    "get_site_data_room_guidance",
    "get_site_expected_documents",
    "get_site_data_room_documents",
    "get_site_data_room_templates",
]


def _site():
    return SimpleNamespace(id=42, company_id=7, name="Acme PV")


def _user():
    return SimpleNamespace(id=1, has_platform_bypass=False)


def _no_write_db():
    return MagicMock(name="db_session")


def _assert_no_writes(db):
    for method in ("add", "add_all", "commit", "flush", "delete", "merge", "execute", "bulk_save_objects"):
        getattr(db, method).assert_not_called()


def _patch_visible_site(monkeypatch, site):
    monkeypatch.setattr(tools, "resolve_candidate_sites", lambda *a, **k: [site] if site else [])


def _patch_diligence(monkeypatch, allowed):
    monkeypatch.setattr(tools, "can_view_diligence", lambda *a, **k: allowed)


# --- Fakes for each wrapped read service -----------------------------------------------------------


class _FakeGuidanceService:
    def __init__(self, db):
        self.db = db

    def build_guidance(self, site_id):
        return {
            "items": [
                {"stage": "Acquisition", "expected": 3, "present": 1, "missing": 2},
            ],
            "missing_documents": [{"name": "Title Report", "stage": "Acquisition"}],
        }


class _FakeDocumentSectionCRUD:
    def __init__(self, db):
        self.db = db

    def get_site_sections(self, site_id):
        return [SimpleNamespace(id=11, name=SimpleNamespace(name="site_stage1"))]


class _FakeDocumentCRUD:
    def __init__(self, db):
        self.db = db

    def get_site_documents_ordered_by_name(self, site_id):
        return [
            SimpleNamespace(
                id=501,
                identity_name="Site Lease",
                identity_kind="site_lease",
                identity_aliases=["Lease Agreement"],
                section_id=11,
                section=SimpleNamespace(name=SimpleNamespace(value="Acquisition")),
                is_archived=False,
                files_count=2,
                files=[
                    SimpleNamespace(version_number=1, deleted=False),
                    SimpleNamespace(version_number=2, deleted=False),
                    SimpleNamespace(version_number=3, deleted=True),
                ],
            )
        ]


class _FakeTemplateCRUD:
    def __init__(self, db):
        self.db = db

    def get_by_company(self, company_id, include_archived=False):
        return [
            SimpleNamespace(
                id=9,
                name="Standard Solar",
                description="Default structure",
                is_archived=False,
                structure={
                    "sections": [
                        {"documents": [{}, {}], "subsections": [{"documents": [{}]}]},
                        {"documents": [{}]},
                    ]
                },
            )
        ]


def _patch_all_services(monkeypatch):
    monkeypatch.setattr(tools, "DataRoomGuidanceService", _FakeGuidanceService)
    monkeypatch.setattr(tools, "DocumentSectionCRUD", _FakeDocumentSectionCRUD)
    monkeypatch.setattr(tools, "DocumentCRUD", _FakeDocumentCRUD)
    monkeypatch.setattr(tools, "DataRoomTemplateCRUD", _FakeTemplateCRUD)
    monkeypatch.setattr(
        tools, "get_expected_documents_for_section", lambda section: [{"kind": "x", "name": "X"}]
    )


# --- 1. Catalog / guardrail / labels / specs -------------------------------------------------------


def test_data_room_tools_are_catalogued_labelled_and_not_prohibited():
    for name in _DATA_ROOM_TOOLS:
        assert name in tools.ALLOWED_TOOLS
        assert name in tools.TOOL_HANDLERS
        assert not guardrails.is_prohibited(name)
        assert name in assistant_service._TOOL_SOURCE_LABELS
        guardrails.assert_tool_allowed(name, tools.ALLOWED_TOOLS)  # must not raise


def test_data_room_specs_require_site_id():
    by_name = {s["function"]["name"]: s for s in tools.TOOL_SPECS}
    for name in _DATA_ROOM_TOOLS:
        params = by_name[name]["function"]["parameters"]
        assert params.get("required") == ["site_id"]
        assert "site_id" in params["properties"]


# --- 2. Authz reproduced: unknown/out-of-scope site never reaches the service ----------------------


@pytest.mark.parametrize("name", _DATA_ROOM_TOOLS)
def test_out_of_scope_site_returns_envelope_and_never_calls_service(monkeypatch, name):
    db = _no_write_db()
    _patch_visible_site(monkeypatch, None)  # caller cannot see the requested id -> fail-closed
    # Wrap every service in a tripwire Mock — none may be constructed/called.
    guidance = Mock(name="DataRoomGuidanceService")
    docs = Mock(name="DocumentCRUD")
    templates = Mock(name="DataRoomTemplateCRUD")
    monkeypatch.setattr(tools, "DataRoomGuidanceService", guidance)
    monkeypatch.setattr(tools, "DocumentCRUD", docs)
    monkeypatch.setattr(tools, "DataRoomTemplateCRUD", templates)

    result = tools.dispatch_tool(db, _user(), name, {"site_id": 999})

    assert result == {"available": False, "reason": "not_authorized_or_not_found", "site_id": 999}
    guidance.assert_not_called()
    docs.assert_not_called()
    templates.assert_not_called()
    _assert_no_writes(db)


@pytest.mark.parametrize("name", _DATA_ROOM_TOOLS)
def test_missing_site_id_returns_unavailable(monkeypatch, name):
    db = _no_write_db()
    resolve = Mock(name="resolve_candidate_sites")
    monkeypatch.setattr(tools, "resolve_candidate_sites", resolve)

    result = tools.dispatch_tool(db, _user(), name, {})

    assert result["available"] is False
    assert result["site_id"] is None
    resolve.assert_not_called()
    _assert_no_writes(db)


# --- 3. Diligence gate — all four require Diligence view -------------------------------------------


@pytest.mark.parametrize("name", _DATA_ROOM_TOOLS)
def test_diligence_denied_returns_not_permitted_and_never_calls_service(monkeypatch, name):
    db = _no_write_db()
    _patch_visible_site(monkeypatch, _site())
    _patch_diligence(monkeypatch, False)
    guidance = Mock(name="DataRoomGuidanceService")
    docs = Mock(name="DocumentCRUD")
    templates = Mock(name="DataRoomTemplateCRUD")
    monkeypatch.setattr(tools, "DataRoomGuidanceService", guidance)
    monkeypatch.setattr(tools, "DocumentCRUD", docs)
    monkeypatch.setattr(tools, "DataRoomTemplateCRUD", templates)

    result = tools.dispatch_tool(db, _user(), name, {"site_id": 42})

    assert result == {"available": False, "reason": "diligence_view_not_permitted", "site_id": 42}
    guidance.assert_not_called()
    docs.assert_not_called()
    templates.assert_not_called()
    _assert_no_writes(db)


# --- 4. Happy path: wraps the read service and discloses site scope --------------------------------


def test_guidance_returns_site_scoped_envelope(monkeypatch):
    db = _no_write_db()
    _patch_visible_site(monkeypatch, _site())
    _patch_diligence(monkeypatch, True)
    _patch_all_services(monkeypatch)

    result = tools.dispatch_tool(db, _user(), "get_site_data_room_guidance", {"site_id": 42})

    assert result["site_id"] == 42
    assert result["items"] and result["items"][0]["missing"] == 2
    assert result["missing_documents"][0]["name"] == "Title Report"
    _assert_no_writes(db)


def test_expected_documents_correlates_section_ids(monkeypatch):
    db = _no_write_db()
    _patch_visible_site(monkeypatch, _site())
    _patch_diligence(monkeypatch, True)
    _patch_all_services(monkeypatch)

    result = tools.dispatch_tool(db, _user(), "get_site_expected_documents", {"site_id": 42})

    assert result["site_id"] == 42
    by_key = {item["section_key"]: item for item in result["items"]}
    assert by_key["site_stage1"]["section_id"] == 11
    assert by_key["site_stage1"]["expected_documents"]
    # Sections with no expected catalog entries are omitted, never invented.
    assert all(item["expected_documents"] for item in result["items"])
    _assert_no_writes(db)


def test_documents_reports_identity_and_latest_version(monkeypatch):
    db = _no_write_db()
    _patch_visible_site(monkeypatch, _site())
    _patch_diligence(monkeypatch, True)
    _patch_all_services(monkeypatch)

    result = tools.dispatch_tool(db, _user(), "get_site_data_room_documents", {"site_id": 42})

    assert result["site_id"] == 42
    doc = result["items"][0]
    assert doc["document_id"] == 501
    assert doc["display_name"] == "Site Lease"
    assert doc["kind"] == "site_lease"
    assert doc["aliases"] == ["Lease Agreement"]
    assert doc["section_name"] == "Acquisition"
    assert doc["version_count"] == 2
    # Latest version ignores the deleted v3 -> highest non-deleted is 2.
    assert doc["latest_version"] == 2
    _assert_no_writes(db)


def test_templates_summarizes_structure_counts(monkeypatch):
    db = _no_write_db()
    _patch_visible_site(monkeypatch, _site())
    _patch_diligence(monkeypatch, True)
    _patch_all_services(monkeypatch)

    result = tools.dispatch_tool(db, _user(), "get_site_data_room_templates", {"site_id": 42})

    assert result["site_id"] == 42 and result["company_id"] == 7
    tpl = result["items"][0]
    assert tpl["id"] == 9 and tpl["name"] == "Standard Solar"
    assert tpl["section_count"] == 2
    # 2 (section 1 docs) + 1 (subsection doc) + 1 (section 2 doc) = 4
    assert tpl["document_count"] == 4
    _assert_no_writes(db)


# --- 5. Zero-write proof across every new tool -----------------------------------------------------


def test_all_data_room_tools_perform_zero_writes(monkeypatch):
    db = _no_write_db()
    _patch_visible_site(monkeypatch, _site())
    _patch_diligence(monkeypatch, True)
    _patch_all_services(monkeypatch)
    for name in _DATA_ROOM_TOOLS:
        result = tools.dispatch_tool(db, _user(), name, {"site_id": 42})
        assert isinstance(result, dict)
        assert result.get("available") is not False
    _assert_no_writes(db)
