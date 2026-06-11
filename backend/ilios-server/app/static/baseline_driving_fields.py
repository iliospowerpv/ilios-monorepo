"""Baseline-driving Due Diligence field designation (DD V2 Phase 1D).

This is the static set of Due Diligence document-key field names (display names,
matching ``DocumentKey.name`` and the canonical field ``display_name``) whose values
feed the energy-production baseline for a site. Overriding any of these fields is a
high-stakes action: a wrong value silently propagates into expected-production and
loss calculations. The Phase 1D guardrail therefore requires a non-empty
``override_notes`` rationale (reviewer identity is always known from auth) whenever
one of these fields is overridden.

The set is intentionally STATIC and conservative. It does NOT trigger, create, or
alter any baseline computation — it only gates the override workflow. It currently
mirrors the PVsyst system-sizing and monthly estimated-production keys
(``DueDiligenceBQKeys``), which are the inputs to the expected-production baseline.
"""
from app.static.due_diligence_bq_keys import DueDiligenceBQKeys

BASELINE_DRIVING_FIELD_NAMES: frozenset[str] = frozenset(DueDiligenceBQKeys.list())


def is_baseline_driving_field(field_name: str) -> bool:
    """Return True if overriding ``field_name`` requires a documented rationale."""
    return field_name in BASELINE_DRIVING_FIELD_NAMES
