"""Tests for the AI Assistant UI-interaction ANALYTICS foundation (Task #89, additive).

The analytics surface is privacy-bounded, first-party product telemetry: the FE reports discrete
UI-interaction events (the assistant was opened, a card was clicked, a hint was dismissed, …) to an
authenticated ingest endpoint that writes ONLY to the isolated ``assistant_ui_events`` table. It is
a deliberate NON-assistant write path — never the assistant/tool/LLM loop, never a tool — so the
permanent invariant (the Workflow Engine is the only mutator of business state) is untouched.

Coverage:

1. Drift guard — the Pydantic event allowlist (``AssistantUiEventNameLiteral``) matches the model
   enum (``AssistantUiEventName``) exactly, so the two can never silently diverge.
2. Ingest normalization — routes collapse to coarse buckets (entity ids discarded), ``detail`` is
   reduced to a per-event allowlisted token, ``in_companion`` is stored, and ``user_id`` comes from
   auth (never the payload).
3. Ingest hardening — unknown event names, extra keys (no smuggled content/ids), oversize/empty
   batches are all rejected (422); the endpoint is flag-gated (404 off).
4. Aggregate — ``build_interaction_stats`` counts the interactions (incl. action-card clicks by
   kind + companion prompts) over ONLY the isolated table; the admin usage summary/endpoint expose
   it under the existing admin gate.

Style mirrors tests/test_assistant_slice3.py.
"""
import typing
from types import SimpleNamespace

import pytest

from app.helpers.authentication import get_current_user
from app.models.assistant import AssistantUiEvent, AssistantUiEventName
from app.schema.assistant import (
    AssistantUiEventIn,
    AssistantUiEventNameLiteral,
)
from app.services.assistant import ui_events_service, usage_service
from tests.conftest import test_app


def _user(uid=1, admin=False):
    return SimpleNamespace(id=uid, has_platform_bypass=admin)


@pytest.fixture()
def _enable_flag(monkeypatch):
    from app.routers import assistant as assistant_router_module

    monkeypatch.setattr(assistant_router_module.settings, "native_assistant_enabled", True)
    yield


def _clear_events(db_session):
    db_session.query(AssistantUiEvent).delete()
    db_session.commit()


def _rows_for(db_session, uid):
    db_session.expire_all()
    return (
        db_session.query(AssistantUiEvent)
        .filter(AssistantUiEvent.user_id == uid)
        .order_by(AssistantUiEvent.id)
        .all()
    )


# --- 1. drift guard ------------------------------------------------------------------------------


def test_event_literal_matches_model_enum():
    literal_values = set(typing.get_args(AssistantUiEventNameLiteral))
    enum_values = {e.value for e in AssistantUiEventName}
    assert literal_values == enum_values


def test_entry_sources_match_frontend_allowlist():
    # Canonical entry-source vocabulary for the `discoverability_entry_clicked` event. This pinned set
    # MUST stay in sync with the FE `ASSISTANT_ENTRY_SOURCES` tuple in
    # frontend/rea-investment-fe/src/contexts/assistantLauncher/assistantLauncher.tsx (which has its
    # own mirror test). Changing one side without the other fails this test — the cross-language drift
    # guard so the closed analytics vocabulary can never silently diverge.
    canonical = {"topbar", "help_menu", "sidebar", "empty_state", "module_header"}
    assert ui_events_service._ENTRY_SOURCES == canonical


# --- 2. ingest normalization ---------------------------------------------------------------------


def test_ingest_records_normalized_rows(client, _enable_flag, db_session, system_user_id):
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.post(
            "/api/assistant/events",
            json={
                "events": [
                    # route carries an entity id → normalized to coarse bucket only
                    {"event": "assistant_opened", "route": "/telemetry/site/4"},
                    # valid card kind + companion flag preserved
                    {
                        "event": "action_card_clicked",
                        "route": "/workflows/run/abc",
                        "detail": "workflow",
                        "in_companion": True,
                    },
                    # detail not on the card allowlist → dropped to NULL
                    {"event": "action_card_clicked", "detail": "totally-bogus"},
                    # detail on an event that admits NONE → dropped to NULL; unknown route → "other"
                    {"event": "assistant_opened", "route": "/nope/x", "detail": "workflow"},
                ]
            },
        )
        assert resp.status_code == 202
        assert resp.json()["accepted"] == 4

        rows = _rows_for(db_session, system_user_id)
        assert len(rows) == 4
        assert all(r.user_id == system_user_id for r in rows)

        opened, card_ok, card_bogus, opened_other = rows
        assert opened.event == AssistantUiEventName.assistant_opened
        assert opened.route_bucket == "telemetry"
        assert opened.detail is None
        assert opened.in_companion is False

        assert card_ok.route_bucket == "workflows"
        assert card_ok.detail == "workflow"
        assert card_ok.in_companion is True

        assert card_bogus.detail is None  # invalid card kind stripped
        assert opened_other.route_bucket == "other"  # unknown route bucketed, not stored verbatim
        assert opened_other.detail is None  # event admits no detail
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)
        _clear_events(db_session)


def test_ingest_uses_authenticated_user_not_payload(client, _enable_flag, db_session, non_system_user_id):
    # Even if the body is otherwise minimal, the row owner is the authed caller.
    test_app.dependency_overrides[get_current_user] = lambda: _user(non_system_user_id)
    try:
        resp = client.post(
            "/api/assistant/events",
            json={"events": [{"event": "assistant_dismissed"}]},
        )
        assert resp.status_code == 202
        rows = _rows_for(db_session, non_system_user_id)
        assert len(rows) == 1
        assert rows[0].user_id == non_system_user_id
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)
        _clear_events(db_session)


# --- 3. ingest hardening -------------------------------------------------------------------------


def test_ingest_rejects_unknown_event(client, _enable_flag, system_user_id):
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.post("/api/assistant/events", json={"events": [{"event": "exfiltrate"}]})
        assert resp.status_code == 422
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_ingest_rejects_extra_fields_no_content_smuggling(client, _enable_flag, db_session, system_user_id):
    # extra='forbid' blocks any attempt to attach message text, ids, or arbitrary payload.
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        for bad in (
            {"event": "prompt_submitted", "message": "my secret prompt text"},
            {"event": "assistant_opened", "user_id": 999},
            {"event": "assistant_opened", "site_id": 4},
        ):
            resp = client.post("/api/assistant/events", json={"events": [bad]})
            assert resp.status_code == 422, bad
        assert _rows_for(db_session, system_user_id) == []
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)
        _clear_events(db_session)


def test_ingest_rejects_oversize_and_empty_batches(client, _enable_flag, system_user_id):
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        too_many = {"events": [{"event": "assistant_opened"} for _ in range(51)]}
        assert client.post("/api/assistant/events", json=too_many).status_code == 422
        assert client.post("/api/assistant/events", json={"events": []}).status_code == 422
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_ingest_404_when_flag_off(client, system_user_id):
    from app.routers import assistant as assistant_router_module

    assistant_router_module.settings.native_assistant_enabled = False
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.post("/api/assistant/events", json={"events": [{"event": "assistant_opened"}]})
        assert resp.status_code == 404
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


# --- service-level normalization (unit) ----------------------------------------------------------


def test_record_events_service_normalizes(db_session, system_user_id):
    events = [
        AssistantUiEventIn(event="suggested_prompt_clicked", route="/data-room/file/7"),
        AssistantUiEventIn(event="discoverability_entry_clicked", detail="topbar"),
        AssistantUiEventIn(event="discoverability_entry_clicked", detail="not-a-source"),
    ]
    try:
        accepted = ui_events_service.record_events(db_session, _user(system_user_id), events)
        assert accepted == 3
        rows = _rows_for(db_session, system_user_id)
        chip, entry_ok, entry_bad = rows
        assert chip.route_bucket == "data_room"
        assert entry_ok.detail == "topbar"
        assert entry_bad.detail is None
    finally:
        _clear_events(db_session)


# --- 4. aggregate --------------------------------------------------------------------------------


def _seed_known(db_session, uid):
    ui_events_service.record_events(
        db_session,
        _user(uid),
        [
            AssistantUiEventIn(event="assistant_opened"),
            AssistantUiEventIn(event="assistant_opened"),
            AssistantUiEventIn(event="assistant_dismissed"),
            AssistantUiEventIn(event="prompt_submitted"),
            AssistantUiEventIn(event="prompt_submitted", in_companion=True),
            AssistantUiEventIn(event="suggested_prompt_clicked"),
            AssistantUiEventIn(event="sources_disclosure_opened"),
            AssistantUiEventIn(event="action_card_clicked", detail="workflow"),
            AssistantUiEventIn(event="action_card_clicked", detail="workflow"),
            AssistantUiEventIn(event="action_card_clicked", detail="resume"),
        ],
    )


def test_interaction_stats_aggregate(db_session, system_user_id):
    _clear_events(db_session)
    try:
        _seed_known(db_session, system_user_id)
        stats = ui_events_service.build_interaction_stats(db_session)
        assert stats.opens == 2
        assert stats.dismissals == 1
        assert stats.prompt_submissions == 2
        assert stats.companion_prompt_submissions == 1
        assert stats.suggested_prompt_clicks == 1
        assert stats.sources_disclosures_opened == 1
        assert stats.events_total == 10
        by_kind = {c.kind: c.count for c in stats.action_card_clicks}
        assert by_kind == {"workflow": 2, "resume": 1}
    finally:
        _clear_events(db_session)


def test_usage_summary_includes_interactions(db_session, system_user_id):
    _clear_events(db_session)
    try:
        _seed_known(db_session, system_user_id)
        usage = usage_service.build_usage_summary(db_session)
        assert usage.interactions.opens == 2
        assert usage.interactions.companion_prompt_submissions == 1
        assert {c.kind for c in usage.interactions.action_card_clicks} == {"workflow", "resume"}
    finally:
        _clear_events(db_session)


def test_admin_usage_endpoint_exposes_interactions(client, _enable_flag, db_session, system_user_id):
    _clear_events(db_session)
    _seed_known(db_session, system_user_id)
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id, admin=True)
    try:
        resp = client.get("/api/assistant/admin/usage")
        assert resp.status_code == 200
        interactions = resp.json()["interactions"]
        assert interactions["opens"] == 2
        assert interactions["companion_prompt_submissions"] == 1
        assert interactions["events_total"] == 10
        by_kind = {c["kind"]: c["count"] for c in interactions["action_card_clicks"]}
        assert by_kind == {"workflow": 2, "resume": 1}
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)
        _clear_events(db_session)
