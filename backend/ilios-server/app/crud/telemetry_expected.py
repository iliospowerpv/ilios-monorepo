"""CRUD for expected-performance baselines (Phase P3.1).

Encapsulates the approval lifecycle so the router stays thin:

* ``create_draft`` — create a ``draft`` baseline, snapshotting loss %, PTO and
  timezone from the site (with abs() loss normalization) when not provided.
* ``approve`` — move a draft/in-review baseline to ``approved`` (stamps reviewer
  + approver). AI-parsed baselines MUST pass through here before activation.
* ``activate`` — only an ``approved`` baseline may be activated; supersedes the
  prior ``active`` baseline of the same type in a single locked transaction. The
  partial unique index ``uq_telemetry_expected_baseline_active`` is the final
  backstop against a race.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.site import SiteAdditionalFieldList
from app.models.telemetry_expected import (
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
)

# Scalar columns a create payload may set directly (snapshot/audit columns and
# the approval state are managed by this CRUD, not the caller).
_CREATE_FIELDS = (
    "baseline_name",
    "baseline_type",
    "source_type",
    "source_document_id",
    "source_project_fact_id",
    "timezone",
    "system_size_ac_kw",
    "system_size_dc_kw",
    "degradation_rate",
    "module_wattage",
    "module_quantity",
    "inverter_wattage",
    "inverter_quantity",
    "thermal_coefficient_pct",
    "power_tolerance_min_pct",
    "year_1_degradation_pct",
    "annual_degradation_pct",
    "cec_efficiency_pct",
    "soiling_factor",
    "dc_loss_pct",
    "ac_loss_pct",
    "medium_voltage_loss_pct",
    "mv_line_loss_pct",
    "pto_date",
    "loss_assumptions_json",
    "model_parameters_json",
    "ai_confidence_json",
    "notes",
)


def _abs_or_none(value):
    """Normalize a loss percentage to positive magnitude (legacy data is mixed-sign)."""
    return None if value is None else abs(value)


class BaselineActivationError(Exception):
    """Raised when an activation/approval transition is not allowed."""


class TelemetryExpectedBaselineCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(model=TelemetryExpectedBaseline, db_session=db_session)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def get(self, baseline_id: int) -> Optional[TelemetryExpectedBaseline]:
        return (
            self.db_session.query(TelemetryExpectedBaseline)
            .filter(TelemetryExpectedBaseline.id == baseline_id)
            .one_or_none()
        )

    def list_for_site(self, site_id: int) -> list[TelemetryExpectedBaseline]:
        return (
            self.db_session.query(TelemetryExpectedBaseline)
            .filter(TelemetryExpectedBaseline.site_id == site_id)
            .order_by(TelemetryExpectedBaseline.created_at.desc())
            .all()
        )

    def get_active(
        self,
        site_id: int,
        baseline_type: TelemetryBaselineType = TelemetryBaselineType.weather_adjusted_model,
    ) -> Optional[TelemetryExpectedBaseline]:
        return (
            self.db_session.query(TelemetryExpectedBaseline)
            .filter(
                TelemetryExpectedBaseline.site_id == site_id,
                TelemetryExpectedBaseline.baseline_type == baseline_type,
                TelemetryExpectedBaseline.status == TelemetryBaselineStatus.active,
            )
            .one_or_none()
        )

    def get_active_for_sites(
        self,
        site_ids,
        baseline_type: TelemetryBaselineType = TelemetryBaselineType.weather_adjusted_model,
    ) -> dict[int, TelemetryExpectedBaseline]:
        """Active baselines for many sites in ONE query (no N+1).

        Returns ``{site_id: baseline}`` only for sites that have an active
        baseline of ``baseline_type``; sites without one are simply absent (so a
        caller can treat a missing site as "no live expected"). The active
        partial-unique index guarantees at most one active baseline per
        (site, type), so the mapping is unambiguous.
        """
        site_ids = list(site_ids)
        if not site_ids:
            return {}
        rows = (
            self.db_session.query(TelemetryExpectedBaseline)
            .filter(
                TelemetryExpectedBaseline.site_id.in_(site_ids),
                TelemetryExpectedBaseline.baseline_type == baseline_type,
                TelemetryExpectedBaseline.status == TelemetryBaselineStatus.active,
            )
            .all()
        )
        return {row.site_id: row for row in rows}

    # ------------------------------------------------------------------
    # Writes / lifecycle
    # ------------------------------------------------------------------
    def create_draft(
        self,
        *,
        company_id: int,
        site_id: int,
        payload: dict,
        site_additional: Optional[SiteAdditionalFieldList],
        site_timezone: Optional[str],
        created_by_user_id: Optional[int],
        version: Optional[int] = None,
    ) -> TelemetryExpectedBaseline:
        """Create a ``draft`` baseline, snapshotting site-derived assumptions.

        Loss %, PTO and timezone are copied from the site when the caller did not
        supply them; loss values are abs()-normalized to positive percent.
        ``version`` is set explicitly when provided (the project-facts bridge
        assigns ``max(version)+1`` for a new draft); otherwise the column default
        (1) applies. ``version`` is intentionally not part of ``_CREATE_FIELDS``.
        """
        data = {k: payload[k] for k in _CREATE_FIELDS if k in payload}
        if version is not None:
            data["version"] = version

        if site_additional is not None:
            if data.get("dc_loss_pct") is None:
                data["dc_loss_pct"] = _abs_or_none(site_additional.dc_wiring_loss)
            if data.get("ac_loss_pct") is None:
                data["ac_loss_pct"] = _abs_or_none(site_additional.ac_wiring_loss)
            if data.get("medium_voltage_loss_pct") is None:
                data["medium_voltage_loss_pct"] = _abs_or_none(
                    site_additional.medium_voltage_loss
                )
            if data.get("mv_line_loss_pct") is None:
                data["mv_line_loss_pct"] = _abs_or_none(site_additional.mv_line_loss)
            if data.get("pto_date") is None:
                data["pto_date"] = site_additional.permission_to_operate

        if data.get("timezone") is None:
            data["timezone"] = site_timezone

        baseline = TelemetryExpectedBaseline(
            company_id=company_id,
            site_id=site_id,
            status=TelemetryBaselineStatus.draft,
            created_by_user_id=created_by_user_id,
            **data,
        )
        self.db_session.add(baseline)
        self.db_session.commit()
        self.db_session.refresh(baseline)
        return baseline

    def approve(
        self, baseline: TelemetryExpectedBaseline, *, user_id: Optional[int]
    ) -> TelemetryExpectedBaseline:
        """Move a draft/in-review/rejected baseline to ``approved``."""
        if baseline.status not in (
            TelemetryBaselineStatus.draft,
            TelemetryBaselineStatus.in_review,
            TelemetryBaselineStatus.rejected,
        ):
            raise BaselineActivationError(
                f"Cannot approve a baseline in status '{baseline.status.value}'."
            )
        now = datetime.utcnow()
        if baseline.reviewed_at is None:
            baseline.reviewed_by = user_id
            baseline.reviewed_at = now
        baseline.approved_by = user_id
        baseline.approved_at = now
        baseline.status = TelemetryBaselineStatus.approved
        self.db_session.commit()
        self.db_session.refresh(baseline)
        return baseline

    def activate(
        self, baseline: TelemetryExpectedBaseline, *, user_id: Optional[int]
    ) -> TelemetryExpectedBaseline:
        """Activate an ``approved`` baseline, superseding the prior active one.

        Enforces the approval gate (only ``approved`` may activate) and performs
        the supersede + activate atomically with the prior active row locked.
        """
        if baseline.status != TelemetryBaselineStatus.approved:
            raise BaselineActivationError(
                "Only an approved baseline can be activated "
                f"(current status: '{baseline.status.value}')."
            )
        now = datetime.utcnow()
        prior = (
            self.db_session.query(TelemetryExpectedBaseline)
            .filter(
                TelemetryExpectedBaseline.site_id == baseline.site_id,
                TelemetryExpectedBaseline.baseline_type == baseline.baseline_type,
                TelemetryExpectedBaseline.status == TelemetryBaselineStatus.active,
            )
            .with_for_update()
            .one_or_none()
        )
        if prior is not None and prior.id != baseline.id:
            prior.status = TelemetryBaselineStatus.superseded
            prior.active_to = now
            baseline.supersedes_baseline_id = prior.id

        baseline.status = TelemetryBaselineStatus.active
        baseline.active_from = now
        baseline.active_to = None
        self.db_session.commit()
        self.db_session.refresh(baseline)
        return baseline
