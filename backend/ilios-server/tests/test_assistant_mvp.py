"""Slice 1 tests for the native AI Assistant.

Pure unit style (Mock/monkeypatch, no live DB rows), mirroring tests/test_onboarding_phase3.py.
Proves: (1) the tool catalog is read-only and consistent, (2) the guardrail blocks off-catalog and
prohibited tool names, (3) tools/chat perform ZERO DB writes, (4) handlers thread current_user
through to the wrapped services (authz delegated, never bypassed), (5) the chat loop dispatches tools
and rejects a model's attempt to call a forbidden tool, (6) the endpoint is flag-gated.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from app.services.assistant import assistant_service, guardrails, tools
from app.services.assistant.faq import search_faq
from app.services.assistant.guardrails import AssistantGuardrailError
from app.services.workflows.orchestration_context_service import PROHIBITED_ACTIONS
from app.schema.assistant import AssistantChatRequest, AssistantContextHints


# --- Fakes mimicking the OpenAI SDK response shape -------------------------------------------------


def _tool_call(call_id: str, name: str, arguments: str = "{}"):
    return SimpleNamespace(
        id=call_id, function=SimpleNamespace(name=name, arguments=arguments)
    )


def _message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _ScriptedClient:
    """create_chat_completion replacement returning queued responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, *, messages, tools, model=None):
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._responses.pop(0)


def _no_write_db():
    """A Mock db whose mutating methods, if ever called, fail the test."""
    db = MagicMock(name="db_session")
    return db


def _assert_no_writes(db):
    for method in ("add", "add_all", "commit", "flush", "delete", "merge", "execute", "bulk_save_objects"):
        getattr(db, method).assert_not_called()


# --- 1. Tool catalog is read-only & consistent ----------------------------------------------------


def test_catalog_specs_match_handlers():
    spec_names = {s["function"]["name"] for s in tools.TOOL_SPECS}
    assert spec_names == set(tools.TOOL_HANDLERS)
    assert spec_names == set(tools.ALLOWED_TOOLS)


def test_every_spec_is_a_read_only_function():
    for s in tools.TOOL_SPECS:
        assert s["type"] == "function"
        fn = s["function"]
        assert fn["name"] and fn["description"]
        assert fn["parameters"]["type"] == "object"
        # No allowlisted tool name may look like a mutation/execution.
        assert not guardrails.is_prohibited(fn["name"])


def test_allowlist_excludes_every_prohibited_action():
    for action in PROHIBITED_ACTIONS:
        assert action not in tools.ALLOWED_TOOLS
        assert guardrails.is_prohibited(action)


# --- 2. Guardrail blocks off-catalog and prohibited names -----------------------------------------


@pytest.mark.parametrize(
    "bad_name",
    [
        "start_or_advance_workflow_run",
        "execute_workflow_step",
        "promote_project_fact",
        "approve_or_activate_expected_baseline",
        "map_or_unmap_device",
        "create_or_change_weather_declaration",
        "bypass_authorization_or_permissions",
        "write_or_mutate_any_operational_truth",
        "delete_site",
        "totally_unknown_tool",
    ],
)
def test_guardrail_blocks_disallowed(bad_name):
    with pytest.raises(AssistantGuardrailError):
        guardrails.assert_tool_allowed(bad_name, tools.ALLOWED_TOOLS)


def test_guardrail_allows_catalog_names():
    for name in tools.ALLOWED_TOOLS:
        guardrails.assert_tool_allowed(name, tools.ALLOWED_TOOLS)  # must not raise


def test_dispatch_rejects_prohibited_before_running(monkeypatch):
    db = _no_write_db()
    with pytest.raises(AssistantGuardrailError):
        tools.dispatch_tool(db, Mock(), "promote_project_fact", {})
    _assert_no_writes(db)


# --- 3. Tools perform zero writes & 4. thread current_user through --------------------------------


def test_handlers_pass_user_through_and_dont_write(monkeypatch):
    db = _no_write_db()
    user = SimpleNamespace(id=7, has_platform_bypass=False)
    captured = {}

    def fake_factory(key):
        def _fake(db_session, current_user, *a, **k):
            captured[key] = current_user
            return SimpleNamespace(model_dump=lambda mode=None: {"ok": key})

        return _fake

    monkeypatch.setattr(tools, "list_workflow_definitions", fake_factory("list_workflows"))
    monkeypatch.setattr(tools, "list_sequences", fake_factory("list_sequences"))
    monkeypatch.setattr(tools, "list_user_runs", fake_factory("list_my_runs"))
    monkeypatch.setattr(tools, "build_recommendations", fake_factory("get_recommendations"))
    monkeypatch.setattr(tools, "build_onboarding_progress", fake_factory("get_onboarding_progress"))
    monkeypatch.setattr(tools, "build_readiness_summary", fake_factory("get_onboarding_readiness"))
    monkeypatch.setattr(tools, "build_orchestration_context", fake_factory("get_orchestration_context"))
    monkeypatch.setattr(tools, "compute_metrics", fake_factory("get_workflow_metrics"))

    for name in tools.ALLOWED_TOOLS:
        result = tools.dispatch_tool(db, user, name, {"limit": 5, "query": "what is ilios"})
        assert isinstance(result, dict)

    # Every wrapped service received the SAME caller (authz delegated, never bypassed).
    for key, seen_user in captured.items():
        assert seen_user is user, key
    _assert_no_writes(db)


def test_faq_tool_is_local_and_filters():
    results = search_faq("what is the difference between a project and a site")
    assert any(r["id"] == "project-vs-site" for r in results)
    # Empty query still returns grounding entries (never empty).
    assert search_faq("") and len(search_faq("", limit=2)) == 2


# --- 5. Chat loop: dispatches tools, rejects forbidden requests, never writes ---------------------


def test_chat_runs_tool_then_answers(monkeypatch):
    db = _no_write_db()
    scripted = _ScriptedClient(
        [
            _response(_message(tool_calls=[_tool_call("c1", "get_recommendations", '{"limit": 3}')])),
            _response(_message(content="Here are your next steps.")),
        ]
    )
    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", scripted)
    monkeypatch.setattr(
        tools,
        "build_recommendations",
        lambda *a, **k: SimpleNamespace(model_dump=lambda mode=None: {"items": []}),
    )

    resp = assistant_service.run_assistant_chat(
        db, SimpleNamespace(id=1, has_platform_bypass=False), AssistantChatRequest(message="what next?")
    )

    assert resp.reply == "Here are your next steps."
    assert resp.mode == "read_only_advice"
    assert [t.name for t in resp.used_tools] == ["get_recommendations"]
    assert resp.used_tools[0].ok is True
    _assert_no_writes(db)


def test_chat_rejects_model_attempt_to_mutate(monkeypatch):
    db = _no_write_db()
    scripted = _ScriptedClient(
        [
            _response(_message(tool_calls=[_tool_call("c1", "promote_project_fact", "{}")])),
            _response(_message(content="I can't do that, but here is how you can.")),
        ]
    )
    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", scripted)

    resp = assistant_service.run_assistant_chat(
        db, SimpleNamespace(id=1, has_platform_bypass=False), AssistantChatRequest(message="promote it")
    )

    assert resp.used_tools[0].name == "promote_project_fact"
    assert resp.used_tools[0].ok is False
    assert resp.reply == "I can't do that, but here is how you can."
    _assert_no_writes(db)


def test_chat_context_hints_added_to_prompt(monkeypatch):
    db = _no_write_db()
    scripted = _ScriptedClient([_response(_message(content="ok"))])
    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", scripted)

    assistant_service.run_assistant_chat(
        db,
        SimpleNamespace(id=1, has_platform_bypass=False),
        AssistantChatRequest(
            message="help", context=AssistantContextHints(route="/x", company_id=3, project_id=9)
        ),
    )
    system_blobs = " ".join(m["content"] for m in scripted.calls[0]["messages"] if m["role"] == "system")
    assert "company_id=3" in system_blobs and "site_id(project_id)=9" in system_blobs


def test_chat_loop_is_bounded(monkeypatch):
    db = _no_write_db()
    # Always return a tool call -> loop must terminate via the iteration cap, not hang.
    forever = _ScriptedClient(
        [
            _response(_message(tool_calls=[_tool_call(f"c{i}", "list_workflows", "{}")]))
            for i in range(assistant_service.MAX_TOOL_ITERATIONS + 3)
        ]
    )
    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", forever)
    monkeypatch.setattr(
        tools, "list_workflow_definitions", lambda *a, **k: SimpleNamespace(model_dump=lambda mode=None: {})
    )

    resp = assistant_service.run_assistant_chat(
        db, SimpleNamespace(id=1, has_platform_bypass=False), AssistantChatRequest(message="loop")
    )
    assert len(scripted_calls := forever.calls) == assistant_service.MAX_TOOL_ITERATIONS
    assert resp.reply  # graceful fallback message, not empty
    _assert_no_writes(db)


# --- 6. Endpoint is flag-gated --------------------------------------------------------------------


def test_endpoint_404_when_flag_disabled(monkeypatch):
    from fastapi import HTTPException

    from app.routers import assistant as assistant_router_module

    monkeypatch.setattr(assistant_router_module.settings, "native_assistant_enabled", False)
    with pytest.raises(HTTPException) as exc:
        assistant_router_module._require_enabled()
    assert exc.value.status_code == 404


def test_endpoint_passes_when_flag_enabled(monkeypatch):
    from app.routers import assistant as assistant_router_module

    monkeypatch.setattr(assistant_router_module.settings, "native_assistant_enabled", True)
    assistant_router_module._require_enabled()  # must not raise
