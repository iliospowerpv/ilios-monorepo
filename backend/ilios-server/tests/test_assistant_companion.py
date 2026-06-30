"""Tests for the AI Assistant WORKFLOW COMPANION surface (additive, read-only).

The Companion turns the existing read-only native assistant into an IN-WIZARD guide that is aware of
the active workflow run + current step. It can EXPLAIN the step/fields/validation/confirmation,
guide RESUME, and surface blockers — but it NEVER executes anything. The Workflow Engine stays the
ONLY mutator; the assistant only READS persisted run state via ``get_workflow_run`` (wrapping the
owner-scoped ``engine.get_run``).

Coverage (all propose-only / zero-mutation):

1. ``get_workflow_run`` tool (Phase 1) — catalogued/labelled/guardrail-clean, requires run_id, wraps
   ``engine.get_run`` on the happy path, returns honest 'unavailable' on cross-user/not-found
   (HTTPException) and on a missing run_id, never discloses, and performs ZERO DB writes.
2. Companion suggested prompts (Phase 2) — ``in_workflow=True`` returns the step-aware Companion
   bucket regardless of route; ``in_workflow=False`` leaves the route mapping unchanged.
3. Companion navigator cards (Phase 2) — a present ``run_id`` switches the navigator into Companion
   Mode (explain re-prompts + a resume card for THIS run, fail-closed); absent ``run_id`` leaves the
   generic page navigator untouched; cap + zero writes hold.
4. ``/suggested-prompts`` endpoint params (Phase 2) — ``run_id`` flips the surface to Companion;
   without it the route mapping is unchanged; flag gate still enforced.
5. Companion system addendum (Phase 2) — the Companion Mode system turn + run/step preamble are
   appended ONLY when the context carries a ``run_id``; the chat loop grounds in ``get_workflow_run``
   with ZERO writes.
6. Zero-execution / no-second-path proof — the assistant package never references any engine WRITE
   function (start_run / save_step / preview_step / execute_step / execute_file / abandon_run) and
   none are exposed as a callable tool; the engine remains the only execution path.

Style mirrors tests/test_assistant_navigator.py and tests/test_assistant_slice3.py: Mock/monkeypatch
unit checks, with the real test DB + TestClient (auth override) for the router checks.
"""
import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from fastapi import HTTPException

from app.helpers.authentication import get_current_user
from app.schema.assistant import (
    AssistantActionCard,
    AssistantChatRequest,
    AssistantContextHints,
)
from app.services.assistant import (
    assistant_service,
    guardrails,
    navigator_suggestions as nav,
    suggested_prompts,
    tools,
)
from tests.conftest import test_app

# The engine WRITE/EXECUTE functions the assistant must NEVER call. Keeping the engine the single
# mutator is the core invariant of the whole Companion feature.
_ENGINE_WRITE_FNS = (
    "start_run",
    "save_step",
    "preview_step",
    "execute_step",
    "execute_file",
    "abandon_run",
)


# --- shared helpers (mirroring test_assistant_navigator.py) --------------------------------------

_WRITE_METHODS = ("add", "add_all", "commit", "flush", "delete", "merge", "execute", "bulk_save_objects")


def _no_write_db():
    return MagicMock(name="db_session")


def _assert_no_writes(db):
    for method in _WRITE_METHODS:
        getattr(db, method).assert_not_called()


def _user(uid=1, admin=False):
    return SimpleNamespace(id=uid, has_platform_bypass=admin)


def _model(payload):
    """A stand-in pydantic response exposing ``model_dump(mode=...)``."""
    return SimpleNamespace(model_dump=lambda mode=None: dict(payload))


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


def _set_runs(monkeypatch, runs):
    monkeypatch.setattr(
        "app.services.workflows.engine.list_user_runs",
        lambda db, user: SimpleNamespace(items=list(runs)),
    )


@pytest.fixture()
def _enable_flag(monkeypatch):
    from app.routers import assistant as assistant_router_module

    monkeypatch.setattr(assistant_router_module.settings, "native_assistant_enabled", True)
    yield


# --- scripted LLM client (mirroring test_assistant_slice3.py) ------------------------------------


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


# === 1. get_workflow_run tool (Phase 1) =========================================================


def test_get_workflow_run_catalogued_labelled_and_not_prohibited():
    assert "get_workflow_run" in tools.ALLOWED_TOOLS
    assert "get_workflow_run" in tools.TOOL_HANDLERS
    assert not guardrails.is_prohibited("get_workflow_run")
    assert "get_workflow_run" in assistant_service._TOOL_SOURCE_LABELS
    guardrails.assert_tool_allowed("get_workflow_run", tools.ALLOWED_TOOLS)  # must not raise


def test_get_workflow_run_spec_requires_run_id():
    by_name = {s["function"]["name"]: s for s in tools.TOOL_SPECS}
    params = by_name["get_workflow_run"]["function"]["parameters"]
    assert params.get("required") == ["run_id"]
    assert "run_id" in params["properties"]


def test_get_workflow_run_happy_path_wraps_engine_get_run(monkeypatch):
    db = _no_write_db()
    recorder = {}

    def _fake_get_run(db_arg, user_arg, run_id):
        recorder["call"] = (run_id,)
        return _model({"run": {"id": run_id, "status": "active"}, "current_step": {"id": "s1"}})

    monkeypatch.setattr(tools, "get_run", _fake_get_run)

    result = tools.dispatch_tool(db, _user(), "get_workflow_run", {"run_id": 55})

    assert result["run"]["id"] == 55
    assert recorder["call"] == (55,)  # the owner-scoped engine read actually ran
    _assert_no_writes(db)


def test_get_workflow_run_missing_run_id_is_honest_unavailable(monkeypatch):
    db = _no_write_db()
    service = Mock(name="get_run")
    monkeypatch.setattr(tools, "get_run", service)

    result = tools.dispatch_tool(db, _user(), "get_workflow_run", {})

    assert result == {"available": False, "reason": "missing_run_id", "run_id": None}
    service.assert_not_called()  # never even reaches the engine
    _assert_no_writes(db)


def test_get_workflow_run_cross_user_returns_honest_unavailable_without_disclosure(monkeypatch):
    db = _no_write_db()

    def _raise_not_found(db_arg, user_arg, run_id):
        # engine.get_run is owner-scoped: a run the caller doesn't own raises 404.
        raise HTTPException(status_code=404, detail="Run not found")

    monkeypatch.setattr(tools, "get_run", _raise_not_found)

    result = tools.dispatch_tool(db, _user(), "get_workflow_run", {"run_id": 999})

    # Honest, content-free envelope — nothing about the other user's run leaks through.
    assert result == {"available": False, "reason": "not_authorized_or_not_found", "run_id": 999}
    _assert_no_writes(db)


# === 2. Companion suggested prompts (Phase 2) ===================================================


def test_companion_prompts_when_in_workflow():
    label, prompts = suggested_prompts.get_suggested_prompts("/anything", in_workflow=True)
    assert label == "Workflow Companion"
    assert len(prompts) == len(suggested_prompts._COMPANION)
    assert all({"label", "prompt"} <= set(p.keys()) for p in prompts)


def test_in_workflow_overrides_route_mapping():
    # A known route (/data-room normally maps to "Data Room") is overridden by Companion Mode.
    plain_label, _ = suggested_prompts.get_suggested_prompts("/data-room/x")
    assert plain_label == "Data Room"
    companion_label, _ = suggested_prompts.get_suggested_prompts("/data-room/x", in_workflow=True)
    assert companion_label == "Workflow Companion"


def test_route_mapping_unchanged_when_not_in_workflow():
    # Regression: the additive Companion branch must not disturb the existing route mapping.
    label, prompts = suggested_prompts.get_suggested_prompts("/telemetry/site/4")
    assert label == "Telemetry"
    assert prompts


# === 3. Companion navigator cards (Phase 2) =====================================================


def test_navigator_companion_mode_when_run_id_present(monkeypatch):
    _set_runs(monkeypatch, [_run(55)])  # this run is open + owned -> resume card permitted
    db = _no_write_db()
    hints = AssistantContextHints(
        route="/workflows/runs/55", run_id=55, workflow_id="wf_x", step_id="s1", site_id=7, company_id=3
    )

    cards = nav.build_navigator_cards(db, _user(), hints, max_cards=10)

    assert all(isinstance(c, AssistantActionCard) for c in cards)
    kinds = [c.kind for c in cards]
    # Step-aware explain re-prompts lead the set...
    assert kinds[:len(nav._COMPANION_EXPLAINS)] == ["explain"] * len(nav._COMPANION_EXPLAINS)
    # ...and a resume card for THIS run is offered.
    resume = [c for c in cards if c.kind == "resume"]
    assert [c.run_id for c in resume] == [55]
    # The generic page navigator's scoped "open" deep links are NOT present in Companion Mode.
    assert "open" not in kinds
    _assert_no_writes(db)


def test_navigator_companion_resume_failclosed_when_run_not_resumable(monkeypatch):
    # Run is closed -> build_action_card(kind='resume') denies; only explain cards survive.
    _set_runs(monkeypatch, [_run(55, status="completed")])
    hints = AssistantContextHints(route="/workflows/runs/55", run_id=55)

    cards = nav.build_navigator_cards(_no_write_db(), _user(), hints, max_cards=10)

    assert [c.kind for c in cards] == ["explain"] * len(nav._COMPANION_EXPLAINS)
    assert not any(c.kind == "resume" for c in cards)


def test_navigator_companion_resume_failclosed_when_run_not_owned(monkeypatch):
    # The owner-scoped list never includes the requested run -> no resume card, no disclosure.
    _set_runs(monkeypatch, [])
    hints = AssistantContextHints(route="/workflows/runs/55", run_id=55)

    cards = nav.build_navigator_cards(_no_write_db(), _user(), hints, max_cards=10)

    assert not any(c.kind == "resume" for c in cards)
    assert all(c.kind == "explain" for c in cards)


def test_navigator_companion_respects_cap(monkeypatch):
    _set_runs(monkeypatch, [_run(55)])
    hints = AssistantContextHints(route="/workflows/runs/55", run_id=55)
    cards = nav.build_navigator_cards(_no_write_db(), _user(), hints, max_cards=2)
    assert len(cards) == 2


def test_navigator_falls_back_to_generic_without_run_id(monkeypatch):
    # Regression: with NO run_id the navigator is the ordinary page navigator, not Companion Mode.
    _set_runs(monkeypatch, [])
    cards = nav.build_navigator_cards(
        _no_write_db(), _user(), AssistantContextHints(route="/settings")
    )
    # The generic route yields only the page-explain card (its prompt is NOT a Companion prompt).
    assert [c.kind for c in cards] == ["explain"]
    companion_prompts = {p for _, p in nav._COMPANION_EXPLAINS}
    assert cards[0].prompt not in companion_prompts


# === 4. /suggested-prompts endpoint params (Phase 2) ============================================


def test_suggested_prompts_endpoint_companion_with_run_id(client, _enable_flag, system_user_id):
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.get(
            "/api/assistant/suggested-prompts",
            params={"route": "/data-room/x", "run_id": 55, "workflow_id": "wf_x", "step_id": "s1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # run_id flips the surface to Companion even though the route would map to Data Room.
        assert body["context_label"] == "Workflow Companion"
        assert body["prompts"]
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_suggested_prompts_endpoint_route_mapping_without_run_id(client, _enable_flag, system_user_id):
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.get("/api/assistant/suggested-prompts", params={"route": "/data-room/x"})
        assert resp.status_code == 200
        assert resp.json()["context_label"] == "Data Room"
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def test_suggested_prompts_endpoint_flag_gate_applies_with_run_id(client, system_user_id):
    from app.routers import assistant as assistant_router_module

    assistant_router_module.settings.native_assistant_enabled = False
    test_app.dependency_overrides[get_current_user] = lambda: _user(system_user_id)
    try:
        resp = client.get("/api/assistant/suggested-prompts", params={"run_id": 55})
        assert resp.status_code == 404  # flag gate runs regardless of Companion context
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


# === 5. Companion system addendum + grounded, zero-write chat (Phase 2) =========================


def test_companion_addendum_only_with_run_id():
    with_run = AssistantChatRequest(
        message="explain this step",
        context=AssistantContextHints(run_id=55, workflow_id="wf_x", step_id="s1"),
    )
    without_run = AssistantChatRequest(
        message="hi", context=AssistantContextHints(route="/project-hub")
    )
    assert assistant_service._companion_addendum(with_run) == assistant_service.COMPANION_MODE_ADDENDUM
    assert assistant_service._companion_addendum(without_run) is None
    assert assistant_service._companion_addendum(AssistantChatRequest(message="hi")) is None


def test_build_messages_appends_companion_turn_and_run_context():
    req = AssistantChatRequest(
        message="explain this step",
        context=AssistantContextHints(
            route="/workflows/runs/55", run_id=55, workflow_id="wf_x", step_id="s1"
        ),
    )
    messages = assistant_service._build_messages(req)
    system_blob = "\n".join(m["content"] for m in messages if m["role"] == "system")
    assert "WORKFLOW COMPANION MODE" in system_blob
    # The advisory preamble carries the run/step identifiers (never form values or tokens).
    assert "run_id=55" in system_blob
    assert "workflow_id=wf_x" in system_blob
    assert "step_id=s1" in system_blob


def test_build_messages_has_no_companion_turn_without_run_id():
    req = AssistantChatRequest(message="hi", context=AssistantContextHints(route="/project-hub"))
    messages = assistant_service._build_messages(req)
    system_blob = "\n".join(m["content"] for m in messages if m["role"] == "system")
    assert "WORKFLOW COMPANION MODE" not in system_blob


def test_companion_chat_grounds_in_get_workflow_run_with_zero_writes(monkeypatch):
    db = _no_write_db()
    scripted = _ScriptedClient(
        [
            _response(_message(tool_calls=[_tool_call("c1", "get_workflow_run", '{"run_id": 55}')])),
            _response(_message(content="You're on the 'Project basics' step; name is required.")),
        ]
    )
    monkeypatch.setattr(assistant_service.llm_client, "create_chat_completion", scripted)
    # The Companion grounds via the read-only get_workflow_run tool; stub it to a run envelope.
    monkeypatch.setattr(
        tools,
        "dispatch_tool",
        lambda *a, **k: {"run": {"id": 55, "status": "active"}, "current_step": {"id": "s1"}},
    )

    resp = assistant_service.run_assistant_chat(
        db,
        _user(),
        AssistantChatRequest(
            message="explain this step",
            context=AssistantContextHints(run_id=55, workflow_id="wf_x", step_id="s1"),
        ),
    )

    assert [t.name for t in resp.used_tools] == ["get_workflow_run"]
    # The Companion Mode system turn reached the model.
    first_call_systems = "\n".join(
        m["content"] for m in scripted.calls[0]["messages"] if m["role"] == "system"
    )
    assert "WORKFLOW COMPANION MODE" in first_call_systems
    _assert_no_writes(db)


# === 6. Zero-execution / no-second-path proof ===================================================


def test_no_engine_write_fn_is_exposed_as_a_tool():
    # The engine's mutation/execution functions must never be callable through the assistant.
    for fn in _ENGINE_WRITE_FNS:
        assert fn not in tools.ALLOWED_TOOLS
        assert fn not in tools.TOOL_HANDLERS
        assert fn not in {s["function"]["name"] for s in tools.TOOL_SPECS}


def test_guardrail_keywords_block_every_engine_write_fn():
    # Defense-in-depth: even if a write fn were ever named as a tool, the guardrail keyword screen
    # must flag it (start/save/preview/execute/abandon are all covered keywords).
    for fn in _ENGINE_WRITE_FNS:
        assert guardrails.is_prohibited(fn), f"{fn} must be screened by the guardrail keywords"


def test_assistant_package_never_references_engine_write_fns():
    """Source-level no-second-path proof: no module under app/services/assistant/ references any
    engine WRITE/EXECUTE function by name. The Companion only ever reads (get_run / list_user_runs);
    the Workflow Engine remains the single execution path."""
    pkg_dir = pathlib.Path(assistant_service.__file__).parent
    offenders: dict[str, list[str]] = {}
    for path in sorted(pkg_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        hits = [fn for fn in _ENGINE_WRITE_FNS if fn in text]
        if hits:
            offenders[path.name] = hits
    assert offenders == {}, f"engine write fns referenced in assistant package: {offenders}"
