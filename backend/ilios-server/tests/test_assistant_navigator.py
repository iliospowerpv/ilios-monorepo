"""Tests for the AI Assistant GLOBAL-NAVIGATOR surface (additive).

Two layers, both propose-only / zero-mutation:

T002 — ``action_cards.build_action_card`` for the new ``open`` / ``explain`` kinds:
  - ``open`` is fail-closed by the destination's OWN read permission (site visibility for
    project_overview; Diligence view for data_room + reconciliation; Finance view for site_finance +
    company_finance); routes are derived server-side from the enum + authorized scope; unknown
    target_view / missing scope are denied; NO DB writes.
  - ``explain`` is permitted with a non-empty prompt (route records the current page) and denied
    without one; NO DB writes.

T001 — ``navigator_suggestions.build_navigator_cards`` deterministic suggester:
  - route → bucket classification; site/project id coercion; per-bucket card sets; permission
    fail-closed absence; dedupe; the max-card cap; NO DB writes.

Style mirrors tests/test_assistant_slice3.py: Mock/monkeypatch unit checks (no live DB rows).
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.schema.assistant import AssistantActionCard, AssistantContextHints
from app.services.assistant import action_cards as ac
from app.services.assistant import navigator_suggestions as nav

# --- shared helpers ------------------------------------------------------------------------------

_WRITE_METHODS = (
    "add",
    "add_all",
    "commit",
    "flush",
    "delete",
    "merge",
    "execute",
    "bulk_save_objects",
)


def _no_write_db():
    return MagicMock(name="db_session")


def _assert_no_writes(db):
    for method in _WRITE_METHODS:
        getattr(db, method).assert_not_called()


def _user(*, bypass=False, finance=False):
    role = SimpleNamespace(permissions={"Finance": {"view": True}} if finance else {})
    return SimpleNamespace(id=1, has_platform_bypass=bypass, role=role)


@pytest.fixture()
def visible_site(monkeypatch):
    """``resolve_candidate_sites`` resolves any requested id to a single visible site (company 3)."""

    def _fake(db, user, *, site_id=None, company_id=None, limit=1):
        if site_id is None:
            return []
        return [SimpleNamespace(id=site_id, company_id=3)]

    monkeypatch.setattr(
        "app.services.workflows.onboarding_common.resolve_candidate_sites", _fake
    )


@pytest.fixture()
def no_visible_site(monkeypatch):
    monkeypatch.setattr(
        "app.services.workflows.onboarding_common.resolve_candidate_sites",
        lambda db, user, *, site_id=None, company_id=None, limit=1: [],
    )


@pytest.fixture()
def authorized_company(monkeypatch):
    """``get_authorized_company`` resolves any company (mirrors the finance routes' dependency)."""

    monkeypatch.setattr(
        "app.helpers.authorization.project_access.get_authorized_company",
        lambda company_id, current_user, db_session: SimpleNamespace(id=company_id),
    )


def _deny_company(monkeypatch):
    """``get_authorized_company`` raises like the real dependency does on denial."""
    from fastapi import HTTPException

    def _raise(company_id, current_user, db_session):
        raise HTTPException(status_code=403)

    monkeypatch.setattr(
        "app.helpers.authorization.project_access.get_authorized_company", _raise
    )


def _set_diligence(monkeypatch, allowed):
    monkeypatch.setattr(
        "app.services.workflows.onboarding_common.can_view_diligence",
        lambda db, user, site: allowed,
    )


def _set_runs(monkeypatch, runs):
    monkeypatch.setattr(
        "app.services.workflows.engine.list_user_runs",
        lambda db, user: SimpleNamespace(items=list(runs)),
    )


def _run(run_id, *, status="active", site_id=7, company_id=3):
    from app.models.workflow import WorkflowRunStatus

    return SimpleNamespace(
        id=run_id,
        status=WorkflowRunStatus[status],
        workflow_id="wf_x",
        workflow_title="Onboard project",
        sequence_id=None,
        site_id=site_id,
        company_id=company_id,
    )


# --- T002: open cards ----------------------------------------------------------------------------


def test_open_project_overview_permitted(visible_site):
    db = _no_write_db()
    res = ac.build_action_card(db, _user(), kind="open", target_view="project_overview", site_id=7)
    assert res["permitted"] is True
    card = res["action_card"]
    assert card["kind"] == "open"
    assert card["target_view"] == "project_overview"
    assert card["route"] == "/project-hub/projects/7"
    assert card["target_site_id"] == 7
    assert card["target_company_id"] == 3  # resolved from the visible site
    assert card["requires_user_action"] is True
    AssistantActionCard(**card)  # schema-valid
    _assert_no_writes(db)


def test_open_data_room_route(visible_site, monkeypatch):
    _set_diligence(monkeypatch, True)
    res = ac.build_action_card(_no_write_db(), _user(), kind="open", target_view="data_room", site_id=7)
    assert res["permitted"] is True
    assert res["action_card"]["route"] == "/project-hub/projects/7/data-room"


def test_open_site_not_visible_denied(no_visible_site):
    db = _no_write_db()
    res = ac.build_action_card(db, _user(), kind="open", target_view="project_overview", site_id=7)
    assert res["permitted"] is False
    assert res["action_card"] is None
    _assert_no_writes(db)


def test_open_data_room_requires_diligence(visible_site, monkeypatch):
    _set_diligence(monkeypatch, False)
    denied = ac.build_action_card(
        _no_write_db(), _user(), kind="open", target_view="data_room", site_id=7
    )
    assert denied["permitted"] is False
    assert denied["action_card"] is None


class _FakeGuidance:
    """Stand-in guidance service: stage 11 is missing the 'site_lease' expected document."""

    def __init__(self, _db):
        pass

    def build_guidance(self, _site_id):
        return {"items": [{"section_id": 11, "missing_documents": [{"kind": "site_lease"}]}]}


_GUIDANCE_PATH = "app.services.due_diligence.data_room_guidance_service.DataRoomGuidanceService"


def test_open_data_room_targets_missing_document(visible_site, monkeypatch):
    """#107: a (kind, section_id) that IS missing appends the server-derived deep-link query."""
    _set_diligence(monkeypatch, True)
    monkeypatch.setattr(_GUIDANCE_PATH, _FakeGuidance)
    db = _no_write_db()
    res = ac.build_action_card(
        db,
        _user(),
        kind="open",
        target_view="data_room",
        site_id=7,
        focus_document_kind="site_lease",
        focus_section_id=11,
    )
    assert res["permitted"] is True
    route = res["action_card"]["route"]
    assert route.startswith("/project-hub/projects/7/data-room?")
    assert "addDocKind=site_lease" in route
    assert "addDocSection=11" in route
    AssistantActionCard(**res["action_card"])  # schema-valid
    _assert_no_writes(db)


def test_open_data_room_ignores_non_missing_focus(visible_site, monkeypatch):
    """A kind that is NOT actually missing falls back to a plain data-room link (no query)."""
    _set_diligence(monkeypatch, True)
    monkeypatch.setattr(_GUIDANCE_PATH, _FakeGuidance)
    res = ac.build_action_card(
        _no_write_db(),
        _user(),
        kind="open",
        target_view="data_room",
        site_id=7,
        focus_document_kind="not_a_missing_kind",
        focus_section_id=11,
    )
    assert res["action_card"]["route"] == "/project-hub/projects/7/data-room"


def test_open_data_room_partial_focus_skips_guidance(visible_site, monkeypatch):
    """Incomplete targeting (kind without section_id) yields a plain link WITHOUT consulting guidance."""
    _set_diligence(monkeypatch, True)
    tripwire = MagicMock(name="DataRoomGuidanceService")
    monkeypatch.setattr(_GUIDANCE_PATH, tripwire)
    res = ac.build_action_card(
        _no_write_db(),
        _user(),
        kind="open",
        target_view="data_room",
        site_id=7,
        focus_document_kind="site_lease",  # no focus_section_id
    )
    assert res["action_card"]["route"] == "/project-hub/projects/7/data-room"
    tripwire.assert_not_called()


def test_open_reconciliation_requires_diligence(visible_site, monkeypatch):
    _set_diligence(monkeypatch, False)
    denied = ac.build_action_card(
        _no_write_db(), _user(), kind="open", target_view="reconciliation", site_id=7
    )
    assert denied["permitted"] is False

    _set_diligence(monkeypatch, True)
    ok = ac.build_action_card(
        _no_write_db(), _user(), kind="open", target_view="reconciliation", site_id=7
    )
    assert ok["permitted"] is True
    assert ok["action_card"]["route"] == "/reconciliation?site_id=7"


def test_open_site_finance_requires_finance(visible_site, authorized_company):
    denied = ac.build_action_card(
        _no_write_db(), _user(finance=False), kind="open", target_view="site_finance", site_id=7
    )
    assert denied["permitted"] is False

    ok = ac.build_action_card(
        _no_write_db(), _user(finance=True), kind="open", target_view="site_finance", site_id=7
    )
    assert ok["permitted"] is True
    assert ok["action_card"]["route"] == "/finance/sites/7/summary?company_id=3"


def test_open_site_finance_denied_when_company_unauthorized(visible_site, monkeypatch):
    # Finance view alone is not enough — the site's company must also be authorized (mirrors the
    # route's get_authorized_company guard).
    _deny_company(monkeypatch)
    res = ac.build_action_card(
        _no_write_db(), _user(finance=True), kind="open", target_view="site_finance", site_id=7
    )
    assert res["permitted"] is False
    assert res["action_card"] is None


def test_open_company_finance(monkeypatch, authorized_company):
    # company_finance needs no visible site, but needs company_id + finance view + company authz.
    no_company = ac.build_action_card(
        _no_write_db(), _user(finance=True), kind="open", target_view="company_finance"
    )
    assert no_company["permitted"] is False  # company_id required

    no_perm = ac.build_action_card(
        _no_write_db(), _user(finance=False), kind="open", target_view="company_finance", company_id=3
    )
    assert no_perm["permitted"] is False

    ok = ac.build_action_card(
        _no_write_db(), _user(finance=True), kind="open", target_view="company_finance", company_id=3
    )
    assert ok["permitted"] is True
    assert ok["action_card"]["route"] == "/finance/summary?company_id=3"
    assert ok["action_card"]["target_company_id"] == 3
    assert ok["action_card"]["target_site_id"] is None


def test_open_company_finance_denied_when_company_unauthorized(monkeypatch):
    # A Finance-view user must NOT get a card for a company they cannot open directly.
    _deny_company(monkeypatch)
    res = ac.build_action_card(
        _no_write_db(), _user(finance=True), kind="open", target_view="company_finance", company_id=999
    )
    assert res["permitted"] is False
    assert res["action_card"] is None


def test_open_company_finance_platform_bypass(authorized_company):
    ok = ac.build_action_card(
        _no_write_db(), _user(bypass=True), kind="open", target_view="company_finance", company_id=3
    )
    assert ok["permitted"] is True


def test_open_unknown_target_view_denied():
    db = _no_write_db()
    res = ac.build_action_card(db, _user(), kind="open", target_view="nope", site_id=7)
    assert res["permitted"] is False
    assert res["action_card"] is None
    _assert_no_writes(db)


def test_open_missing_site_id_denied():
    res = ac.build_action_card(_no_write_db(), _user(), kind="open", target_view="project_overview")
    assert res["permitted"] is False


# --- T002: explain cards -------------------------------------------------------------------------


def test_explain_permitted_records_route():
    db = _no_write_db()
    res = ac.build_action_card(
        db,
        _user(),
        kind="explain",
        prompt="Explain this page.",
        title="Explain this project",
        current_route="/project-hub/projects/7",
        site_id=7,
    )
    assert res["permitted"] is True
    card = res["action_card"]
    assert card["kind"] == "explain"
    assert card["prompt"] == "Explain this page."
    assert card["title"] == "Explain this project"
    assert card["route"] == "/project-hub/projects/7"
    assert card["target_view"] is None
    assert card["target_site_id"] == 7
    AssistantActionCard(**card)
    _assert_no_writes(db)


def test_explain_requires_prompt():
    res = ac.build_action_card(_no_write_db(), _user(), kind="explain", prompt="   ")
    assert res["permitted"] is False
    assert res["action_card"] is None


def test_explain_route_defaults_when_route_missing():
    res = ac.build_action_card(_no_write_db(), _user(), kind="explain", prompt="hi")
    assert res["permitted"] is True
    assert res["action_card"]["route"] == "/"


def test_unknown_kind_denied():
    res = ac.build_action_card(_no_write_db(), _user(), kind="bogus")
    assert res["permitted"] is False
    assert res["action_card"] is None


# --- T001: route bucketing + id coercion ---------------------------------------------------------


@pytest.mark.parametrize(
    "route,expected",
    [
        ("/project-hub/companies/3", "company_hub"),
        ("/project-hub/companies/3?tab=projects", "company_hub"),
        ("/project-hub/projects/7", "project_overview"),
        ("/project-hub/7/data-room", "data_room"),
        ("/project-hub/7/data-room/doc/2", "data_room"),
        ("/project-hub", "project_hub"),
        ("/project-hub/", "project_hub"),
        ("/finance/sites/7/summary", "site_finance"),
        ("/finance/summary?company_id=3", "company_finance"),
        ("/reconciliation?site_id=7", "reconciliation"),
        ("/workflows/start/x", "workflows"),
        ("/something-else", "generic"),
        (None, "generic"),
        ("", "generic"),
    ],
)
def test_bucket(route, expected):
    assert nav._bucket(route) == expected


def test_resolve_site_id_prefers_site_then_project():
    assert nav._resolve_site_id(AssistantContextHints(site_id=7, project_id=9)) == 7
    assert nav._resolve_site_id(AssistantContextHints(project_id=9)) == 9
    assert nav._resolve_site_id(AssistantContextHints()) is None
    assert nav._resolve_site_id(None) is None


# --- T001: navigator card assembly ---------------------------------------------------------------


def test_navigator_project_overview_full_set(visible_site, authorized_company, monkeypatch):
    _set_diligence(monkeypatch, True)
    _set_runs(monkeypatch, [])
    db = _no_write_db()
    hints = AssistantContextHints(route="/project-hub/projects/7", site_id=7, company_id=3)
    cards = nav.build_navigator_cards(db, _user(finance=True), hints)

    assert all(isinstance(c, AssistantActionCard) for c in cards)
    kinds = [(c.kind, c.target_view) for c in cards]
    assert kinds[0] == ("explain", None)  # explain leads
    assert ("open", "data_room") in kinds
    assert ("open", "reconciliation") in kinds
    assert ("open", "site_finance") in kinds
    _assert_no_writes(db)


def test_navigator_finance_card_absent_without_permission(visible_site, monkeypatch):
    _set_diligence(monkeypatch, True)
    _set_runs(monkeypatch, [])
    hints = AssistantContextHints(route="/project-hub/projects/7", site_id=7, company_id=3)
    cards = nav.build_navigator_cards(_no_write_db(), _user(finance=False), hints)

    open_targets = [c.target_view for c in cards if c.kind == "open"]
    assert "site_finance" not in open_targets  # finance denied -> card simply absent
    assert "data_room" in open_targets  # diligence allowed
    assert "reconciliation" in open_targets


def test_navigator_diligence_cards_absent_without_permission(visible_site, authorized_company, monkeypatch):
    _set_diligence(monkeypatch, False)
    _set_runs(monkeypatch, [])
    hints = AssistantContextHints(route="/project-hub/projects/7", site_id=7, company_id=3)
    cards = nav.build_navigator_cards(_no_write_db(), _user(finance=True), hints)

    open_targets = [c.target_view for c in cards if c.kind == "open"]
    assert "data_room" not in open_targets
    assert "reconciliation" not in open_targets
    assert "site_finance" in open_targets  # finance still allowed


def test_navigator_generic_route_only_explain(monkeypatch):
    # Unknown route + no scope: no scoped open cards survive; explain still present.
    _set_runs(monkeypatch, [])
    cards = nav.build_navigator_cards(
        _no_write_db(), _user(), AssistantContextHints(route="/settings")
    )
    assert [c.kind for c in cards] == ["explain"]
    assert cards[0].route == "/settings"


def test_navigator_includes_owner_resume_runs(visible_site, monkeypatch):
    _set_diligence(monkeypatch, True)
    _set_runs(monkeypatch, [_run(101, site_id=7), _run(202, site_id=7)])
    hints = AssistantContextHints(route="/project-hub/projects/7", site_id=7, company_id=3)
    cards = nav.build_navigator_cards(_no_write_db(), _user(finance=True), hints, max_cards=10)

    resume = [c for c in cards if c.kind == "resume"]
    assert {c.run_id for c in resume} == {101, 202}
    assert all(c.route == f"/workflows/runs/{c.run_id}" for c in resume)


def test_navigator_resume_excludes_closed_and_other_scope(visible_site, monkeypatch):
    _set_diligence(monkeypatch, True)
    _set_runs(
        monkeypatch,
        [
            _run(1, status="completed", site_id=7),  # closed -> excluded
            _run(2, status="abandoned", site_id=7),  # closed -> excluded
            _run(3, status="active", site_id=999),  # other site -> excluded
            _run(4, status="active", site_id=7),  # kept
        ],
    )
    hints = AssistantContextHints(route="/project-hub/projects/7", site_id=7, company_id=3)
    cards = nav.build_navigator_cards(_no_write_db(), _user(finance=True), hints, max_cards=10)
    assert {c.run_id for c in cards if c.kind == "resume"} == {4}


def test_navigator_respects_max_card_cap(visible_site, monkeypatch):
    _set_diligence(monkeypatch, True)
    _set_runs(monkeypatch, [_run(101, site_id=7), _run(202, site_id=7)])
    hints = AssistantContextHints(route="/project-hub/projects/7", site_id=7, company_id=3)
    cards = nav.build_navigator_cards(_no_write_db(), _user(finance=True), hints, max_cards=2)
    assert len(cards) == 2


def test_navigator_dedupes_cards(visible_site, monkeypatch):
    _set_diligence(monkeypatch, True)
    _set_runs(monkeypatch, [])
    hints = AssistantContextHints(route="/project-hub/projects/7", site_id=7, company_id=3)
    cards = nav.build_navigator_cards(_no_write_db(), _user(finance=True), hints, max_cards=10)
    keys = [(c.kind, c.target_view, c.route, c.run_id, c.prompt) for c in cards]
    assert len(keys) == len(set(keys))


def test_navigator_company_hub_offers_company_finance(authorized_company, monkeypatch):
    _set_runs(monkeypatch, [])
    hints = AssistantContextHints(route="/project-hub/companies/3", company_id=3)
    cards = nav.build_navigator_cards(_no_write_db(), _user(finance=True), hints)
    open_targets = [c.target_view for c in cards if c.kind == "open"]
    assert "company_finance" in open_targets
