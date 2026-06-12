"""Shared override-guardrail logic for Due Diligence baseline-driving fields (DD V2 Phase 1.6).

Centralizes the value-divergence decision used by BOTH the single-key ``set_key`` endpoint and
the ``bulk_accept_ai_values`` endpoint so the audit-integrity rule lives in exactly one place: a
baseline-driving field whose submitted value diverges from its AI-extracted original may only be
saved as an ``overridden`` value accompanied by a reviewer rationale.

This module performs NO database access and NO baseline computation. It only classifies an already
submitted value against an already-resolved AI original (or, as a fail-safe, the previously stored
value). Resolving the AI original lives in ``ProjectFactsService``; persisting the resulting
decision lives in the routers.
"""

from dataclasses import dataclass


def normalize_term(value) -> str:
    """Normalize a term value for divergence comparison.

    Coerces to a trimmed string so ``None``, numeric, and whitespace-padded forms of the same
    value compare equal. Strict otherwise: ``"100"`` vs ``"100.0"`` reads as a divergence, so the
    guardrail fails CLOSED (asks for a rationale) rather than silently accepting. Never mutates the
    stored value.
    """
    if value is None:
        return ""
    return str(value).strip()


@dataclass(frozen=True)
class OverrideEvaluation:
    """Outcome of evaluating a baseline-driving submission against its AI original."""

    diverges: bool
    effective_status: str        # "accepted" or "overridden"
    requires_rationale: bool     # diverges from the AI original but no rationale was supplied


def evaluate_baseline_override(
    *,
    submitted_value,
    ai_determined: bool,
    ai_original,
    existing_effective_value,
    existing_key_present: bool,
    has_rationale: bool,
) -> OverrideEvaluation:
    """Classify a baseline-driving submission.

    Divergence resolution order:

    1. AI original determined -> diverges iff ``submitted != ai_original``.
    2. AI original undeterminable but a value is already stored -> fail-safe: diverges iff
       ``submitted != existing_effective_value`` so a silent edit still requires a rationale.
    3. AI original undeterminable and brand-new key -> not an override of any AI value: accepted.

    A divergence requires a non-empty rationale; without one ``requires_rationale`` is True and the
    caller must reject the write (HTTP 422). With a rationale the status is ``overridden``; no
    divergence yields ``accepted``.
    """
    if ai_determined:
        diverges = normalize_term(submitted_value) != normalize_term(ai_original)
    elif existing_key_present:
        diverges = normalize_term(submitted_value) != normalize_term(existing_effective_value)
    else:
        diverges = False

    if not diverges:
        return OverrideEvaluation(diverges=False, effective_status="accepted", requires_rationale=False)
    return OverrideEvaluation(
        diverges=True,
        effective_status="overridden",
        requires_rationale=not has_rationale,
    )
