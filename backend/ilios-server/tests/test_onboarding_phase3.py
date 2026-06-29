"""Unit tests for Native Onboarding Phase 3 — guided portfolio setup & AI-orchestration readiness.

These cover the Phase-3 invariants that keep the new aggregation layer "advice, never action":

* the three declarative sequences are registered and serialize with their cross-step prefill hints,
* the readiness summary degrades PER SECTION (permission_denied / unavailable) and never raises,
* onboarding progress excludes stages the caller can't evaluate from the completion ratio,
* recommendations are deterministic, permission-scoped, and ordered by priority,
* the orchestration context is a versioned, read-only envelope with explicit prohibited actions,
* none of the new services ever write/commit on the session (they only read).

Style mirrors ``tests/test_workflow_engine.py``: pure Mock/patch unit tests, no live DB rows.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.workflow import WorkflowRunStatus
from app.schema.workflow import (
    OnboardingProgressResponse,
    ReadinessSummaryResponse,
    RecommendationsResponse,
    SequenceListResponse,
    WorkflowListResponse,
    WorkflowMetricsResponse,
    WorkflowRunListResponse,
)
from app.services.workflows import definitions, engine
from app.services.workflows import onboarding_progress_service as progress_svc
from app.services.workflows import readiness_summary_service as readiness_svc
from app.services.workflows import recommendations_service as rec_svc
from app.services.workflows import orchestration_context_service as ctx_svc


def _bypass_user(user_id: int = 1, bypass: bool = True):
    return SimpleNamespace(id=user_id, has_platform_bypass=bypass)


def _site(site_id=1, name="Solar One", company_id=3):
    return SimpleNamespace(id=site_id, name=name, company_id=company_id)


def _health(status="HEALTHY", connected=True, mapped=True):
    return SimpleNamespace(
        status=SimpleNamespace(value=status),
        is_connected=connected,
        is_site_mapped=mapped,
        mapped_device_count=4,
        last_data_at=None,
        data_delay_minutes=5,
    )


def _recon(facts_ready=True, missing=None, active_id=None, design_id=None):
    return SimpleNamespace(
        readiness=SimpleNamespace(
            facts_to_draft_ready=facts_ready,
            missing_required_physics_fields=missing or [],
            active_baseline_available=active_id is not None,
            active_baseline_id=active_id,
            design_estimate_baseline_id=design_id,
        )
    )


def _diag():
    return SimpleNamespace(
        total_devices=10,
        mappable_count=8,
        mapped_count=6,
        expected_driving_count=4,
        unmapped_eligible_count=2,
        weather_unknown_semantics_count=1,
    )


# --- Sequences + declarative prefill (B1) --------------------------------------------


class TestPhase3Sequences:
    def test_three_sequences_registered(self):
        assert set(definitions.SEQUENCES) == {
            "onboarding",
            "site_diligence",
            "portfolio_setup",
        }

    def test_new_sequence_steps(self):
        sd = definitions.get_sequence("site_diligence")
        ps = definitions.get_sequence("portfolio_setup")
        assert [s.workflow_id for s in sd.steps] == [
            "add_site",
            "document_upload",
            "parse_document",
        ]
        assert [s.workflow_id for s in ps.steps] == [
            "add_company",
            "add_site",
            "invite_user",
        ]

    def test_prefill_serialized_for_bypass_user(self):
        resp = engine.list_sequences(Mock(), _bypass_user(bypass=True))
        assert len(resp.items) == 3
        sd = next(s for s in resp.items if s.id == "site_diligence")
        # document_upload + parse_document prefill site_id from the add_site step (index 0).
        upload = next(s for s in sd.steps if s.workflow_id == "document_upload")
        assert any(
            h.target_field == "site_id" and h.from_step_index == 0
            for h in upload.prefill
        )

    def test_prefill_must_reference_earlier_step(self):
        bad = definitions.SequenceDef(
            id="bad",
            title="Bad",
            description="d",
            category="X",
            steps=(
                definitions.SequenceStepDef(
                    "add_company",
                    "A",
                    "d",
                    prefill=(definitions.PrefillHint("company_id", 0),),
                ),
            ),
        )
        # A step cannot prefill from itself (index 0 referencing step 0).
        import pytest

        with pytest.raises(definitions.WorkflowDefinitionError):
            definitions.validate_sequence(bad)


# --- Onboarding progress (B2) --------------------------------------------------------


class TestOnboardingProgress:
    def test_unavailable_stages_excluded_from_ratio(self):
        with patch.object(
            progress_svc, "resolve_candidate_sites", return_value=[_site()]
        ), patch.object(
            progress_svc, "can_view_diligence", return_value=False
        ), patch(
            "app.services.telemetry.health_service.compute_site_telemetry_health",
            return_value=_health(),
        ), patch(
            "app.crud.telemetry_expected.TelemetryExpectedBaselineCRUD"
        ) as crud_cls:
            crud_cls.return_value.get_active.return_value = SimpleNamespace(id=99)
            resp = progress_svc.build_onboarding_progress(Mock(), _bypass_user())

        item = resp.items[0]
        diligence_stages = [
            s for s in item.stages if s.key.startswith(("diligence", "expected_baseline_drafted"))
        ]
        assert all(not s.available for s in diligence_stages)
        # 4 evaluable stages (project_created, baseline_active, telemetry_connected, healthy).
        assert item.total_stages == 4
        assert item.completed_stages == 4
        assert item.completion_rate == 1.0

    def test_returns_response_model(self):
        with patch.object(progress_svc, "resolve_candidate_sites", return_value=[]):
            resp = progress_svc.build_onboarding_progress(Mock(), _bypass_user())
        assert isinstance(resp, OnboardingProgressResponse)
        assert resp.total_sites == 0


# --- Readiness summary per-section degradation (B2) ----------------------------------


class TestReadinessDegradation:
    def test_sections_degrade_independently_and_never_raise(self):
        with patch.object(
            readiness_svc, "resolve_candidate_sites", return_value=[_site()]
        ), patch.object(
            readiness_svc, "can_view_diligence", return_value=False
        ), patch(
            "app.services.telemetry.health_service.compute_site_telemetry_health",
            side_effect=RuntimeError("boom"),
        ), patch(
            "app.services.telemetry.device_eligibility_diagnostics_service.compute_site_eligibility_diagnostics",
            return_value=_diag(),
        ), patch(
            "app.crud.telemetry_expected.TelemetryExpectedBaselineCRUD"
        ) as crud_cls:
            crud_cls.return_value.get_active.return_value = None
            crud_cls.return_value.list_for_site.return_value = []
            resp = readiness_svc.build_readiness_summary(Mock(), _bypass_user())

        site = resp.items[0]
        # Diligence denied -> permission_denied; telemetry raised -> unavailable.
        assert site.reconciliation.available is False
        assert site.reconciliation.reason == "permission_denied"
        assert site.telemetry_health.available is False
        assert site.telemetry_health.reason == "unavailable"
        # Independent sections still succeed.
        assert site.device_eligibility.available is True
        assert site.expected_baseline.available is True
        assert site.expected_baseline.status == "none"

    def test_reconciliation_present_when_permitted(self):
        with patch.object(
            readiness_svc, "resolve_candidate_sites", return_value=[_site()]
        ), patch.object(
            readiness_svc, "can_view_diligence", return_value=True
        ), patch(
            "app.services.due_diligence.reconciliation_service.build_site_reconciliation",
            return_value=_recon(facts_ready=True, active_id=7),
        ), patch(
            "app.services.telemetry.health_service.compute_site_telemetry_health",
            return_value=_health(),
        ), patch(
            "app.services.telemetry.device_eligibility_diagnostics_service.compute_site_eligibility_diagnostics",
            return_value=_diag(),
        ), patch(
            "app.crud.telemetry_expected.TelemetryExpectedBaselineCRUD"
        ) as crud_cls:
            crud_cls.return_value.get_active.return_value = SimpleNamespace(id=7)
            crud_cls.return_value.list_for_site.return_value = [SimpleNamespace(status=SimpleNamespace(value="active"))]
            resp = readiness_svc.build_readiness_summary(Mock(), _bypass_user())

        site = resp.items[0]
        assert site.reconciliation.available is True
        assert site.reconciliation.status == "ready"
        assert site.reconciliation.data["active_baseline_id"] == 7


# --- Recommendations ordering (B2) ---------------------------------------------------


class TestRecommendations:
    def test_no_sites_recommends_onboarding_sequence(self):
        empty = SimpleNamespace(items=[])
        seqs = SimpleNamespace(
            items=[
                SimpleNamespace(id="onboarding", title="Start onboarding", can_start=True)
            ]
        )
        with patch("app.services.workflows.engine.list_sequences", return_value=seqs), patch(
            "app.services.workflows.engine.list_user_runs",
            return_value=WorkflowRunListResponse(items=[]),
        ), patch.object(rec_svc, "build_onboarding_progress", return_value=empty):
            resp = rec_svc.build_recommendations(Mock(), _bypass_user())

        assert isinstance(resp, RecommendationsResponse)
        assert len(resp.items) == 1
        assert resp.items[0].kind == "sequence"
        assert resp.items[0].sequence_id == "onboarding"

    def test_deterministic_priority_ordering(self):
        run = SimpleNamespace(
            id=5,
            workflow_id="add_company",
            workflow_title="Add Company",
            status=WorkflowRunStatus.active,
            site_id=None,
            company_id=3,
        )
        progress = SimpleNamespace(
            items=[
                SimpleNamespace(
                    site_id=1,
                    site_name="S1",
                    company_id=3,
                    stages=[
                        SimpleNamespace(
                            key="diligence_facts_ready", available=True, done=False
                        )
                    ],
                )
            ],
        )
        with patch(
            "app.services.workflows.engine.list_sequences",
            return_value=SequenceListResponse(items=[]),
        ), patch(
            "app.services.workflows.engine.list_user_runs",
            return_value=SimpleNamespace(items=[run]),
        ), patch.object(
            rec_svc, "build_onboarding_progress", return_value=progress
        ), patch.object(
            rec_svc, "_can_start_workflow", return_value=True
        ):
            resp = rec_svc.build_recommendations(Mock(), _bypass_user())

        priorities = [r.priority for r in resp.items]
        assert priorities == sorted(priorities)
        # resume (10) < document_upload (30) < invite (50)
        assert resp.items[0].title.startswith("Resume")
        assert any(
            r.workflow_id == "document_upload" and r.target_site_id == 1
            for r in resp.items
        )

    def test_upload_recommendation_requires_target_site_diligence_edit(self):
        """A site can be visible + Diligence-VIEWable (so its progress stage is evaluable) yet not
        Diligence-EDITable — the upload workflow needs ``edit``, so it must NOT be recommended for
        that site (no dead-end card), even though ``_can_start_workflow`` is generally True."""
        progress = SimpleNamespace(
            items=[
                SimpleNamespace(
                    site_id=1,
                    site_name="S1",
                    company_id=3,
                    stages=[
                        SimpleNamespace(
                            key="diligence_facts_ready", available=True, done=False
                        )
                    ],
                )
            ],
        )

        def _run(editable_return):
            with patch(
                "app.services.workflows.engine.list_sequences",
                return_value=SequenceListResponse(items=[]),
            ), patch(
                "app.services.workflows.engine.list_user_runs",
                return_value=WorkflowRunListResponse(items=[]),
            ), patch.object(
                rec_svc, "build_onboarding_progress", return_value=progress
            ), patch.object(
                rec_svc, "_can_start_workflow", return_value=True
            ), patch.object(
                definitions,
                "_diligence_editable_site_ids",
                return_value=editable_return,
            ):
                return rec_svc.build_recommendations(Mock(), _bypass_user(bypass=False))

        # View-only target (not in the editable set): no upload card for site 1.
        denied = _run(set())
        assert not any(r.workflow_id == "document_upload" for r in denied.items)

        # Editable target: the upload card reappears for the same site.
        allowed = _run({1})
        assert any(
            r.workflow_id == "document_upload" and r.target_site_id == 1
            for r in allowed.items
        )

    def test_governed_actions_never_recommended(self):
        progress = SimpleNamespace(
            items=[
                SimpleNamespace(
                    site_id=1, site_name="S1", company_id=3, stages=[]
                )
            ],
        )
        with patch(
            "app.services.workflows.engine.list_sequences",
            return_value=SequenceListResponse(items=[]),
        ), patch(
            "app.services.workflows.engine.list_user_runs",
            return_value=WorkflowRunListResponse(items=[]),
        ), patch.object(
            rec_svc, "build_onboarding_progress", return_value=progress
        ), patch.object(
            rec_svc, "_can_start_workflow", return_value=True
        ):
            resp = rec_svc.build_recommendations(Mock(), _bypass_user())

        wf_ids = {r.workflow_id for r in resp.items}
        # None of the governed/operational mutations are ever surfaced as a runnable action.
        assert not (
            wf_ids
            & {
                "promote_fact",
                "activate_baseline",
                "map_device",
                "declare_weather",
            }
        )


# --- Orchestration context envelope (B2) --------------------------------------------


class TestOrchestrationContext:
    def test_versioned_read_only_envelope(self):
        now = datetime.now(timezone.utc)
        with patch(
            "app.services.workflows.engine.list_workflow_definitions",
            return_value=WorkflowListResponse(items=[]),
        ), patch(
            "app.services.workflows.engine.list_sequences",
            return_value=SequenceListResponse(items=[]),
        ), patch(
            "app.services.workflows.engine.list_user_runs",
            return_value=WorkflowRunListResponse(items=[]),
        ), patch(
            "app.services.workflows.engine.compute_metrics",
            return_value=WorkflowMetricsResponse(
                scope="me",
                total_runs=0,
                completed_runs=0,
                abandoned_runs=0,
                in_progress_runs=0,
                completion_rate=0.0,
                abandonment_rate=0.0,
                by_workflow=[],
            ),
        ), patch(
            "app.services.workflows.onboarding_progress_service.build_onboarding_progress",
            return_value=OnboardingProgressResponse(
                generated_at=now, scope="me", total_sites=0, items=[]
            ),
        ), patch(
            "app.services.workflows.readiness_summary_service.build_readiness_summary",
            return_value=ReadinessSummaryResponse(
                generated_at=now, scope="me", total_sites=0, items=[]
            ),
        ), patch(
            "app.services.workflows.recommendations_service.build_recommendations",
            return_value=RecommendationsResponse(
                generated_at=now, scope="me", items=[]
            ),
        ):
            ctx = ctx_svc.build_orchestration_context(Mock(), _bypass_user())

        assert ctx.schema_version == "workflow_orchestration_context.v1"
        assert ctx.mode == "read_only_advice"
        assert ctx.actor_scope == "me"
        # Explicit, machine-readable non-execution markers must include the governed actions.
        for forbidden in (
            "promote_project_fact",
            "approve_or_activate_expected_baseline",
            "map_or_unmap_device",
            "create_or_change_weather_declaration",
            "bypass_authorization_or_permissions",
        ):
            assert forbidden in ctx.prohibited_actions


# --- The new services never write (B2 hard constraint) ------------------------------


class TestNoWrites:
    def _assert_no_writes(self, db_session):
        db_session.add.assert_not_called()
        db_session.commit.assert_not_called()
        db_session.delete.assert_not_called()
        db_session.flush.assert_not_called()

    def test_progress_and_readiness_never_write(self):
        db = Mock()
        with patch.object(progress_svc, "resolve_candidate_sites", return_value=[]):
            progress_svc.build_onboarding_progress(db, _bypass_user())
        with patch.object(readiness_svc, "resolve_candidate_sites", return_value=[]):
            readiness_svc.build_readiness_summary(db, _bypass_user())
        self._assert_no_writes(db)
