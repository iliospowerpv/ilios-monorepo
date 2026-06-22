"""Append-only governance guard for ``weather_device_mappings`` (WS.1).

This module is the **single source of truth** for the database-level append-only
enforcement of governed weather-semantics declarations. It is deliberately
dependency-light: it imports nothing from ``app.models``, ``app.db.session``, or
``app.core.config`` so that the Alembic migration can import the canonical SQL
without dragging in the ORM/runtime, and the pytest harness (which builds the
schema with ``Base.metadata.create_all`` instead of running migrations) can apply
the very same trigger via a fixture.

Two layers of enforcement, kept in lockstep here:

1. **DB trigger** (authoritative backstop). A ``BEFORE UPDATE`` PL/pgSQL trigger
   scoped to *governed* rows (``OLD.declaration_status IS NOT NULL``). Legacy
   ungoverned rows (status NULL) are exempt and keep their historical behavior.
   INSERTs are never constrained. The trigger rejects any change to a protected
   semantic/provenance column, allows only the legal status transitions
   ``draft→active`` and ``active→superseded``, forbids clearing
   ``needs_re_review`` (true→false), and enforces set-once lifecycle columns.

2. **ORM guard** (defense in depth). :func:`assert_governed_update_allowed`
   mirrors the trigger logic on plain value dicts so application code fails fast.
   ``app/models/weather.py`` registers a ``before_update`` listener that builds the
   old/new dicts from attribute history and calls this function.

Nothing here converts weather semantics, touches the resolver/expected math, or
clears a blocking dependency. A semantic correction is always a NEW row plus an
explicit supersession — never an in-place edit.
"""
from __future__ import annotations

from typing import Any, Mapping

# --- Identifiers ------------------------------------------------------------
WEATHER_DECLARATION_GUARD_TABLE = "weather_device_mappings"
WEATHER_DECLARATION_GUARD_FUNCTION = "enforce_weather_declaration_append_only"
WEATHER_DECLARATION_GUARD_TRIGGER = "trg_enforce_weather_declaration_append_only"

# --- Lifecycle vocabulary (string values, kept in lockstep with the enums) --
STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_SUPERSEDED = "superseded"

# The only legal declaration_status transitions on a governed row.
LEGAL_STATUS_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        (STATUS_DRAFT, STATUS_ACTIVE),
        (STATUS_ACTIVE, STATUS_SUPERSEDED),
    }
)

# Bases that may ever qualify a declaration as production-grade eligible.
QUALIFYING_BASES: frozenset[str] = frozenset({"provider_confirmed", "source_document"})

# --- Protected (immutable) columns on a governed row ------------------------
# Any change to one of these (null-safe ``IS DISTINCT FROM``) is rejected. A
# semantic correction must be a new declaration + explicit supersession.
PROTECTED_COLUMNS: tuple[str, ...] = (
    "site_id",
    "irradiance_plane",
    "temperature_type",
    "calibration_status",
    "calibrated_at",
    "calibration_reference",
    "declaration_basis",
    "source_document_id",
    "source_file_id",
    "weather_source_id",
    "provider_key",
    "external_device_id",
    "device_id",
    "metric",
    "reviewer_note",
    "sensor_role",
    "sensor_model",
    "effective_from",
    "effective_to",
    "provider_metadata_json",
    "upstream_fingerprint_json",
    "declared_by",
    "declared_at",
    "supersedes_mapping_id",
    "created_at",
)

# Set-once lifecycle columns: once non-null they may never change.
SET_ONCE_COLUMNS: tuple[str, ...] = (
    "activated_by",
    "activated_at",
    "eligibility_snapshot_json",
    "superseded_by_mapping_id",
)

# Activation-only lifecycle columns: may be *initialized* (NULL -> value) ONLY in
# the same UPDATE that performs the draft->active transition. (Set-once above then
# freezes them.)
ACTIVATION_FIELDS: tuple[str, ...] = (
    "activated_by",
    "activated_at",
    "eligibility_snapshot_json",
)

# The supersession backlink may be *initialized* ONLY in the same UPDATE that
# performs the active->superseded transition, and is REQUIRED on that transition.
SUPERSEDE_BACKLINK_COLUMN = "superseded_by_mapping_id"


class WeatherDeclarationGuardError(Exception):
    """Raised by the ORM guard when an illegal in-place edit is attempted."""


def _v(value: Any) -> Any:
    """Normalize an enum/scalar to its comparable value (enum -> ``.value``)."""
    return getattr(value, "value", value)


def assert_governed_update_allowed(
    old: Mapping[str, Any], new: Mapping[str, Any]
) -> None:
    """Mirror of the DB trigger for ORM-level defense in depth.

    ``old``/``new`` are plain column-name -> value maps. Raises
    :class:`WeatherDeclarationGuardError` on any forbidden change. Legacy rows
    (``old.declaration_status`` is None/absent) are exempt, exactly like the
    trigger, so this never affects ungoverned mappings.
    """
    old_status = _v(old.get("declaration_status"))
    if old_status is None:
        return  # legacy/ungoverned row — not governed, exempt.

    new_status = _v(new.get("declaration_status"))
    transition = (old_status, new_status)
    activating = transition == (STATUS_DRAFT, STATUS_ACTIVE)
    superseding = transition == (STATUS_ACTIVE, STATUS_SUPERSEDED)

    # 1. Protected semantic/provenance columns are immutable.
    for col in PROTECTED_COLUMNS:
        if _v(old.get(col)) != _v(new.get(col)):
            raise WeatherDeclarationGuardError(
                f"weather_device_mappings governance: column '{col}' is immutable "
                "on a governed declaration; create a new declaration and supersede "
                "instead of editing it in place."
            )

    # 2. Only the legal declaration_status transitions are allowed.
    if new_status != old_status and transition not in LEGAL_STATUS_TRANSITIONS:
        raise WeatherDeclarationGuardError(
            "weather_device_mappings governance: illegal declaration_status "
            f"transition {old_status!r} -> {new_status!r}."
        )

    # 3. needs_re_review is monotonic (false->true only); never auto-cleared.
    old_flag = bool(old.get("needs_re_review"))
    new_flag = bool(new.get("needs_re_review"))
    if old_flag and not new_flag:
        raise WeatherDeclarationGuardError(
            "weather_device_mappings governance: needs_re_review cannot be cleared "
            "(true->false); supersede with a new activated declaration instead."
        )

    # 4. Set-once lifecycle columns cannot change once written.
    for col in SET_ONCE_COLUMNS:
        old_val = old.get(col)
        if old_val is not None and _v(old_val) != _v(new.get(col)):
            raise WeatherDeclarationGuardError(
                f"weather_device_mappings governance: column '{col}' is set-once and "
                "cannot change after it is first written."
            )

    # 5. Activation fields may be initialized ONLY while activating (draft->active).
    if not activating:
        for col in ACTIVATION_FIELDS:
            if old.get(col) is None and new.get(col) is not None:
                raise WeatherDeclarationGuardError(
                    f"weather_device_mappings governance: column '{col}' may only be "
                    "set as part of a draft->active activation."
                )

    # 6. Supersession backlink only while superseding; required on that transition.
    if (
        old.get(SUPERSEDE_BACKLINK_COLUMN) is None
        and new.get(SUPERSEDE_BACKLINK_COLUMN) is not None
        and not superseding
    ):
        raise WeatherDeclarationGuardError(
            "weather_device_mappings governance: superseded_by_mapping_id may only "
            "be set as part of an active->superseded supersession."
        )
    if superseding and new.get(SUPERSEDE_BACKLINK_COLUMN) is None:
        raise WeatherDeclarationGuardError(
            "weather_device_mappings governance: an active->superseded supersession "
            "must set superseded_by_mapping_id to the replacing declaration."
        )

    # 7. The stale flag (false->true) may only be raised on an active row.
    flagging_stale = (not old_flag) and new_flag
    if flagging_stale and not (
        old_status == STATUS_ACTIVE and new_status == STATUS_ACTIVE
    ):
        raise WeatherDeclarationGuardError(
            "weather_device_mappings governance: needs_re_review can only be raised "
            "on an active declaration."
        )

    # 8. re_review_reason may change ONLY in the same update that raises the flag.
    if _v(old.get("re_review_reason")) != _v(new.get("re_review_reason")) and not flagging_stale:
        raise WeatherDeclarationGuardError(
            "weather_device_mappings governance: re_review_reason may only be set "
            "while raising needs_re_review (false->true)."
        )


# ---------------------------------------------------------------------------
# Canonical SQL (imported verbatim by the migration AND the pytest fixture)
# ---------------------------------------------------------------------------
_PROTECTED_SQL_ARRAY = "ARRAY[" + ", ".join(f"'{c}'" for c in PROTECTED_COLUMNS) + "]"

CREATE_FUNCTION_SQL = f"""
CREATE OR REPLACE FUNCTION {WEATHER_DECLARATION_GUARD_FUNCTION}()
RETURNS TRIGGER AS $$
DECLARE
    protected_cols text[] := {_PROTECTED_SQL_ARRAY};
    col text;
    old_j jsonb := to_jsonb(OLD);
    new_j jsonb := to_jsonb(NEW);
BEGIN
    -- Legacy / ungoverned rows are exempt and keep their historical behavior.
    IF OLD.declaration_status IS NULL THEN
        RETURN NEW;
    END IF;

    -- 1. Protected semantic/provenance columns are immutable on a governed row.
    FOREACH col IN ARRAY protected_cols LOOP
        IF (old_j -> col) IS DISTINCT FROM (new_j -> col) THEN
            RAISE EXCEPTION 'weather_device_mappings governance: column % is immutable on a governed declaration (id=%); create a new declaration and supersede instead.', col, OLD.id;
        END IF;
    END LOOP;

    -- 2. Only the legal declaration_status transitions are allowed.
    IF NEW.declaration_status IS DISTINCT FROM OLD.declaration_status THEN
        IF NOT (
            (OLD.declaration_status = 'draft' AND NEW.declaration_status = 'active')
            OR (OLD.declaration_status = 'active' AND NEW.declaration_status = 'superseded')
        ) THEN
            RAISE EXCEPTION 'weather_device_mappings governance: illegal declaration_status transition % -> % (id=%).', OLD.declaration_status, NEW.declaration_status, OLD.id;
        END IF;
    END IF;

    -- 3. needs_re_review is monotonic (false->true only); never auto-cleared.
    IF COALESCE(OLD.needs_re_review, false) AND NOT COALESCE(NEW.needs_re_review, false) THEN
        RAISE EXCEPTION 'weather_device_mappings governance: needs_re_review cannot be cleared (id=%); supersede with a new activated declaration instead.', OLD.id;
    END IF;

    -- 4. Set-once lifecycle columns cannot change once written.
    IF OLD.activated_by IS NOT NULL AND NEW.activated_by IS DISTINCT FROM OLD.activated_by THEN
        RAISE EXCEPTION 'weather_device_mappings governance: activated_by is set-once (id=%).', OLD.id;
    END IF;
    IF OLD.activated_at IS NOT NULL AND NEW.activated_at IS DISTINCT FROM OLD.activated_at THEN
        RAISE EXCEPTION 'weather_device_mappings governance: activated_at is set-once (id=%).', OLD.id;
    END IF;
    IF OLD.eligibility_snapshot_json IS NOT NULL AND NEW.eligibility_snapshot_json IS DISTINCT FROM OLD.eligibility_snapshot_json THEN
        RAISE EXCEPTION 'weather_device_mappings governance: eligibility_snapshot_json is set-once (id=%).', OLD.id;
    END IF;
    IF OLD.superseded_by_mapping_id IS NOT NULL AND NEW.superseded_by_mapping_id IS DISTINCT FROM OLD.superseded_by_mapping_id THEN
        RAISE EXCEPTION 'weather_device_mappings governance: superseded_by_mapping_id is set-once (id=%).', OLD.id;
    END IF;

    -- 5. Activation fields may be initialized ONLY while activating (draft->active).
    IF NOT (OLD.declaration_status = 'draft' AND NEW.declaration_status = 'active') THEN
        IF (OLD.activated_by IS NULL AND NEW.activated_by IS NOT NULL)
           OR (OLD.activated_at IS NULL AND NEW.activated_at IS NOT NULL)
           OR (OLD.eligibility_snapshot_json IS NULL AND NEW.eligibility_snapshot_json IS NOT NULL) THEN
            RAISE EXCEPTION 'weather_device_mappings governance: activation fields (activated_by/activated_at/eligibility_snapshot_json) may only be set as part of a draft->active activation (id=%).', OLD.id;
        END IF;
    END IF;

    -- 6. Supersession backlink only while superseding; required on that transition.
    IF NOT (OLD.declaration_status = 'active' AND NEW.declaration_status = 'superseded') THEN
        IF OLD.superseded_by_mapping_id IS NULL AND NEW.superseded_by_mapping_id IS NOT NULL THEN
            RAISE EXCEPTION 'weather_device_mappings governance: superseded_by_mapping_id may only be set as part of an active->superseded supersession (id=%).', OLD.id;
        END IF;
    ELSE
        IF NEW.superseded_by_mapping_id IS NULL THEN
            RAISE EXCEPTION 'weather_device_mappings governance: an active->superseded supersession must set superseded_by_mapping_id (id=%).', OLD.id;
        END IF;
    END IF;

    -- 7. The stale flag (false->true) may only be raised on an active row.
    IF (NOT COALESCE(OLD.needs_re_review, false)) AND COALESCE(NEW.needs_re_review, false) THEN
        IF NOT (OLD.declaration_status = 'active' AND NEW.declaration_status = 'active') THEN
            RAISE EXCEPTION 'weather_device_mappings governance: needs_re_review can only be raised on an active declaration (id=%).', OLD.id;
        END IF;
    END IF;

    -- 8. re_review_reason may change ONLY in the same update that raises the flag.
    IF (old_j -> 're_review_reason') IS DISTINCT FROM (new_j -> 're_review_reason') THEN
        IF NOT ((NOT COALESCE(OLD.needs_re_review, false)) AND COALESCE(NEW.needs_re_review, false)) THEN
            RAISE EXCEPTION 'weather_device_mappings governance: re_review_reason may only be set while raising needs_re_review (false->true) (id=%).', OLD.id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""".strip()

DROP_TRIGGER_SQL = (
    f"DROP TRIGGER IF EXISTS {WEATHER_DECLARATION_GUARD_TRIGGER} "
    f"ON {WEATHER_DECLARATION_GUARD_TABLE};"
)

CREATE_TRIGGER_SQL = (
    f"CREATE TRIGGER {WEATHER_DECLARATION_GUARD_TRIGGER} "
    f"BEFORE UPDATE ON {WEATHER_DECLARATION_GUARD_TABLE} "
    f"FOR EACH ROW EXECUTE FUNCTION {WEATHER_DECLARATION_GUARD_FUNCTION}();"
)

DROP_FUNCTION_SQL = f"DROP FUNCTION IF EXISTS {WEATHER_DECLARATION_GUARD_FUNCTION}();"

# Ordered statements to (re)install the guard on an existing schema — used by the
# migration's upgrade() and by the pytest fixture after create_all().
APPLY_GUARD_SQL: tuple[str, ...] = (
    DROP_TRIGGER_SQL,
    CREATE_FUNCTION_SQL,
    CREATE_TRIGGER_SQL,
)

# Ordered statements to remove the guard — used by the migration's downgrade().
REMOVE_GUARD_SQL: tuple[str, ...] = (
    DROP_TRIGGER_SQL,
    DROP_FUNCTION_SQL,
)
