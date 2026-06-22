"""WS.4 — read-only governed weather-semantics reconciliation (8-state taxonomy).

This service is the "reconciliation consumer" referenced by ``declaration_policy``.
For every weather-source-capable device on a site it resolves the device's current
governed declaration verdict (taxonomy states 1-5) and OVERLAYS the
source/profile-level states (6-8) when semantics are undeclared, producing a single
per-device headline state plus deduped site-level counts.

It is STRICTLY READ-ONLY. It performs no writes/commits, never infers or converts
semantics (declaring nothing leaves the value ``unknown``), never promotes or
activates anything, and never touches the WeatherResolver, the expected formula,
ingestion, rollups, the scheduler, baselines, ``expected_weather_provenance``, or
O&M. It only DISCLOSES what the governance layer already recorded.

The taxonomy (most-advanced-declaration-wins, then source overlay):
  1. ``source_exists_semantics_unknown``  (declaration axis — no governed value)
  2. ``declaration_draft``                (declaration axis — recorded, not active)
  3. ``declared_not_physics_usable``      (declaration axis — active, not usable)
  4. ``declared_eligible_integration_pending`` (declaration axis — eligible)
  5. ``declaration_stale_needs_re_review``     (declaration axis — flagged stale)
  6. ``weather_source_missing``           (source axis — no site weather source)
  7. ``weather_source_stale``             (source axis — source(s) but none active)
  8. ``source_coverage_incomplete``       (source axis — active but not in-effect now)

States 6-8 are surfaced ONLY when the declaration axis is at state 1 (semantics
undeclared) AND the source is not currently usable; a device that already has a
draft / active / eligible / stale declaration keeps its declaration state as the
headline (the deeper source gap is still reported via ``source_state``). Layer-1
blocking is only ever ``lowers_confidence`` / ``informational`` — this layer never
emits ``blocks_calculation``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.crud.weather import (
    WeatherDeviceMappingCRUD,
    WeatherSourceCRUD,
    WeatherSourceProfileCRUD,
)
from app.models.device import Device
from app.models.site import Site
from app.models.weather import WeatherSourceProfileStatus
from app.schema.weather import (
    WeatherSemanticsReconciliationResponse,
    WeatherSemanticsReconciliationRow,
)
from app.services.telemetry.device_classification import classify_device
from app.services.weather.declaration_policy import (
    BLOCKING_INFORMATIONAL,
    BLOCKING_LOWERS_CONFIDENCE,
    STATE_DECLARATION_DRAFT,
    STATE_DECLARATION_STALE_NEEDS_RE_REVIEW,
    STATE_DECLARED_ELIGIBLE_INTEGRATION_PENDING,
    STATE_DECLARED_NOT_PHYSICS_USABLE,
    STATE_SOURCE_EXISTS_SEMANTICS_UNKNOWN,
    evaluate_mapping,
)

# --- Source/profile-axis overlay states (taxonomy states 6-8) ---------------
STATE_WEATHER_SOURCE_MISSING = "weather_source_missing"
STATE_WEATHER_SOURCE_STALE = "weather_source_stale"
STATE_SOURCE_COVERAGE_INCOMPLETE = "source_coverage_incomplete"

# Internal sentinel: a usable, in-effect active source profile is present.
_SOURCE_PRESENT = "source_present"


def _naive_utcnow() -> datetime:
    """Current UTC instant as a naive datetime.

    Weather profile effective periods (and readings/rollups) are stored naive-UTC,
    so comparisons and the response ``generated_at`` use the same convention.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class _StateMeta:
    label: str
    explanation: str
    required_action: Optional[str]
    blocking_level: str


# Presentation metadata for every headline state. Declaration states 1-5 reuse the
# canonical declaration_policy constants so wording stays single-sourced; source
# states 6-8 are defined here. ``required_action=None`` for the eligible state (no
# action) and for ``declared_not_physics_usable`` (which prefers the verdict's own,
# more specific required_action).
_STATE_META: dict[str, _StateMeta] = {
    STATE_DECLARED_ELIGIBLE_INTEGRATION_PENDING: _StateMeta(
        label="Eligible — integration pending",
        explanation=(
            "Weather semantics are declared, active, and complete; the value is "
            "eligible for expected-model integration, which has not yet been applied."
        ),
        required_action=None,
        blocking_level=BLOCKING_INFORMATIONAL,
    ),
    STATE_DECLARATION_DRAFT: _StateMeta(
        label="Draft — not activated",
        explanation=(
            "A weather-semantics declaration exists but is still a draft; it is "
            "recorded only and is not in force until it is activated."
        ),
        required_action=(
            "Complete the required evidence and calibration, then activate the "
            "draft declaration."
        ),
        blocking_level=BLOCKING_LOWERS_CONFIDENCE,
    ),
    STATE_DECLARATION_STALE_NEEDS_RE_REVIEW: _StateMeta(
        label="Active — needs re-review",
        explanation=(
            "The active declaration is flagged as stale and needs re-review (its "
            "upstream identity changed, or it was manually flagged)."
        ),
        required_action=(
            "Re-declare and activate a new declaration to clear the stale flag."
        ),
        blocking_level=BLOCKING_LOWERS_CONFIDENCE,
    ),
    STATE_DECLARED_NOT_PHYSICS_USABLE: _StateMeta(
        label="Declared — not physics-usable",
        explanation=(
            "The active declaration is not usable by the expected physics today "
            "(e.g. not POA / not a cell-usable temperature, or it is missing a "
            "qualifying basis, sensor role, or calibration)."
        ),
        required_action=None,  # prefer the verdict's specific required_action
        blocking_level=BLOCKING_LOWERS_CONFIDENCE,
    ),
    STATE_SOURCE_EXISTS_SEMANTICS_UNKNOWN: _StateMeta(
        label="Source present — semantics undeclared",
        explanation=(
            "A usable weather source exists for this site, but this device's "
            "weather semantics have not been declared. Semantics are never inferred."
        ),
        required_action=(
            "Declare the weather semantics (e.g. POA plane / cell temperature) "
            "with qualifying evidence, then activate."
        ),
        blocking_level=BLOCKING_LOWERS_CONFIDENCE,
    ),
    STATE_WEATHER_SOURCE_MISSING: _StateMeta(
        label="No weather source",
        explanation=(
            "This site has no registered weather source, so there is nothing to "
            "declare against. Attach evidence and register a weather source — "
            "semantics are never inferred."
        ),
        required_action=(
            "Register a weather source for this site (attach source evidence) "
            "before declaring this device's semantics."
        ),
        blocking_level=BLOCKING_LOWERS_CONFIDENCE,
    ),
    STATE_WEATHER_SOURCE_STALE: _StateMeta(
        label="Weather source not active",
        explanation=(
            "A weather source exists for this site, but no source profile is "
            "active (every profile is draft, in review, rejected, or superseded)."
        ),
        required_action=(
            "Review and activate a weather source profile for this site."
        ),
        blocking_level=BLOCKING_LOWERS_CONFIDENCE,
    ),
    STATE_SOURCE_COVERAGE_INCOMPLETE: _StateMeta(
        label="Source coverage incomplete",
        explanation=(
            "An active weather source profile exists, but its effective period "
            "does not currently cover this site, leaving a coverage gap."
        ),
        required_action=(
            "Extend the active weather source profile's effective period to cover "
            "the required window."
        ),
        blocking_level=BLOCKING_LOWERS_CONFIDENCE,
    ),
}


def _enum_value(value: Any) -> Any:
    """Return ``value.value`` for enum-likes, else the value unchanged."""
    return getattr(value, "value", value)


def _profile_in_effect(profile: Any, now: Any) -> bool:
    """Whether a profile's (open-ended) effective window currently covers ``now``.

    NULL bounds are treated as open (no constraint). Pure comparison; no writes.
    """
    start = getattr(profile, "effective_from", None)
    end = getattr(profile, "effective_to", None)
    if start is not None and now < start:
        return False
    if end is not None and now >= end:
        return False
    return True


def _compute_source_axis(db: Session, site: Site) -> tuple[str, bool, bool]:
    """Resolve the site's source-axis state.

    Returns ``(source_state, has_weather_source, has_active_in_effect_profile)``,
    where ``source_state`` is one of ``weather_source_missing`` /
    ``weather_source_stale`` / ``source_coverage_incomplete`` / ``source_present``.

    Existence and activation are judged from the site's own weather sources and
    site-scoped profiles (the resolver selects active site profiles). A
    company/global weather source with no site profile is not "active for this
    site", so it is intentionally not counted as present here.
    """
    sources = WeatherSourceCRUD(db).list_for_site(site.id)
    profiles = WeatherSourceProfileCRUD(db).list_for_site(site.id)

    if not sources and not profiles:
        return STATE_WEATHER_SOURCE_MISSING, False, False

    active_profiles = [
        p
        for p in profiles
        if _enum_value(p.status) == WeatherSourceProfileStatus.active.value
    ]
    if not active_profiles:
        return STATE_WEATHER_SOURCE_STALE, True, False

    now = _naive_utcnow()
    if not any(_profile_in_effect(p, now) for p in active_profiles):
        return STATE_SOURCE_COVERAGE_INCOMPLETE, True, False

    return _SOURCE_PRESENT, True, True


def _build_row(
    device: Device, mapping: Any, *, source_state: str
) -> WeatherSemanticsReconciliationRow:
    """Build one read-only reconciliation row for a weather-capable device.

    The declaration verdict (states 1-5) is the headline UNLESS semantics are
    undeclared (state 1) AND the source is not currently usable, in which case the
    deeper source-axis state (6-8) becomes the headline. A device with any
    declared value (draft/active/eligible/stale) never has its state hidden by a
    source gap — the gap is still disclosed via ``source_state``.
    """
    verdict = evaluate_mapping(mapping)
    declaration_state = verdict.declaration_state

    if (
        declaration_state == STATE_SOURCE_EXISTS_SEMANTICS_UNKNOWN
        and source_state != _SOURCE_PRESENT
    ):
        headline = source_state
    else:
        headline = declaration_state

    meta = _STATE_META[headline]
    required_action = meta.required_action
    if headline == STATE_DECLARED_NOT_PHYSICS_USABLE:
        # Surface the verdict's specific next action (e.g. which field blocks).
        required_action = verdict.required_action or meta.required_action

    return WeatherSemanticsReconciliationRow(
        device_id=device.id,
        device_name=getattr(device, "name", None),
        device_category=_enum_value(getattr(device, "category", None)),
        metric=getattr(mapping, "metric", None) if mapping is not None else None,
        mapping_id=getattr(mapping, "id", None) if mapping is not None else None,
        reconciliation_state=headline,
        state_label=meta.label,
        state_explanation=meta.explanation,
        required_action=required_action,
        blocking_level=meta.blocking_level,
        declaration_state=declaration_state,
        source_state=source_state,
        declaration_status=(
            _enum_value(getattr(mapping, "declaration_status", None))
            if mapping is not None
            else None
        ),
        declaration_basis=(
            _enum_value(getattr(mapping, "declaration_basis", None))
            if mapping is not None
            else None
        ),
        needs_re_review=(
            bool(getattr(mapping, "needs_re_review", False))
            if mapping is not None
            else False
        ),
        re_review_reason=(
            getattr(mapping, "re_review_reason", None) if mapping is not None else None
        ),
        expected_model_eligible=verdict.expected_model_eligible,
        physics_usable_irradiance=verdict.physics_usable_irradiance,
        physics_usable_temperature=verdict.physics_usable_temperature,
        irradiance_plane=(
            _enum_value(getattr(mapping, "irradiance_plane", None))
            if mapping is not None
            else None
        ),
        temperature_type=(
            _enum_value(getattr(mapping, "temperature_type", None))
            if mapping is not None
            else None
        ),
        calibration_status=(
            _enum_value(getattr(mapping, "calibration_status", None))
            if mapping is not None
            else None
        ),
        layer1_message=verdict.layer1_message,
        eligibility_reason_codes=list(verdict.reason_codes),
    )


def build_site_semantics_reconciliation(
    db: Session, site: Site
) -> WeatherSemanticsReconciliationResponse:
    """Build the site-level governed weather-semantics reconciliation (read-only).

    Iterates every weather-source-capable device on the site, resolves its current
    governed declaration via ``get_current_for_device`` (prefers active), and maps
    it to a single headline taxonomy state. Performs zero writes/commits and never
    infers or converts semantics.
    """
    source_state, has_source, has_active_profile = _compute_source_axis(db, site)

    devices = (
        db.query(Device).filter(Device.site_id == site.id).order_by(Device.id).all()
    )
    weather_devices = [
        d for d in devices if classify_device(d).weather_source_capable
    ]

    mapping_crud = WeatherDeviceMappingCRUD(db)
    rows: list[WeatherSemanticsReconciliationRow] = []
    for device in weather_devices:
        mapping = mapping_crud.get_current_for_device(device.id)
        rows.append(_build_row(device, mapping, source_state=source_state))

    state_counts: dict[str, int] = {}
    blocking_counts: dict[str, int] = {}
    eligible_count = 0
    needs_re_review_count = 0
    for row in rows:
        state_counts[row.reconciliation_state] = (
            state_counts.get(row.reconciliation_state, 0) + 1
        )
        blocking_counts[row.blocking_level] = (
            blocking_counts.get(row.blocking_level, 0) + 1
        )
        if row.expected_model_eligible:
            eligible_count += 1
        if row.needs_re_review:
            needs_re_review_count += 1

    return WeatherSemanticsReconciliationResponse(
        site_id=site.id,
        generated_at=_naive_utcnow(),
        total_weather_capable_devices=len(rows),
        has_weather_source=has_source,
        has_active_weather_profile=has_active_profile,
        eligible_count=eligible_count,
        needs_re_review_count=needs_re_review_count,
        state_counts=state_counts,
        blocking_counts=blocking_counts,
        devices=rows,
    )
