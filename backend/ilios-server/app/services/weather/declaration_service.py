"""WS.2 — governed weather-semantics declaration lifecycle service.

This is the single transactional owner of the ``draft -> active -> superseded``
lifecycle for ``weather_device_mappings``. It sits ON TOP of the WS.1 append-only
guards (the DB trigger + ORM listener in ``app.db.weather_declaration_guard``):
the guard enforces the *shape* of any UPDATE (which columns may change), while
this service enforces the *governance policy* (basis evidence completeness,
cross-tenant evidence resolvability, single-active per device/metric, and
explicit supersession) and writes the immutable ``weather_source_approvals``
ledger.

Layer-1 only. This module:

* NEVER converts weather semantics (defaults stay ``unknown``; nothing is
  inferred from device name/category/metric).
* NEVER writes ``expected_weather_provenance``, touches the WeatherResolver math,
  the expected formula, ingestion, rollups, the scheduler, device
  eligibility/classification, baselines, or O&M actuals.
* Performs a *semantic correction* only as a NEW row plus an explicit
  supersession — never an in-place edit of a governed row.

Transaction discipline: every public operation commits exactly once at the end.
The private ledger helper only ``add``/``flush`` (it never commits) so a failure
anywhere in a multi-step operation rolls the whole thing back when the session is
closed — activation + supersession + ledger are therefore atomic.

Important separation of concerns — *activation* vs *eligibility*:

* **Activation** records a coherent governed declaration. It validates the
  evidence appropriate to the declared basis and the supersession lineage. A
  ``reviewer_assumption``/``reviewer_source_note`` declaration, or a POA
  declaration that is not yet calibrated, MAY be activated — it simply becomes an
  active governed record.
* **Eligibility** (``expected_model_eligible``) is a *derived disclosure*
  computed by the pure policy (basis + physics-usability + calibration + sensor
  role + coverage). It is captured as an audit snapshot at activation and always
  recomputed live on read; it is never an activation gate. This is why a
  recorded-only declaration can be active but never eligible.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.file import File
from app.models.weather import (
    WeatherApprovalAction,
    WeatherApprovalTargetType,
    WeatherDeclarationBasis,
    WeatherDeclarationStatus,
    WeatherDeviceMapping,
    WeatherSourceApproval,
)
from app.services.weather.declaration_policy import evaluate_mapping
from app.services.weather.upstream_fingerprint import compute_upstream_fingerprint


class DeclarationServiceError(Exception):
    """A governance/validation failure the router maps to an HTTP error.

    ``status_code`` carries the intended HTTP status (422 for malformed/incomplete
    declarations, 409 for illegal lifecycle transitions / single-active conflicts,
    404 for a missing declaration) and ``detail`` the user-facing message.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _v(value: Any) -> Any:
    """Normalize an enum/scalar to its comparable ``.value`` (None stays None)."""
    return getattr(value, "value", value)


def _now() -> datetime:
    """Current instant in the naive-UTC convention used across the weather domain."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# The two WS.2 partial unique indexes (see migration ff37) that enforce the
# single-active-per-lineage invariant at the DB level. We map ONLY a violation of
# one of these to a 409 race; any other IntegrityError must propagate unmasked.
_SINGLE_ACTIVE_CONSTRAINTS = frozenset(
    {
        "uq_weather_device_mappings_active_device",
        "uq_weather_device_mappings_active_external",
    }
)


def _is_single_active_violation(exc: IntegrityError) -> bool:
    """True only when ``exc`` is the single-active partial unique index rejecting a
    concurrent activation winner — not an unrelated FK/NOT NULL/other constraint.

    psycopg2 exposes the violated constraint via ``exc.orig.diag.constraint_name``;
    matching it against the two WS.2 indexes keeps genuinely unrelated integrity
    errors from being mislabeled as a "concurrent activation" 409 (they re-raise).
    """
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None) in _SINGLE_ACTIVE_CONSTRAINTS


# ---------------------------------------------------------------------------
# Immutable ledger (non-committing — caller owns the transaction boundary)
# ---------------------------------------------------------------------------
def _record_ledger(
    db: Session,
    *,
    site_id: int,
    target_id: int,
    action: WeatherApprovalAction,
    actor_id: Optional[int],
    rationale: Optional[str] = None,
) -> WeatherSourceApproval:
    """Append a ``weather_source_approvals`` row WITHOUT committing.

    Unlike ``WeatherSourceApprovalCRUD.record`` (which commits), this only
    ``add``/``flush`` so a public lifecycle op can write several ledger entries
    plus the mapping changes and commit them together atomically.
    """
    entry = WeatherSourceApproval(
        site_id=site_id,
        target_type=WeatherApprovalTargetType.weather_device_mapping,
        target_id=target_id,
        action=action,
        approved_by=actor_id,
        approved_at=_now(),
        rationale=rationale,
    )
    db.add(entry)
    db.flush()
    return entry


# ---------------------------------------------------------------------------
# Cross-tenant evidence resolvability (fail closed)
# ---------------------------------------------------------------------------
def _validate_evidence_in_tenant(
    db: Session,
    *,
    site_id: int,
    source_document_id: Optional[int],
    source_file_id: Optional[int],
) -> None:
    """Reject evidence that does not resolve within the declaration's own site.

    A site-A admin must never be able to attach a site-B document/file as
    evidence. Documents are scoped by ``documents.site_id``; files scope through
    ``files.document_id -> documents.site_id``. Fails closed (any unresolved or
    out-of-tenant reference raises).
    """
    if source_document_id is not None:
        doc = (
            db.query(Document)
            .filter(Document.id == source_document_id)
            .one_or_none()
        )
        if doc is None or doc.site_id != site_id:
            raise DeclarationServiceError(
                422,
                f"source_document_id {source_document_id} was not found in this "
                "project/site; evidence must belong to the same project.",
            )
    if source_file_id is not None:
        file_row = db.query(File).filter(File.id == source_file_id).one_or_none()
        if file_row is None:
            raise DeclarationServiceError(
                422, f"source_file_id {source_file_id} was not found."
            )
        doc = (
            db.query(Document)
            .filter(Document.id == file_row.document_id)
            .one_or_none()
        )
        if doc is None or doc.site_id != site_id:
            raise DeclarationServiceError(
                422,
                f"source_file_id {source_file_id} is not accessible from this "
                "project/site; evidence must belong to the same project.",
            )


# ---------------------------------------------------------------------------
# Basis-specific completeness
# ---------------------------------------------------------------------------
def _validate_create_friction(payload: Any) -> None:
    """Create-time, basis-shape friction (only the lowest-confidence basis).

    The ``reviewer_assumption`` basis needs an explicit confirmation flag plus a
    non-empty note before a draft can even be recorded — friction proportional to
    its low confidence. The confirmation flag is transient (request-only), so it
    is enforced here at create rather than at activation. All other completeness
    is deferred to activation per the lifecycle matrix ("basis-shape only" on
    create, "full completeness" on activate).
    """
    basis = _v(payload.declaration_basis)
    if basis == WeatherDeclarationBasis.reviewer_assumption.value:
        if not getattr(payload, "assumption_confirmed", False):
            raise DeclarationServiceError(
                422,
                "A reviewer_assumption declaration requires explicit confirmation "
                "(assumption_confirmed=true) — assumptions are recorded-only and "
                "must be acknowledged.",
            )
        note = getattr(payload, "reviewer_note", None)
        if not (note and str(note).strip()):
            raise DeclarationServiceError(
                422,
                "A reviewer_assumption declaration requires a reviewer_note "
                "explaining the assumption.",
            )


def _validate_activation_completeness(mapping: WeatherDeviceMapping) -> None:
    """Full governance completeness for the declared basis, checked at activation.

    This validates that the declaration carries the EVIDENCE appropriate to its
    basis — not that it is ``expected_model_eligible``. Eligibility (POA plane /
    cell temperature / calibration / sensor role) is a derived disclosure and is
    intentionally NOT an activation gate, so recorded-only and not-yet-calibrated
    declarations can still become active governed records.
    """
    basis = _v(mapping.declaration_basis)
    if basis is None:
        raise DeclarationServiceError(
            422, "A governed declaration must have a declaration_basis."
        )

    has_document = (
        mapping.source_document_id is not None or mapping.source_file_id is not None
    )
    has_note = bool(mapping.reviewer_note and str(mapping.reviewer_note).strip())
    has_provider_metadata = bool(mapping.provider_metadata_json)

    if basis == WeatherDeclarationBasis.source_document.value:
        if not has_document:
            raise DeclarationServiceError(
                422,
                "A source_document declaration must have an attached "
                "source_document_id or source_file_id before activation.",
            )
    elif basis == WeatherDeclarationBasis.provider_confirmed.value:
        if not (has_provider_metadata or has_document):
            raise DeclarationServiceError(
                422,
                "A provider_confirmed declaration must carry provider metadata or "
                "an attached source document/file before activation.",
            )
    elif basis == WeatherDeclarationBasis.reviewer_source_note.value:
        if not has_note:
            raise DeclarationServiceError(
                422,
                "A reviewer_source_note declaration must have a reviewer_note "
                "before activation.",
            )
    elif basis == WeatherDeclarationBasis.reviewer_assumption.value:
        if not has_note:
            raise DeclarationServiceError(
                422,
                "A reviewer_assumption declaration must have a reviewer_note "
                "before activation.",
            )


# ---------------------------------------------------------------------------
# Lineage helpers
# ---------------------------------------------------------------------------
def _lineage_query(db: Session, mapping: WeatherDeviceMapping):
    """Query scoped to the same (site, device-or-external-device, metric) lineage.

    Single-active and supersession are evaluated per lineage. When ``device_id``
    is NULL the mapping is keyed by ``external_device_id`` instead (NULL never
    equals NULL in SQL, so the device-id path would silently match nothing).
    """
    query = db.query(WeatherDeviceMapping).filter(
        WeatherDeviceMapping.site_id == mapping.site_id,
        WeatherDeviceMapping.metric == mapping.metric,
    )
    if mapping.device_id is not None:
        query = query.filter(WeatherDeviceMapping.device_id == mapping.device_id)
    else:
        query = query.filter(
            WeatherDeviceMapping.device_id.is_(None),
            WeatherDeviceMapping.external_device_id == mapping.external_device_id,
        )
    return query


def _activate_locked(
    db: Session,
    *,
    site_id: int,
    mapping: WeatherDeviceMapping,
    actor_id: Optional[int],
    rationale: Optional[str],
) -> None:
    """Activate ``mapping`` (draft -> active), atomically superseding the prior.

    Caller MUST already own ``mapping`` (freshly created in this transaction) or
    have loaded it ``FOR UPDATE``. This routine locks every currently-active row
    in the same lineage, enforces single-active + explicit supersession, flips the
    draft to active (set-once activation fields + eligibility snapshot), supersedes
    the prior row with a back-link, and appends the ledger events. It does NOT
    commit — the public caller owns the commit so the whole sequence is atomic.
    """
    if _v(mapping.declaration_status) != WeatherDeclarationStatus.draft.value:
        raise DeclarationServiceError(
            409,
            "Only a draft declaration can be activated (current status: "
            f"{_v(mapping.declaration_status) or 'ungoverned'}).",
        )

    # Re-validate evidence resolvability at activation, not only at create. A draft
    # recorded earlier may reference a document/file that has since been re-parented
    # to another site or removed; activation must fail closed exactly as create did
    # rather than promote a now-out-of-tenant evidence reference to active.
    _validate_evidence_in_tenant(
        db,
        site_id=site_id,
        source_document_id=mapping.source_document_id,
        source_file_id=mapping.source_file_id,
    )

    _validate_activation_completeness(mapping)

    # Lock every currently-active row in this lineage: this both enforces
    # single-active and serializes concurrent activations of the same device/metric.
    active_rows = (
        _lineage_query(db, mapping)
        .filter(
            WeatherDeviceMapping.declaration_status
            == WeatherDeclarationStatus.active,
            WeatherDeviceMapping.id != mapping.id,
        )
        .with_for_update()
        .all()
    )

    prior: Optional[WeatherDeviceMapping] = None
    if mapping.supersedes_mapping_id is not None:
        prior = next(
            (r for r in active_rows if r.id == mapping.supersedes_mapping_id), None
        )
        if prior is None:
            # The target does not exist, is not active, or is a different lineage.
            raise DeclarationServiceError(
                409,
                "supersedes_mapping_id must reference the current ACTIVE "
                "declaration for this device and metric.",
            )

    uncovered = [r for r in active_rows if prior is None or r.id != prior.id]
    if uncovered:
        raise DeclarationServiceError(
            409,
            "An active declaration already exists for this device/metric; pass "
            "supersedes_mapping_id to supersede it as part of this activation.",
        )

    now = _now()

    # Supersede the prior ACTIVE row FIRST so the lineage never holds two active
    # rows at any flush point. The WS.2 single-active partial unique index is a
    # non-deferrable partial index checked per-statement; flipping the draft to
    # active while the prior was still active would trip it. The per-row append-only
    # guard is order-independent, so superseding before activating is equally valid.
    if prior is not None:
        prior.declaration_status = WeatherDeclarationStatus.superseded
        prior.superseded_by_mapping_id = mapping.id
        db.flush()  # emit the active->superseded UPDATE (guard validates the shape)
        _record_ledger(
            db,
            site_id=site_id,
            target_id=prior.id,
            action=WeatherApprovalAction.supersede,
            actor_id=actor_id,
            rationale=(rationale or f"Superseded by declaration {mapping.id}."),
        )

    mapping.declaration_status = WeatherDeclarationStatus.active
    mapping.activated_by = actor_id
    mapping.activated_at = now
    # Audit-only snapshot of the verdict at activation; the live verdict is always
    # recomputed on read. Computed AFTER setting status=active so it reflects the
    # active row (coverage is a consumer concern, left unevaluated here).
    mapping.eligibility_snapshot_json = evaluate_mapping(mapping).to_dict()
    db.flush()  # emit the draft->active UPDATE (guard validates the shape)

    _record_ledger(
        db,
        site_id=site_id,
        target_id=mapping.id,
        action=WeatherApprovalAction.activate,
        actor_id=actor_id,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Public lifecycle operations
# ---------------------------------------------------------------------------
def create_declaration(
    db: Session,
    *,
    site: Any,
    device: Any,
    payload: Any,
    actor_id: Optional[int],
) -> WeatherDeviceMapping:
    """Create a governed declaration as a NEW draft row (never auto-active).

    Always INSERTs a fresh row with ``declaration_status = draft`` — a legacy
    NULL-status row is never mutated into a governed one. Records the
    ``declare_draft`` ledger event. When ``payload.activate`` is true the draft is
    created AND activated in the same transaction (create + activate atomic).
    """
    _validate_create_friction(payload)
    _validate_evidence_in_tenant(
        db,
        site_id=site.id,
        source_document_id=payload.source_document_id,
        source_file_id=payload.source_file_id,
    )

    mapping = WeatherDeviceMapping(
        site_id=site.id,
        device_id=device.id if device is not None else None,
        external_device_id=payload.external_device_id,
        weather_source_id=payload.weather_source_id,
        metric=payload.metric,
        provider_key=payload.provider_key,
        irradiance_plane=payload.irradiance_plane,
        temperature_type=payload.temperature_type,
        calibration_status=payload.calibration_status,
        calibrated_at=payload.calibrated_at,
        calibration_reference=payload.calibration_reference,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        declaration_basis=payload.declaration_basis,
        declaration_status=WeatherDeclarationStatus.draft,
        declared_by=actor_id,
        declared_at=_now(),
        source_document_id=payload.source_document_id,
        source_file_id=payload.source_file_id,
        reviewer_note=payload.reviewer_note,
        sensor_role=payload.sensor_role,
        sensor_model=payload.sensor_model,
        provider_metadata_json=payload.provider_metadata_json,
        supersedes_mapping_id=payload.supersedes_mapping_id,
        needs_re_review=False,
    )
    # WS.3: snapshot the UPSTREAM IDENTITY this declaration is authored against,
    # ONCE, at draft creation. ``upstream_fingerprint_json`` is a guard-protected
    # (immutable) column on a governed row, so it can NEVER be re-captured on a
    # later UPDATE — the draft snapshot is the permanent provenance baseline and
    # carries forward unchanged when the draft is activated. The WS.3 detector
    # later compares this baseline to the device's live identity to decide whether
    # the declaration has gone stale (needs_re_review). Pure: no inference, no math.
    mapping.upstream_fingerprint_json = compute_upstream_fingerprint(device, mapping)
    db.add(mapping)
    db.flush()  # assign mapping.id before the ledger entry references it

    _record_ledger(
        db,
        site_id=site.id,
        target_id=mapping.id,
        action=WeatherApprovalAction.declare_draft,
        actor_id=actor_id,
        rationale=payload.reviewer_note,
    )

    activate = bool(getattr(payload, "activate", False))
    try:
        if activate:
            _activate_locked(
                db,
                site_id=site.id,
                mapping=mapping,
                actor_id=actor_id,
                rationale=None,
            )
        db.commit()
    except IntegrityError as exc:
        # Fail closed as a 409 ONLY when the single-active partial unique index
        # rejected a concurrent activation winner (another txn activated this
        # lineage between our uncovered-rows check and our flush). Any other
        # IntegrityError — or any IntegrityError on a draft-only insert, which has
        # no single-active surface — is a different fault and must propagate unmasked.
        db.rollback()
        if activate and _is_single_active_violation(exc):
            raise DeclarationServiceError(
                409,
                "An active declaration already exists for this device/metric "
                "(a concurrent activation won the race); reload and supersede the "
                "current active declaration instead.",
            )
        raise
    db.refresh(mapping)
    return mapping


def activate_declaration(
    db: Session,
    *,
    site: Any,
    mapping_id: int,
    actor_id: Optional[int],
    rationale: Optional[str] = None,
) -> WeatherDeviceMapping:
    """Activate an existing draft declaration (full validation + atomic supersede)."""
    mapping = (
        db.query(WeatherDeviceMapping)
        .filter(
            WeatherDeviceMapping.id == mapping_id,
            WeatherDeviceMapping.site_id == site.id,
        )
        .with_for_update()
        .one_or_none()
    )
    if mapping is None:
        raise DeclarationServiceError(
            404,
            f"Weather declaration {mapping_id} was not found on this project/site.",
        )

    try:
        _activate_locked(
            db,
            site_id=site.id,
            mapping=mapping,
            actor_id=actor_id,
            rationale=rationale,
        )
        db.commit()
    except IntegrityError as exc:
        # Translate ONLY the single-active partial unique index violation (a
        # concurrent activation winning the race) to a 409; re-raise any other
        # integrity fault unmasked rather than mislabeling it a race.
        db.rollback()
        if _is_single_active_violation(exc):
            raise DeclarationServiceError(
                409,
                "An active declaration already exists for this device/metric "
                "(a concurrent activation won the race); reload and supersede the "
                "current active declaration instead.",
            )
        raise
    db.refresh(mapping)
    return mapping


def mark_needs_re_review(
    db: Session,
    *,
    site: Any,
    mapping_id: int,
    actor_id: Optional[int],
    reason: str,
) -> WeatherDeviceMapping:
    """Manually flag an ACTIVE declaration as needing re-review (monotonic).

    Sets ``needs_re_review`` false->true plus ``re_review_reason`` and records the
    ``needs_re_review`` ledger event. Never auto-clears — the flag clears only when
    a new activated declaration supersedes this one. Idempotency is fail-closed: a
    re-flag of an already-flagged row is rejected rather than silently re-stamped.
    """
    cleaned_reason = (reason or "").strip()
    if not cleaned_reason:
        raise DeclarationServiceError(422, "A re-review reason is required.")

    mapping = (
        db.query(WeatherDeviceMapping)
        .filter(
            WeatherDeviceMapping.id == mapping_id,
            WeatherDeviceMapping.site_id == site.id,
        )
        .with_for_update()
        .one_or_none()
    )
    if mapping is None:
        raise DeclarationServiceError(
            404,
            f"Weather declaration {mapping_id} was not found on this project/site.",
        )

    if _v(mapping.declaration_status) != WeatherDeclarationStatus.active.value:
        raise DeclarationServiceError(
            409,
            "needs_re_review can only be raised on an ACTIVE declaration.",
        )
    if bool(mapping.needs_re_review):
        raise DeclarationServiceError(
            409, "This declaration is already flagged for re-review."
        )

    mapping.needs_re_review = True
    mapping.re_review_reason = cleaned_reason
    db.flush()  # emit the active->active flag-stale UPDATE (guard validates shape)

    _record_ledger(
        db,
        site_id=site.id,
        target_id=mapping.id,
        action=WeatherApprovalAction.needs_re_review,
        actor_id=actor_id,
        rationale=cleaned_reason,
    )
    db.commit()
    db.refresh(mapping)
    return mapping
