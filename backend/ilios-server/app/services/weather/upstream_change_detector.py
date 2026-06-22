"""WS.3 — upstream-change / stale re-review detector (additive, Layer-1).

Compares each ACTIVE governed weather declaration's stored upstream fingerprint
(captured ONCE at draft creation) to the device's CURRENT upstream identity and
reports divergence. Two entry points:

* :func:`detect_site` — strictly READ-ONLY. Recomputes current fingerprints and
  returns per-mapping divergence for display surfaces (eligibility diagnostics,
  reconciliation, an admin "preview"). It performs NO writes and NO commits.
* :func:`apply_re_review` — the ONLY write path. For an explicit admin
  re-evaluation, it raises the monotonic ``needs_re_review`` flag (+
  ``re_review_reason`` + a ``needs_re_review`` ledger entry) on active declarations
  whose upstream diverged and that are not already flagged. It commits once.

Boundary (Layer-1): the detector may write ONLY ``needs_re_review`` /
``re_review_reason`` and the immutable ledger. It NEVER creates, activates,
supersedes, or clears a declaration; NEVER edits weather semantics; and NEVER
touches the resolver/expected math, ingestion, rollups, the scheduler, baselines,
``expected_weather_provenance``, or O&M. ``needs_re_review`` is monotonic — it is
raised false->true only and is cleared solely by a new activated supersession
(WS.2). The two flag-writing columns are exactly the ones the WS.1 append-only
guard permits to change on an active row (guard rules 7 + 8), so every write here
satisfies the guard.

Unlike the manual single-row :func:`mark_needs_re_review` (which is fail-closed
409 on an already-flagged row), the batch :func:`apply_re_review` SKIPS
already-flagged rows silently so an operator can safely re-run it (idempotent).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.weather import (
    WeatherApprovalAction,
    WeatherDeclarationStatus,
    WeatherDeviceMapping,
)
from app.services.weather.declaration_service import _now, _record_ledger  # noqa: F401
from app.services.weather.upstream_fingerprint import (
    compare_fingerprint,
    compute_upstream_fingerprint,
)


@dataclass
class MappingDivergence:
    """Per-declaration divergence verdict (read-only description)."""

    mapping_id: int
    device_id: Optional[int]
    metric: Optional[str]
    needs_re_review: bool
    has_stored_fingerprint: bool
    diverged: bool
    changed_keys: list[str]
    summary: Optional[str]
    would_flag: bool
    flagged: bool = False


@dataclass
class SiteReEvaluationReport:
    """Site-level rollup of the divergence scan / re-evaluation."""

    site_id: int
    applied: bool
    total_active: int
    diverged_count: int
    would_flag_count: int
    already_flagged_count: int
    newly_flagged_count: int
    mappings: list[MappingDivergence] = field(default_factory=list)


def _active_mappings(
    db: Session, site_id: int, *, lock: bool
) -> list[WeatherDeviceMapping]:
    """All ACTIVE governed declarations for a site (optionally ``FOR UPDATE``)."""
    query = (
        db.query(WeatherDeviceMapping)
        .filter(
            WeatherDeviceMapping.site_id == site_id,
            WeatherDeviceMapping.declaration_status
            == WeatherDeclarationStatus.active,
        )
        .order_by(WeatherDeviceMapping.id)
    )
    if lock:
        query = query.with_for_update()
    return query.all()


def _device_for(db: Session, mapping: WeatherDeviceMapping) -> Optional[Device]:
    """The mapped device, or ``None`` for an external-only declaration."""
    if mapping.device_id is None:
        return None
    return db.query(Device).filter(Device.id == mapping.device_id).one_or_none()


def _evaluate(db: Session, mapping: WeatherDeviceMapping) -> dict[str, Any]:
    """Compare ``mapping``'s stored fingerprint to the device's live identity."""
    device = _device_for(db, mapping)
    current = compute_upstream_fingerprint(device, mapping)
    return compare_fingerprint(mapping.upstream_fingerprint_json, current)


def _to_divergence(
    mapping: WeatherDeviceMapping,
    result: dict[str, Any],
    *,
    already_flagged: bool,
    flagged: bool,
) -> MappingDivergence:
    """Build a divergence row from explicit PRE-run state.

    ``already_flagged`` is the flag state BEFORE this run (so ``would_flag`` is
    stable even after the apply path mutates the row); the reported
    ``needs_re_review`` is the FINAL state (``already_flagged`` or newly
    ``flagged``).
    """
    diverged = bool(result["diverged"])
    return MappingDivergence(
        mapping_id=mapping.id,
        device_id=mapping.device_id,
        metric=mapping.metric,
        needs_re_review=already_flagged or flagged,
        has_stored_fingerprint=bool(mapping.upstream_fingerprint_json),
        diverged=diverged,
        changed_keys=list(result["changed_keys"]),
        summary=result["summary"],
        would_flag=diverged and not already_flagged,
        flagged=flagged,
    )


def detect_site(db: Session, *, site: Any) -> SiteReEvaluationReport:
    """Read-only divergence scan over a site's ACTIVE declarations.

    Computes each active declaration's current fingerprint and compares it to the
    stored one. Writes NOTHING — no flag, no reason, no ledger. ``would_flag`` marks
    a row a subsequent :func:`apply_re_review` WOULD flag (diverged and not already
    flagged). Use this for previews / display surfaces.
    """
    mappings = _active_mappings(db, site.id, lock=False)
    rows: list[MappingDivergence] = []
    diverged_count = 0
    would_flag_count = 0
    already_flagged_count = 0

    for mapping in mappings:
        result = _evaluate(db, mapping)
        already = bool(mapping.needs_re_review)
        row = _to_divergence(
            mapping, result, already_flagged=already, flagged=False
        )
        rows.append(row)
        if row.diverged:
            diverged_count += 1
        if already:
            already_flagged_count += 1
        if row.would_flag:
            would_flag_count += 1

    return SiteReEvaluationReport(
        site_id=site.id,
        applied=False,
        total_active=len(mappings),
        diverged_count=diverged_count,
        would_flag_count=would_flag_count,
        already_flagged_count=already_flagged_count,
        newly_flagged_count=0,
        mappings=rows,
    )


def apply_re_review(
    db: Session, *, site: Any, actor_id: Optional[int]
) -> SiteReEvaluationReport:
    """Flag diverged, unflagged ACTIVE declarations as needing re-review (one commit).

    Locks the site's active declarations ``FOR UPDATE``, then for each that diverged
    and is NOT already flagged: raises ``needs_re_review`` false->true, records the
    upstream-change summary in ``re_review_reason``, and appends a ``needs_re_review``
    ledger entry. Already-flagged rows are SKIPPED (idempotent — not an error, unlike
    the manual single-row path). Never clears a flag, never edits semantics, never
    touches expected/baseline/provenance. Commits exactly once at the end so all the
    flag writes + ledger entries are atomic.
    """
    mappings = _active_mappings(db, site.id, lock=True)
    rows: list[MappingDivergence] = []
    diverged_count = 0
    would_flag_count = 0
    already_flagged_count = 0
    newly_flagged_count = 0

    for mapping in mappings:
        result = _evaluate(db, mapping)
        already = bool(mapping.needs_re_review)
        diverged = bool(result["diverged"])

        if diverged:
            diverged_count += 1
        if already:
            already_flagged_count += 1

        will_flag = diverged and not already
        if will_flag:
            would_flag_count += 1
            # Raise the monotonic flag. Guard rules 7/8 allow exactly this shape on
            # an active row: needs_re_review false->true with re_review_reason set in
            # the SAME update. This is the ONLY mutation the detector performs.
            mapping.needs_re_review = True
            mapping.re_review_reason = result["summary"]
            db.flush()  # emit the UPDATE so the append-only guard validates its shape
            _record_ledger(
                db,
                site_id=site.id,
                target_id=mapping.id,
                action=WeatherApprovalAction.needs_re_review,
                actor_id=actor_id,
                rationale=result["summary"],
            )
            newly_flagged_count += 1

        rows.append(
            _to_divergence(
                mapping, result, already_flagged=already, flagged=will_flag
            )
        )

    db.commit()
    return SiteReEvaluationReport(
        site_id=site.id,
        applied=True,
        total_active=len(mappings),
        diverged_count=diverged_count,
        would_flag_count=would_flag_count,
        already_flagged_count=already_flagged_count,
        newly_flagged_count=newly_flagged_count,
        mappings=rows,
    )
