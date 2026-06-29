"""Unit tests for the native Workflow Engine foundation + the Add Company pilot.

These cover the governance/safety invariants that make "the engine never silently mutates
operational truth" structurally true (audit §6/§7/§9):

* the load-time definition guard rejects governed/auto-execute/none-confirmation misuse,
* the authoritative permission re-check is fail-closed (unknown tokens refused) and audited,
* execute is idempotent (per-step and per-idempotency-key) and never double-writes,
* the blast-radius confirm token forces a re-confirm when the reviewed inputs change,
* the write step dispatches to the EXISTING company-create endpoint (no parallel mutation),
* a successful execute writes a workflow_engine audit row linking the run -> produced entity.

They are pure unit tests (Mock/patch, no live DB rows) following the same style as
``tests/integration/test_site_creation_permissions.py`` — the engine's collaborators
(CRUD, executor, audit) are patched at the engine module boundary so the orchestration logic
itself is exercised in isolation.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.schema.company import CreateCompanySchema
from app.schema.site import CreateSiteSchema
from app.services.workflows import definitions, engine, executors
from app.services.workflows.definitions import (
    ADD_COMPANY,
    ADD_SITE,
    CONFIRMATION_GOVERNED,
    CONFIRMATION_NONE,
    CONFIRMATION_STANDARD,
    REGISTRY,
    STEP_COLLECT,
    STEP_EXECUTE,
    FieldDef,
    StepDef,
    WorkflowDef,
    WorkflowDefinitionError,
    validate_definition,
)
from app.schema.workflow import ExecuteRequest
from app.services.workflows.engine import WorkflowEngineError
from app.models.workflow import WorkflowRunStatus

# Valid inputs for the add_company collect step (satisfy CreateCompanySchema).
COMPANY_INPUTS = {
    "name": "Green Lantern",
    "company_type": "Investor",
    "address": "719 Main Street",
    "city": "Mullica Hill",
    "state": "NJ",
    "zip_code": "08062",
}

EXECUTE_STEP_ID = "review_and_create"


def _bypass_user(user_id: int = 1, bypass: bool = True):
    """A current_user stand-in; the engine reads ``has_platform_bypass`` + ``id`` only."""
    return SimpleNamespace(id=user_id, has_platform_bypass=bypass)


def _wf(steps):
    return WorkflowDef(
        id="t",
        version="1",
        title="T",
        description="d",
        entry_permission="platform_admin",
        steps=tuple(steps),
    )


# --- Load-time definition guard (audit §7/§9) ----------------------------------------


class TestDefinitionGuard:
    """validate_definition() runs at import time and must fail closed on misuse."""

    def test_real_add_company_definition_is_valid(self):
        # The real pilot definition imported cleanly (would have raised otherwise).
        assert validate_definition(ADD_COMPANY) is None
        assert "add_company" in REGISTRY

    def test_add_company_has_collect_then_execute_steps(self):
        kinds = [s.kind for s in ADD_COMPANY.steps]
        assert kinds == [STEP_COLLECT, STEP_EXECUTE]
        execute_step = ADD_COMPANY.steps[1]
        assert execute_step.id == EXECUTE_STEP_ID
        assert execute_step.confirmation == CONFIRMATION_STANDARD
        assert execute_step.governed is False

    def test_empty_workflow_rejected(self):
        with pytest.raises(WorkflowDefinitionError, match="no steps"):
            validate_definition(_wf([]))

    def test_governed_step_must_use_governed_confirmation(self):
        step = StepDef("s", "S", STEP_EXECUTE, CONFIRMATION_STANDARD, governed=True)
        with pytest.raises(WorkflowDefinitionError, match="confirmation='governed'"):
            validate_definition(_wf([step]))

    def test_governed_step_must_not_auto_execute(self):
        step = StepDef(
            "s", "S", STEP_EXECUTE, CONFIRMATION_GOVERNED, governed=True, auto_execute=True
        )
        with pytest.raises(WorkflowDefinitionError, match="auto_execute"):
            validate_definition(_wf([step]))

    def test_write_step_must_not_use_none_confirmation(self):
        step = StepDef("s", "S", STEP_EXECUTE, CONFIRMATION_NONE)
        with pytest.raises(WorkflowDefinitionError, match="confirmation='none'"):
            validate_definition(_wf([step]))

    def test_write_step_must_not_auto_execute(self):
        step = StepDef("s", "S", STEP_EXECUTE, CONFIRMATION_STANDARD, auto_execute=True)
        with pytest.raises(WorkflowDefinitionError, match="human confirm required"):
            validate_definition(_wf([step]))

    def test_collect_step_must_use_none_confirmation(self):
        step = StepDef("s", "S", STEP_COLLECT, CONFIRMATION_STANDARD)
        with pytest.raises(WorkflowDefinitionError, match="confirmation='none'"):
            validate_definition(_wf([step]))

    def test_duplicate_step_id_rejected(self):
        steps = [
            StepDef("dup", "A", STEP_COLLECT, CONFIRMATION_NONE),
            StepDef("dup", "B", STEP_COLLECT, CONFIRMATION_NONE),
        ]
        with pytest.raises(WorkflowDefinitionError, match="duplicate step"):
            validate_definition(_wf(steps))

    def test_unknown_kind_rejected(self):
        step = StepDef("s", "S", "weird", CONFIRMATION_NONE)
        with pytest.raises(WorkflowDefinitionError, match="unknown kind"):
            validate_definition(_wf([step]))

    def test_unknown_confirmation_rejected(self):
        step = StepDef("s", "S", STEP_COLLECT, "weird")
        with pytest.raises(WorkflowDefinitionError, match="unknown confirmation"):
            validate_definition(_wf([step]))


# --- Fail-closed permission re-check (audit §6) --------------------------------------


class TestPermissionGuard:
    def test_none_permission_is_allowed(self):
        assert engine._ensure_permission(None, _bypass_user(bypass=False), Mock()) is None

    def test_platform_admin_requires_bypass(self):
        with pytest.raises(HTTPException) as exc:
            engine._ensure_permission("platform_admin", _bypass_user(bypass=False), Mock())
        assert exc.value.status_code == 403

    def test_platform_admin_allowed_with_bypass(self):
        assert engine._ensure_permission("platform_admin", _bypass_user(bypass=True), Mock()) is None

    def test_unknown_permission_token_is_refused_even_for_bypass_user(self):
        # Fail-closed: an unrecognized requirement is refused, never silently allowed.
        with pytest.raises(HTTPException) as exc:
            engine._ensure_permission("frobnicate", _bypass_user(bypass=True), Mock())
        assert exc.value.status_code == 403

    def test_missing_attribute_defaults_to_no_bypass(self):
        assert engine._has_platform_bypass(SimpleNamespace()) is False


# --- Executor wiring: dispatch to the EXISTING endpoint (audit §4/§8) ----------------


class TestExecutorWiring:
    def test_add_company_uses_dedicated_executor(self):
        assert executors.get_executor("add_company") is executors._execute_add_company

    def test_unknown_workflow_has_no_executor(self):
        # Governed terminals / unmapped workflows have no executor and can never auto-write.
        assert executors.get_executor("does_not_exist") is None

    def test_execute_add_company_invokes_real_create_company_endpoint(self):
        with patch(
            "app.routers.assets_management.companies.create_company", new_callable=AsyncMock
        ) as mock_endpoint:
            mock_endpoint.return_value = SimpleNamespace(id=777)
            result = asyncio.run(
                executors._execute_add_company(Mock(), _bypass_user(), dict(COMPANY_INPUTS))
            )

        assert result == ("company", 777)
        mock_endpoint.assert_awaited_once()
        payload = mock_endpoint.await_args.kwargs["payload"]
        assert isinstance(payload, CreateCompanySchema)
        assert payload.name == "Green Lantern"


# --- Engine execute_step orchestration -----------------------------------------------


class _EngineHarness:
    """Patches the engine's collaborators and tracks the mocks for assertions."""

    def __init__(
        self,
        *,
        user=None,
        run_status=WorkflowRunStatus.active,
        review_state=None,
        idempotency_lookup=None,
        collect_inputs=None,
    ):
        self.user = user if user is not None else _bypass_user()
        self.run = SimpleNamespace(
            id=10,
            status=run_status,
            workflow_id="add_company",
            current_step=EXECUTE_STEP_ID,
        )
        self.review_state = review_state
        self.idempotency_lookup = idempotency_lookup
        self.collect_inputs = collect_inputs if collect_inputs is not None else dict(COMPANY_INPUTS)
        self.executor = AsyncMock(return_value=("company", 777))

    def _get_run_step(self, run_id, step_id):
        if step_id == "company_details":
            return SimpleNamespace(inputs=self.collect_inputs)
        return self.review_state

    def __enter__(self):
        self._patches = [
            patch("app.services.workflows.engine.WorkflowRunCRUD"),
            patch("app.services.workflows.engine.WorkflowStepStateCRUD"),
            patch("app.services.workflows.engine.get_executor", return_value=self.executor),
            patch("app.services.workflows.engine.create_workflow_audit_log", return_value=555),
        ]
        self.run_crud, self.step_crud_cls, self.get_executor, self.audit = (
            p.start() for p in self._patches
        )
        self.run_crud.return_value.get_for_user.return_value = self.run

        step_crud = self.step_crud_cls.return_value
        step_crud.get_run_step.side_effect = self._get_run_step
        step_crud.get_by_idempotency_key.return_value = self.idempotency_lookup
        step_crud.db_session = Mock()
        step_crud.db_session.get.return_value = SimpleNamespace(
            status=None, current_step=None
        )
        self.step_crud = step_crud
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()

    def execute(self, confirm_token=None, idempotency_key=None):
        if confirm_token is None:
            confirm_token = engine._confirm_token(self.run.id, EXECUTE_STEP_ID, self.collect_inputs)
        req = ExecuteRequest(confirm_token=confirm_token, idempotency_key=idempotency_key)
        return asyncio.run(
            engine.execute_step(Mock(), self.user, self.run.id, EXECUTE_STEP_ID, req)
        )


class TestExecuteStep:
    def test_happy_path_dispatches_to_executor_and_audits_success(self):
        with _EngineHarness() as h:
            resp = h.execute()

        assert resp.executed is True
        assert resp.entity_type == "company"
        assert resp.entity_id == 777
        assert resp.run_status == WorkflowRunStatus.completed
        h.executor.assert_awaited_once()
        # The success audit links the run/step to the produced entity.
        h.audit.assert_called_once()
        kwargs = h.audit.call_args.kwargs
        assert kwargs["action"] == "workflow.add_company.execute"
        assert kwargs["is_success"] is True
        assert kwargs["governed"] is False
        assert kwargs["details"]["entity_id"] == 777

    def test_permission_denied_is_fail_closed_and_audited(self):
        with _EngineHarness(user=_bypass_user(bypass=False)) as h:
            with pytest.raises(HTTPException) as exc:
                h.execute()

        assert exc.value.status_code == 403
        h.executor.assert_not_awaited()
        h.get_executor.assert_not_called()
        h.audit.assert_called_once()
        kwargs = h.audit.call_args.kwargs
        assert kwargs["is_success"] is False
        assert kwargs["details"]["outcome"] == "refused_permission"

    def test_blast_radius_reconfirm_when_token_stale(self):
        with _EngineHarness() as h:
            with pytest.raises(WorkflowEngineError) as exc:
                h.execute(confirm_token="stale-token")

        assert exc.value.status_code == 409
        assert exc.value.payload["code"] == "reconfirm_required"
        h.executor.assert_not_awaited()

    def test_idempotent_when_step_already_executed(self):
        prior = SimpleNamespace(
            executed=True, result_entity_type="company", result_entity_id=42
        )
        with _EngineHarness(review_state=prior) as h:
            resp = h.execute()

        assert resp.executed is True
        assert resp.entity_id == 42
        h.executor.assert_not_awaited()
        h.get_executor.assert_not_called()

    def test_idempotent_when_idempotency_key_reused(self):
        prior = SimpleNamespace(
            executed=True, result_entity_type="company", result_entity_id=99
        )
        with _EngineHarness(idempotency_lookup=prior) as h:
            resp = h.execute(idempotency_key="dup-key")

        assert resp.executed is True
        assert resp.entity_id == 99
        h.executor.assert_not_awaited()

    def test_execute_refused_on_non_active_run(self):
        with _EngineHarness(run_status=WorkflowRunStatus.completed) as h:
            with pytest.raises(HTTPException) as exc:
                h.execute()

        assert exc.value.status_code == 409
        h.executor.assert_not_awaited()


# =====================================================================================
# Pilot 2: Add Site / Project. These prove the engine generalizes to a SECOND flow that
# uses a company-scoped permission model (not platform_admin) and a DYNAMIC select.
# =====================================================================================

# Valid inputs for the add_site collect step (satisfy CreateSiteSchema). company_id and the
# numeric sizes arrive as STRINGS from the FE SearchableSelect/number inputs; the schema must
# coerce them, which these inputs deliberately exercise.
SITE_INPUTS = {
    "company_id": "5",
    "name": "Apollo",
    "address": "719 Main Street",
    "city": "Mullica Hill",
    "state": "NJ",
    "zip_code": "08062",
    "county": "Gloucester",
    "system_size_ac": "1000",
    "system_size_dc": "1200",
    "lon_lat_url": "41.9486, -72.6443",
    "timezone": "America/New_York",
}


class TestAddSiteDefinition:
    def test_real_add_site_definition_is_valid(self):
        # The real pilot-2 definition imported cleanly (would have raised otherwise).
        assert validate_definition(ADD_SITE) is None
        assert "add_site" in REGISTRY

    def test_add_site_has_collect_then_execute_steps(self):
        kinds = [s.kind for s in ADD_SITE.steps]
        assert kinds == [STEP_COLLECT, STEP_EXECUTE]
        execute_step = ADD_SITE.steps[1]
        assert execute_step.id == "review_and_create"
        assert execute_step.confirmation == CONFIRMATION_STANDARD
        assert execute_step.governed is False
        assert execute_step.audit_action == "workflow.add_site.execute"

    def test_add_site_entry_permission_is_company_scoped(self):
        # Distinct permission model from add_company (platform_admin).
        assert ADD_SITE.entry_permission == "assets_management:create_site"
        for step in ADD_SITE.steps:
            assert step.required_permission == "assets_management:create_site"

    def test_add_site_has_success_message(self):
        assert ADD_SITE.success_message == "Project created successfully."

    def test_add_site_collects_company_picker_and_number_fields(self):
        collect = ADD_SITE.steps[0]
        by_name = {f.name: f for f in collect.inputs}
        assert by_name["company_id"].type == "select"
        assert by_name["company_id"].options_source == "companies"
        assert by_name["timezone"].options_source == "us_timezones"
        assert by_name["system_size_ac"].type == "number"
        assert by_name["system_size_dc"].type == "number"

    def test_add_site_schema_mappings(self):
        assert definitions.get_payload_schema("add_site") is CreateSiteSchema
        assert (
            definitions.get_step_input_schema("add_site", "project_details") is CreateSiteSchema
        )


class TestAddSitePermission:
    """The company-scoped token is fail-closed at the authoritative re-check."""

    @staticmethod
    def _edit_user(companies):
        return SimpleNamespace(
            id=2,
            has_platform_bypass=False,
            get_limited_companies_ids=lambda: list(companies),
        )

    def test_create_site_refused_without_company_access(self):
        # No accessible company -> the coarse gate refuses before any per-company check.
        user = self._edit_user([])
        with pytest.raises(HTTPException) as exc:
            engine._ensure_permission("assets_management:create_site", user, Mock())
        assert exc.value.status_code == 403

    def test_create_site_allowed_with_company_edit(self):
        user = self._edit_user([5])
        with patch(
            "app.services.workflows.engine.require_module_permission_any_company",
            return_value=True,
        ) as guard:
            assert (
                engine._ensure_permission("assets_management:create_site", user, Mock()) is None
            )
        guard.assert_called_once()

    def test_create_site_refused_when_company_guard_denies(self):
        user = self._edit_user([5])
        with patch(
            "app.services.workflows.engine.require_module_permission_any_company",
            side_effect=HTTPException(status_code=403, detail="no edit"),
        ):
            with pytest.raises(HTTPException) as exc:
                engine._ensure_permission("assets_management:create_site", user, Mock())
        assert exc.value.status_code == 403

    def test_create_site_allowed_for_platform_bypass(self):
        # Platform-bypass short-circuits before any company lookup.
        assert (
            engine._ensure_permission(
                "assets_management:create_site", _bypass_user(bypass=True), Mock()
            )
            is None
        )


class TestAddSiteExecutor:
    def test_add_site_uses_dedicated_executor(self):
        assert executors.get_executor("add_site") is executors._execute_add_site

    def test_execute_add_site_invokes_real_create_site_endpoint(self):
        with patch(
            "app.routers.assets_management.sites.create", new_callable=AsyncMock
        ) as mock_endpoint:
            mock_endpoint.return_value = {
                "code": 201,
                "message": "Site has been created",
                "id": 555,
            }
            result = asyncio.run(
                executors._execute_add_site(Mock(), _bypass_user(), dict(SITE_INPUTS))
            )

        assert result == ("site", 555)
        mock_endpoint.assert_awaited_once()
        payload = mock_endpoint.await_args.kwargs["site"]
        assert isinstance(payload, CreateSiteSchema)
        assert payload.name == "Apollo"
        # The string company_id + numeric sizes from the FE must coerce via the EXISTING schema.
        assert payload.company_id == 5
        assert payload.system_size_ac == 1000


class TestAddSiteOptionResolution:
    def test_us_timezones_includes_utc_and_iana(self):
        opts = definitions.resolve_options("us_timezones")
        values = {o["value"] for o in opts}
        assert "UTC" in values
        assert "America/New_York" in values

    def test_companies_requires_db_and_user(self):
        assert definitions.resolve_options("companies") == []
        assert definitions.resolve_options("companies", Mock(), None) == []

    def test_companies_for_platform_bypass_lists_all_active(self):
        db = Mock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            (1, "Acme"),
            (2, "Beta"),
        ]
        opts = definitions.resolve_options("companies", db, _bypass_user(bypass=True))
        assert opts == [
            {"label": "Acme", "value": "1"},
            {"label": "Beta", "value": "2"},
        ]

    def test_companies_empty_when_non_bypass_has_no_companies(self):
        user = SimpleNamespace(
            id=2, has_platform_bypass=False, get_limited_companies_ids=lambda: []
        )
        assert definitions.resolve_options("companies", Mock(), user) == []


class TestAddSitePreviewWarning:
    """The duplicate-name warning is read-only and NON-blocking (sites have no uniqueness)."""

    def test_warns_when_same_name_site_exists_in_company(self):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=1)
        warnings = engine._build_warnings(db, "add_site", {"name": "Apollo", "company_id": 5})
        assert any("already exists" in w for w in warnings)

    def test_no_warning_when_no_duplicate(self):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        warnings = engine._build_warnings(db, "add_site", {"name": "Apollo", "company_id": 5})
        assert warnings == []
