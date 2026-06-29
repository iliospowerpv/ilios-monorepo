"""Slice 2 tests for the native AI Assistant.

Covers the additive Slice 2 surface on top of the Slice 1 read-only core:

1. ``propose_action_card`` is a genuine read-only tool: it is in the catalog, passes the guardrail
   name-screen, validates permission, and performs ZERO DB writes (it only produces inert deep links).
2. ``build_action_card`` permits/denies workflow/sequence/resume cards via the SAME read-only checks
   the dashboard uses, and never executes or writes.
3. The chat loop aggregates validated cards onto the response (deduped) without writing.
4. Conversation persistence (the ONLY write path) is owner-scoped to the isolated assistant tables:
   create/append/list/get, cross-user 404, and soft-archive hiding.
5. The router is flag-gated (404 off) and the persist path on ``POST /chat`` records the turn and
   echoes the conversation id, while the default (no-persist) path writes nothing.

Style mirrors tests/test_assistant_mvp.py: Mock/monkeypatch for the unit checks, the real test DB +
TestClient (with an auth override) for the persistence/router checks.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from app.helpers.authentication import get_current_user
from app.models.workflow import WorkflowRunStatus
from app.schema.assistant import (
    AssistantActionCard,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantContextHints,
    AssistantToolInvocation,
)
from app.services.assistant import action_cards as ac
from app.services.assistant import assistant_service, conversation_store, guardrails, tools
from app.services.workflows import definitions as wf_definitions
from app.services.workflows import engine as wf_engine
from tests.conftest import test_app


# --- shared helpers (mirroring test_assistant_mvp.py) ---------------------------------------------


def _tool_call(call_id: str, name: str, arguments: str = "{}"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def _message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _ScriptedClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, *, messages, tools, model=None):
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._responses.pop(0)


def _no_write_db():
    return MagicMock(name="db_session")


def _assert_no_writes(db):
    for method in ("add", "add_all", "commit", "flush", "delete", "merge", "execute", "bulk_save_objects"):
        getattr(db, method).assert_not_called()


def _user(uid=1):
    return SimpleNamespace(id=uid, has_platform_bypass=False)


# --- 1. propose_action_card is a catalog-resident, guardrail-clean, read-only tool ----------------


def test_propose_action_card_is_in_catalog_and_read_only():
    assert "propose_action_card" in tools.ALLOWED_TOOLS
    assert "propose_action_card" in tools.TOOL_HANDLERS
    spec_names = {s["function"]["name"] for s in tools.TOOL_SPECS}
    assert "propose_action_card" in spec_names
    # The name must NOT look like a mutation/execution, or the guardrail would block it.
    assert not guardrails.is_prohibited("propose_action_card")
    guardrails.assert_tool_allowed("propose_action_card", tools.ALLOWED_TOOLS)  # must not raise


# --- 2. build_action_card permit/deny + zero writes ----------------------------------------------


def test_action_card_workflow_permitted(monkeypatch):
    db = _no_write_db()
    monkeypatch.setattr(wf_definitions, "get_definition", lambda wid: SimpleNamespace(title="Onboard a Site"))
    monkeypatch.setattr(wf_engine, "_can_start", lambda wf, user, db_session: True)

    out = ac.build_action_card(db, _user(), kind="workflow", workflow_id="onboard_site", site_id=4, company_id=3)

    assert out["permitted"] is True
    card = out["action_card"]
    assert card["kind"] == "workflow"
    assert card["title"] == "Onboard a Site"
    assert card["route"] == "/workflows/start/onboard_site?site_id=4&company_id=3"
    assert card["requires_user_action"] is True
    _assert_no_writes(db)


def test_action_card_workflow_denied_when_user_cannot_start(monkeypatch):
    db = _no_write_db()
    monkeypatch.setattr(wf_definitions, "get_definition", lambda wid: SimpleNamespace(title="Onboard"))
    monkeypatch.setattr(wf_engine, "_can_start", lambda wf, user, db_session: False)

    out = ac.build_action_card(db, _user(), kind="workflow", workflow_id="onboard_site")

    assert out["permitted"] is False
    assert out["action_card"] is None
    _assert_no_writes(db)


def test_action_card_unknown_workflow_denied(monkeypatch):
    db = _no_write_db()
    monkeypatch.setattr(wf_definitions, "get_definition", lambda wid: None)
    out = ac.build_action_card(db, _user(), kind="workflow", workflow_id="nope")
    assert out["permitted"] is False and out["action_card"] is None
    _assert_no_writes(db)


def test_action_card_can_start_failure_fails_closed(monkeypatch):
    db = _no_write_db()
    monkeypatch.setattr(wf_definitions, "get_definition", lambda wid: SimpleNamespace(title="X"))

    def _boom(wf, user, db_session):
        raise RuntimeError("authz blew up")

    monkeypatch.setattr(wf_engine, "_can_start", _boom)
    out = ac.build_action_card(db, _user(), kind="workflow", workflow_id="x")
    assert out["permitted"] is False and out["action_card"] is None
    _assert_no_writes(db)


def test_action_card_sequence_permit_and_deny(monkeypatch):
    db = _no_write_db()
    seq = SimpleNamespace(id="seq_a", title="Full Onboarding", can_start=True)
    monkeypatch.setattr(wf_engine, "list_sequences", lambda d, u: SimpleNamespace(items=[seq]))

    ok = ac.build_action_card(db, _user(), kind="sequence", sequence_id="seq_a")
    assert ok["permitted"] is True
    assert ok["action_card"]["route"] == "/workflows/sequences/seq_a"

    seq.can_start = False
    denied = ac.build_action_card(db, _user(), kind="sequence", sequence_id="seq_a")
    assert denied["permitted"] is False and denied["action_card"] is None

    missing = ac.build_action_card(db, _user(), kind="sequence", sequence_id="ghost")
    assert missing["permitted"] is False
    _assert_no_writes(db)


def test_action_card_resume_owner_scoped_and_status_aware(monkeypatch):
    db = _no_write_db()
    run = SimpleNamespace(
        id=55,
        status=WorkflowRunStatus.active,
        workflow_id="onboard_site",
        workflow_title="Onboard a Site",
        sequence_id=None,
        site_id=4,
        company_id=3,
    )
    monkeypatch.setattr(wf_engine, "list_user_runs", lambda d, u: SimpleNamespace(items=[run]))

    ok = ac.build_action_card(db, _user(), kind="resume", run_id=55)
    assert ok["permitted"] is True
    assert ok["action_card"]["route"] == "/workflows/runs/55"
    assert ok["action_card"]["run_id"] == 55

    # A run the caller doesn't own simply isn't in their list → denied.
    not_mine = ac.build_action_card(db, _user(), kind="resume", run_id=999)
    assert not_mine["permitted"] is False

    run.status = WorkflowRunStatus.completed
    closed = ac.build_action_card(db, _user(), kind="resume", run_id=55)
    assert closed["permitted"] is False and closed["action_card"] is None
    _assert_no_writes(db)


def test_action_card_unknown_kind_denied():
    db = _no_write_db()
    out = ac.build_action_card(db, _user(), kind="explode")
    assert out["permitted"] is False and out["action_card"] is None
    _assert_no_writes(db)


# --- 3. chat loop aggregates validated cards (deduped), still zero-write --------------------------


def test_chat_aggregates_and_dedups_action_cards(monkeypatch):
    db = _no_write_db()
    scripted = _ScriptedClient(
        [
            _response(
                _message(
                    tool_calls=[
                        _tool_call("c1", "propose_action_card", '{"kind": "workflow", "workflow_id": "w"}'),
                        _tool_call("c2", "propose_action_card", '{"kind": "workflow", "workflow_id": "w"}'),
                    ]
                )
            ),
            _response(_message(content="Here's a shortcut you can click.")),
        ]
    )
    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", scripted)

    card = {
        "kind": "workflow",
        "title": "Workflow",
        "reason": "do it",
        "route": "/workflows/start/w",
        "workflow_id": "w",
        "sequence_id": None,
        "run_id": None,
        "target_site_id": None,
        "target_company_id": None,
        "requires_user_action": True,
    }
    monkeypatch.setattr(
        tools, "build_action_card", lambda *a, **k: {"permitted": True, "reason": None, "action_card": card}
    )

    resp = assistant_service.run_assistant_chat(db, _user(), AssistantChatRequest(message="how do I onboard?"))

    # Two identical proposals collapse to a single card.
    assert len(resp.action_cards) == 1
    assert resp.action_cards[0].route == "/workflows/start/w"
    assert resp.action_cards[0].requires_user_action is True
    assert [t.name for t in resp.used_tools] == ["propose_action_card", "propose_action_card"]
    _assert_no_writes(db)


def test_chat_omits_denied_action_cards(monkeypatch):
    db = _no_write_db()
    scripted = _ScriptedClient(
        [
            _response(_message(tool_calls=[_tool_call("c1", "propose_action_card", '{"kind": "workflow", "workflow_id": "w"}')])),
            _response(_message(content="You don't have permission to start that.")),
        ]
    )
    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", scripted)
    monkeypatch.setattr(
        tools, "build_action_card", lambda *a, **k: {"permitted": False, "reason": "nope", "action_card": None}
    )

    resp = assistant_service.run_assistant_chat(db, _user(), AssistantChatRequest(message="onboard"))
    assert resp.action_cards == []
    _assert_no_writes(db)


# --- 4. conversation persistence: owner-scoped CRUD on the isolated tables ------------------------


def test_conversation_store_create_append_list_get(db_session, system_user_id):
    conv = conversation_store.create_conversation(
        db_session, _user(system_user_id), company_id=None, first_message="What should I do next?"
    )
    assert conv.id is not None
    assert conv.title == "What should I do next?"

    conversation_store.append_turn(
        db_session,
        conv,
        user_message="What should I do next?",
        reply="Here are your next steps.",
        used_tools=[{"name": "get_recommendations", "ok": True}],
        action_cards=[],
        model="gpt-5.2",
    )

    fetched = conversation_store.get_conversation(db_session, _user(system_user_id), conv.id)
    assert fetched is not None
    assert len(fetched.messages) == 2
    assert fetched.messages[0].role.value == "user"
    assert fetched.messages[1].role.value == "assistant"
    assert fetched.messages[1].model == "gpt-5.2"

    listed = conversation_store.list_conversations(db_session, _user(system_user_id))
    assert any(c.id == conv.id for c in listed)

    # cleanup
    db_session.delete(conv)
    db_session.commit()


def test_conversation_store_owner_scoped_and_archive(db_session, system_user_id, non_system_user_id):
    conv = conversation_store.create_conversation(
        db_session, _user(system_user_id), first_message="owner only"
    )
    db_session.commit()

    # Another user cannot read it.
    assert conversation_store.get_conversation(db_session, _user(non_system_user_id), conv.id) is None
    # Another user cannot archive it.
    assert conversation_store.archive_conversation(db_session, _user(non_system_user_id), conv.id) is False

    # Owner archives → hidden from get/list.
    assert conversation_store.archive_conversation(db_session, _user(system_user_id), conv.id) is True
    assert conversation_store.get_conversation(db_session, _user(system_user_id), conv.id) is None
    assert all(c.id != conv.id for c in conversation_store.list_conversations(db_session, _user(system_user_id)))

    # cleanup
    db_session.delete(conv)
    db_session.commit()


# --- 5. router: flag gating + persist path + config ----------------------------------------------


@pytest.fixture()
def _enable_flag(monkeypatch):
    from app.routers import assistant as assistant_router_module

    monkeypatch.setattr(assistant_router_module.settings, "native_assistant_enabled", True)
    yield


def test_config_endpoint_lists_propose_action_card(client, _enable_flag, system_user_id):
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=system_user_id)
    try:
        resp = client.get("/api/assistant/config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert "propose_action_card" in body["available_tools"]
        assert body["prohibited_actions"]  # non-empty mirror of the engine contract
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_config_404_when_flag_disabled(client, system_user_id):
    from app.routers import assistant as assistant_router_module

    assistant_router_module.settings.native_assistant_enabled = False
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=system_user_id)
    try:
        resp = client.get("/api/assistant/config")
        assert resp.status_code == 404
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def _canned_chat_response(reply="ok", cards=None):
    return AssistantChatResponse(
        generated_at=datetime.now(timezone.utc),
        model="gpt-5.2",
        reply=reply,
        used_tools=[AssistantToolInvocation(name="answer_help_faq", ok=True)],
        action_cards=cards or [],
    )


def test_chat_persists_and_echoes_conversation_id(client, _enable_flag, monkeypatch, system_user_id):
    from app.routers import assistant as assistant_router_module

    card = AssistantActionCard(
        kind="workflow", title="Onboard", reason="next step", route="/workflows/start/w", workflow_id="w"
    )
    monkeypatch.setattr(
        assistant_router_module,
        "run_assistant_chat",
        lambda db, user, payload: _canned_chat_response(reply="Here you go.", cards=[card]),
    )
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=system_user_id)
    try:
        resp = client.post("/api/assistant/chat", json={"message": "how do I onboard?", "persist": True})
        assert resp.status_code == 200
        body = resp.json()
        assert body["conversation_id"]
        conv_id = int(body["conversation_id"])

        # The turn is now retrievable with both messages and the persisted card.
        detail = client.get(f"/api/assistant/conversations/{conv_id}")
        assert detail.status_code == 200
        d = detail.json()
        assert len(d["messages"]) == 2
        assert d["messages"][1]["action_cards"][0]["route"] == "/workflows/start/w"

        # It also appears in the owner's list.
        listing = client.get("/api/assistant/conversations")
        assert any(c["id"] == conv_id for c in listing.json()["items"])

        # Soft-archive hides it.
        assert client.delete(f"/api/assistant/conversations/{conv_id}").status_code == 204
        assert client.get(f"/api/assistant/conversations/{conv_id}").status_code == 404
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_chat_default_does_not_persist(client, _enable_flag, monkeypatch, non_system_user_id):
    from app.routers import assistant as assistant_router_module

    monkeypatch.setattr(
        assistant_router_module, "run_assistant_chat", lambda db, user, payload: _canned_chat_response()
    )
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=non_system_user_id)
    try:
        resp = client.post("/api/assistant/chat", json={"message": "just asking"})
        assert resp.status_code == 200
        assert resp.json()["conversation_id"] is None
        # Nothing was written for this user.
        assert client.get("/api/assistant/conversations").json()["items"] == []
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_get_conversation_cross_user_is_404(client, _enable_flag, db_session, system_user_id, non_system_user_id):
    conv = conversation_store.create_conversation(db_session, _user(system_user_id), first_message="private")
    db_session.commit()
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=non_system_user_id)
    try:
        assert client.get(f"/api/assistant/conversations/{conv.id}").status_code == 404
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)
        db_session.delete(conv)
        db_session.commit()
