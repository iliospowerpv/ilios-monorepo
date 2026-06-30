"""Slice 3 tests for the native AI Assistant.

Covers the additive Slice 3 surface on top of the Slice 1+2 read-only core:

1. FAQ knowledge coverage — ``_public`` exposes ``category``; ``search_faq`` is deterministic and
   surfaces the expanded topic set (telemetry, reconciliation, devices, weather, finance, …).
2. Source disclosures — ``_collect_sources`` records LABELS-ONLY ``faq``/``tool`` sources (deduped),
   excludes FAQ from the tool-label map and ignores unknown tools; the chat loop attaches them with
   ZERO DB writes.
3. Suggested prompts — deterministic route→prompts mapping with a general fallback, surfaced by the
   flag-gated ``GET /suggested-prompts`` endpoint.
4. Rate-limit / error UX — a model rate-limit maps to ``429`` (+``Retry-After``); a generic model
   failure maps to ``503``; neither leaks a raw SDK error.
5. Feedback thumbs — owner-scoped set/clear on an ASSISTANT message only; cross-user / user-message /
   missing targets resolve to None/404; the tool layer stays zero-write.
6. Admin usage observability — read-only aggregate over ONLY the isolated assistant tables, with the
   admin gate (403 non-admin) and flag gate (404 off) enforced and the documented invariants holding.

Style mirrors tests/test_assistant_slice2.py: Mock/monkeypatch for unit checks, the real test DB +
TestClient (with an auth override) for the persistence/router checks.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.helpers.authentication import get_current_user
from app.models.assistant import AssistantMessageRole
from app.schema.assistant import AssistantChatRequest, AssistantSource
from app.services.assistant import (
    assistant_service,
    conversation_store,
    faq,
    suggested_prompts,
    tools,
    usage_service,
)
from app.services.assistant.llm_client import AssistantLLMError, AssistantRateLimitError
from tests.conftest import test_app


# --- shared helpers (mirroring test_assistant_slice2.py) -----------------------------------------


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


def _user(uid=1, admin=False):
    return SimpleNamespace(id=uid, has_platform_bypass=admin)


@pytest.fixture()
def _enable_flag(monkeypatch):
    from app.routers import assistant as assistant_router_module

    monkeypatch.setattr(assistant_router_module.settings, "native_assistant_enabled", True)
    yield


# --- 1. FAQ knowledge coverage -------------------------------------------------------------------


def test_faq_public_always_includes_category():
    for entry in faq.FAQ_ENTRIES:
        pub = faq._public(entry)
        assert set(pub.keys()) == {"id", "category", "question", "answer"}
        assert pub["category"]  # every curated entry is categorized


def test_faq_corpus_covers_expanded_categories():
    categories = {e.get("category") for e in faq.FAQ_ENTRIES}
    # Slice 3 broadened coverage well beyond the original Basics/Workflows set.
    for expected in {"Basics", "Workflows", "Diligence", "Telemetry", "Devices", "Weather", "Data"}:
        assert expected in categories


@pytest.mark.parametrize(
    "query, expected_category",
    [
        ("how do I refresh telemetry", "Telemetry"),
        ("what does reconciliation show", "Diligence"),
        ("which devices can be mapped", "Devices"),
    ],
)
def test_faq_search_surfaces_relevant_topic(query, expected_category):
    results = faq.search_faq(query)
    assert results, f"expected matches for {query!r}"
    assert all(set(r.keys()) == {"id", "category", "question", "answer"} for r in results)
    assert any(r["category"] == expected_category for r in results)


def test_faq_search_is_deterministic_and_bounded():
    first = faq.search_faq("telemetry refresh", limit=3)
    second = faq.search_faq("telemetry refresh", limit=3)
    assert first == second
    assert len(first) <= 3
    # Empty/over-generic query still grounds the model with leading entries.
    assert faq.search_faq("") == [faq._public(e) for e in faq.FAQ_ENTRIES[:4]]


# --- 2. source disclosures (labels-only, deduped, zero-write) ------------------------------------


def test_collect_sources_faq_entries():
    sink: list[AssistantSource] = []
    seen: set = set()
    result = {"results": [{"id": "tel_1", "question": "How do I refresh telemetry?", "category": "Telemetry"}]}
    assistant_service._collect_sources("answer_help_faq", result, sink, seen)
    assert len(sink) == 1
    src = sink[0]
    assert src.kind == "faq"
    assert src.label == "How do I refresh telemetry?"
    assert src.ref == "tel_1"
    assert src.detail == "Telemetry"
    # Re-collecting the same entry id is a no-op (dedupe on (kind, ref)).
    assistant_service._collect_sources("answer_help_faq", result, sink, seen)
    assert len(sink) == 1


def test_collect_sources_data_tool_label_and_dedupe():
    sink: list[AssistantSource] = []
    seen: set = set()
    assistant_service._collect_sources("get_recommendations", {"items": []}, sink, seen)
    assistant_service._collect_sources("get_recommendations", {"items": []}, sink, seen)
    assert len(sink) == 1
    assert sink[0].kind == "tool"
    assert sink[0].ref == "get_recommendations"
    assert sink[0].label == "Recommended next actions"


def test_collect_sources_ignores_navigation_and_unknown_tools():
    sink: list[AssistantSource] = []
    seen: set = set()
    # propose_action_card is a navigation affordance, not a knowledge source.
    assistant_service._collect_sources("propose_action_card", {"action_card": {}}, sink, seen)
    # An off-catalog / unlabeled tool name contributes nothing.
    assistant_service._collect_sources("something_else", {"x": 1}, sink, seen)
    assert sink == []


def test_chat_attaches_sources_with_zero_writes(monkeypatch):
    db = _no_write_db()
    scripted = _ScriptedClient(
        [
            _response(_message(tool_calls=[_tool_call("c1", "answer_help_faq", '{"query": "refresh telemetry"}')])),
            _response(_message(content="Here's how telemetry refresh works.")),
        ]
    )
    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", scripted)
    monkeypatch.setattr(
        tools,
        "dispatch_tool",
        lambda *a, **k: {"results": [{"id": "tel_1", "question": "How do I refresh telemetry?", "category": "Telemetry"}]},
    )

    resp = assistant_service.run_assistant_chat(db, _user(), AssistantChatRequest(message="how do I refresh?"))

    assert [s.kind for s in resp.sources] == ["faq"]
    assert resp.sources[0].ref == "tel_1"
    assert [t.name for t in resp.used_tools] == ["answer_help_faq"]
    _assert_no_writes(db)


# --- 3. suggested prompts (deterministic mapping + fallback) -------------------------------------


def test_suggested_prompts_route_match():
    label, prompts = suggested_prompts.get_suggested_prompts("/telemetry/site/4")
    assert label == "Telemetry"
    assert prompts and all({"label", "prompt"} <= set(p.keys()) for p in prompts)


@pytest.mark.parametrize(
    "route, expected_label",
    [
        ("/finance/budgeting", "Finance"),
        ("/reports/performance", "Reporting"),
        ("/operations-and-maintenance/site/4", "Operations & Maintenance"),
        ("/due-diligence/companies/1/sites/2", "Due Diligence"),
        ("/portfolio/overview", "Portfolio"),
        # The admin surface must NOT be swallowed by the broader /portfolio prefix.
        ("/portfolio-admin/telemetry", "Settings & Admin"),
        ("/home", "Workspace"),
    ],
)
def test_suggested_prompts_module_buckets(route, expected_label):
    label, prompts = suggested_prompts.get_suggested_prompts(route)
    assert label == expected_label
    assert prompts and all({"label", "prompt"} <= set(p.keys()) for p in prompts)


def test_suggested_prompts_general_fallback():
    label, prompts = suggested_prompts.get_suggested_prompts("/totally/unknown")
    assert label is None
    assert prompts  # general defaults
    none_label, none_prompts = suggested_prompts.get_suggested_prompts(None)
    assert none_label is None and none_prompts == prompts


def test_suggested_prompts_endpoint(client, _enable_flag, system_user_id):
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.get("/api/assistant/suggested-prompts", params={"route": "/data-room/x"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["context_label"] == "Data Room"
        assert body["prompts"]
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_suggested_prompts_404_when_flag_off(client, system_user_id):
    from app.routers import assistant as assistant_router_module

    assistant_router_module.settings.native_assistant_enabled = False
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        assert client.get("/api/assistant/suggested-prompts").status_code == 404
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


# --- 4. rate-limit / error UX -------------------------------------------------------------------


def test_chat_rate_limit_maps_to_429_with_retry_after(client, _enable_flag, monkeypatch, system_user_id):
    def _raise_rate_limit(*, messages, tools, model=None):
        raise AssistantRateLimitError(retry_after=7)

    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", _raise_rate_limit)
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.post("/api/assistant/chat", json={"message": "hello"})
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "7"
        # Friendly message, never a raw SDK/provider error.
        assert "try again" in resp.json()["message"].lower()
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_chat_generic_model_failure_maps_to_503(client, _enable_flag, monkeypatch, system_user_id):
    def _raise_llm(*, messages, tools, model=None):
        raise AssistantLLMError("boom from provider")

    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", _raise_llm)
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.post("/api/assistant/chat", json={"message": "hello"})
        assert resp.status_code == 503
        assert "boom from provider" not in resp.json()["message"]
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


# --- 5. feedback thumbs (owner-scoped, assistant-only, zero tool writes) -------------------------


def _seed_turn(db_session, owner_id, *, reply="Here you go.", with_tool=True):
    conv = conversation_store.create_conversation(db_session, _user(owner_id), first_message="hi")
    msg = conversation_store.append_turn(
        db_session,
        conv,
        user_message="hi",
        reply=reply,
        used_tools=[{"name": "get_recommendations", "ok": True}] if with_tool else [],
        action_cards=[],
        sources=[{"kind": "tool", "label": "Recommended next actions", "ref": "get_recommendations"}],
        model="gpt-5.2",
    )
    return conv, msg


def test_set_feedback_set_and_clear(db_session, system_user_id):
    conv, msg = _seed_turn(db_session, system_user_id)
    try:
        out = conversation_store.set_feedback(
            db_session, _user(system_user_id), conversation_id=conv.id, message_id=msg.id, rating="up", note="great"
        )
        assert out is not None
        assert out.feedback.value == "up"
        assert out.feedback_note == "great"

        cleared = conversation_store.set_feedback(
            db_session, _user(system_user_id), conversation_id=conv.id, message_id=msg.id, rating=None, note=None
        )
        assert cleared.feedback is None and cleared.feedback_note is None
    finally:
        db_session.delete(conv)
        db_session.commit()


def test_set_feedback_rejects_user_message_and_cross_user(db_session, system_user_id, non_system_user_id):
    conv, msg = _seed_turn(db_session, system_user_id)
    user_msg = next(m for m in conv.messages if m.role == AssistantMessageRole.user)
    try:
        # Feedback only applies to ASSISTANT turns.
        assert (
            conversation_store.set_feedback(
                db_session, _user(system_user_id), conversation_id=conv.id, message_id=user_msg.id, rating="up", note=None
            )
            is None
        )
        # Another user cannot rate the owner's message.
        assert (
            conversation_store.set_feedback(
                db_session, _user(non_system_user_id), conversation_id=conv.id, message_id=msg.id, rating="down", note=None
            )
            is None
        )
    finally:
        db_session.delete(conv)
        db_session.commit()


def test_feedback_endpoint_owner_scoped(client, _enable_flag, db_session, system_user_id, non_system_user_id):
    conv, msg = _seed_turn(db_session, system_user_id)
    url = f"/api/assistant/conversations/{conv.id}/messages/{msg.id}/feedback"
    try:
        # Cross-user → 404 (never reveals another's data).
        test_app.dependency_overrides[get_current_user] = lambda: _user(non_system_user_id)
        assert client.post(url, json={"rating": "up"}).status_code == 404

        # Owner → 200 and the rating round-trips.
        test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
        resp = client.post(url, json={"rating": "down", "note": "off"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["message_id"] == msg.id
        assert body["feedback"] == "down"
        assert body["feedback_note"] == "off"

        # Missing message → 404.
        missing = f"/api/assistant/conversations/{conv.id}/messages/99999999/feedback"
        assert client.post(missing, json={"rating": "up"}).status_code == 404
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)
        db_session.delete(conv)
        db_session.commit()


# --- 6. admin usage observability (read-only aggregate, admin + flag gates) ----------------------


def test_usage_summary_invariants(db_session, system_user_id):
    conv, msg = _seed_turn(db_session, system_user_id)
    conversation_store.set_feedback(
        db_session, _user(system_user_id), conversation_id=conv.id, message_id=msg.id, rating="up", note=None
    )
    try:
        usage = usage_service.build_usage_summary(db_session)
        # Aggregate invariants hold regardless of other seed data in the test DB.
        assert usage.conversations_total == usage.conversations_active + usage.conversations_archived
        assert usage.messages_total == usage.user_messages + usage.assistant_messages
        assert usage.feedback_up + usage.feedback_down + usage.feedback_none == usage.assistant_messages
        # Our seeded turn is reflected.
        assert usage.conversations_total >= 1
        assert usage.assistant_messages >= 1
        assert usage.feedback_up >= 1
        assert any(t.name == "get_recommendations" for t in usage.top_tools)
    finally:
        db_session.delete(conv)
        db_session.commit()


def test_admin_usage_endpoint_requires_admin(client, _enable_flag, system_user_id, non_system_user_id):
    # Non-admin → 403.
    test_app.dependency_overrides[get_current_user] = lambda: _user(non_system_user_id, admin=False)
    try:
        assert client.get("/api/assistant/admin/usage").status_code == 403
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)

    # Admin → 200 with the aggregate payload.
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id, admin=True)
    try:
        resp = client.get("/api/assistant/admin/usage")
        assert resp.status_code == 200
        body = resp.json()
        for key in (
            "conversations_total",
            "messages_total",
            "user_messages",
            "assistant_messages",
            "distinct_users",
            "feedback_up",
            "feedback_down",
            "feedback_none",
            "top_tools",
        ):
            assert key in body
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_admin_usage_404_when_flag_off(client, system_user_id):
    from app.routers import assistant as assistant_router_module

    assistant_router_module.settings.native_assistant_enabled = False
    # Flag check runs before the admin gate, so even an admin gets 404 when off.
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id, admin=True)
    try:
        assert client.get("/api/assistant/admin/usage").status_code == 404
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)
