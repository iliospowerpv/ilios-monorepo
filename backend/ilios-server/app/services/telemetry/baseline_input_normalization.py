"""Reviewer-confirmed unit normalization for baseline physics inputs.

A small, pure, DB-free helper used by the promoted-facts → draft-baseline bridge
(:mod:`app.services.telemetry.baseline_from_facts_service`). Some active facts
arrive as unit-qualified text (e.g. ``"340 Wp"`` for a module, ``"66 kWac"`` for
an inverter). The strict :func:`_coerce_number` deliberately refuses to parse
these (it never guesses), so they are reported as non-numeric and block the
draft.

This module proposes a normalized numeric value for such text — but it NEVER
applies one silently. It only ever *proposes*; the caller requires an explicit
reviewer confirmation (and, for a unit conversion such as ``W → kW``, a separate
explicit conversion confirmation) before the proposed value is used. The
``project_facts`` row is never mutated.

Two facts carry units the calc cares about, with DIFFERENT canonical units:

* ``module_wattage`` is in **watts (W)**
* ``inverter_wattage`` is in **kilowatts (kW)**

Quantities (``module_quantity`` / ``inverter_quantity``) are unitless counts and
are intentionally NOT normalizable here — a non-numeric quantity stays missing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Canonical unit each normalizable physics field is expressed in.
EXPECTED_UNITS: dict[str, str] = {
    "module_wattage": "W",
    "inverter_wattage": "kW",
}

# Per-field recognized unit tokens (lower-cased) -> (multiplier_to_target_unit,
# is_same_unit). ``is_same_unit`` True means a plain unit *strip* (value already
# in the target unit); False means a real unit *conversion* (needs the reviewer's
# explicit conversion confirmation). Anything not listed is ambiguous and blocks
# (never guessed). ``kVA`` is intentionally absent for inverters: it is apparent
# power, not real power (kW), so it is never silently treated as kW.
_UNIT_TABLES: dict[str, dict[str, tuple[float, bool]]] = {
    "module_wattage": {  # target: W
        "w": (1.0, True),
        "wp": (1.0, True),
        "watt": (1.0, True),
        "watts": (1.0, True),
        "kw": (1000.0, False),
        "kwp": (1000.0, False),
    },
    "inverter_wattage": {  # target: kW
        "kw": (1.0, True),
        "kwac": (1.0, True),
        "kwp": (1.0, True),
        "w": (0.001, False),
        "wac": (0.001, False),
        "watt": (0.001, False),
        "watts": (0.001, False),
        "mw": (1000.0, False),
        "mwac": (1000.0, False),
    },
}

# number + trailing unit token, e.g. "340 Wp", "66kWac", "1,000 W".
_VALUE_UNIT_RE = re.compile(
    r"^\s*([+-]?[0-9][0-9,]*\.?[0-9]*)\s*([A-Za-z/µ°]+)\s*$"
)


@dataclass(frozen=True)
class NormalizationProposal:
    """A proposed (never auto-applied) normalization of a unit-qualified value."""

    field: str
    raw_value: str
    target_unit: str
    parseable: bool
    blocked: bool
    reason: str
    proposed_value: Optional[float] = None
    from_unit: Optional[str] = None
    method: Optional[str] = None  # 'unit_strip' | 'unit_convert'
    factor: float = 1.0
    requires_confirmation: bool = False
    requires_conversion_confirmation: bool = False


def is_normalizable_field(field: str) -> bool:
    """Only the two unit-bearing physics fields can be normalized."""
    return field in EXPECTED_UNITS


def _parse(raw: str) -> Optional[tuple[float, str]]:
    """Split ``"340 Wp"`` -> ``(340.0, "wp")``; ``None`` when not number+unit."""
    match = _VALUE_UNIT_RE.match(raw)
    if match is None:
        return None
    number_text = match.group(1).replace(",", "")
    unit_token = match.group(2).strip().lower()
    try:
        number = float(number_text)
    except ValueError:
        return None
    if not unit_token:
        return None
    return number, unit_token


def propose(field: str, raw) -> NormalizationProposal:
    """Propose a normalized numeric value for a unit-qualified fact value.

    The result always describes *why* it is or is not usable; it never mutates
    anything and never returns a value the caller may apply without an explicit
    reviewer confirmation. A blocked proposal (ambiguous / missing / unknown unit
    or an unparseable value) means the field stays missing.
    """
    target_unit = EXPECTED_UNITS.get(field, "")
    raw_str = "" if raw is None else str(raw).strip()

    if not is_normalizable_field(field):
        return NormalizationProposal(
            field=field,
            raw_value=raw_str,
            target_unit=target_unit,
            parseable=False,
            blocked=True,
            reason=f"{field} does not carry a normalizable unit.",
        )

    if not raw_str:
        return NormalizationProposal(
            field=field,
            raw_value=raw_str,
            target_unit=target_unit,
            parseable=False,
            blocked=True,
            reason="Value is empty.",
        )

    parsed = _parse(raw_str)
    if parsed is None:
        return NormalizationProposal(
            field=field,
            raw_value=raw_str,
            target_unit=target_unit,
            parseable=False,
            blocked=True,
            reason=(
                f"{raw_str!r} is not a number followed by a unit — units are "
                "never assumed; enter a unit-qualified value to normalize."
            ),
        )

    number, unit_token = parsed
    table = _UNIT_TABLES.get(field, {})
    entry = table.get(unit_token)
    if entry is None:
        return NormalizationProposal(
            field=field,
            raw_value=raw_str,
            target_unit=target_unit,
            parseable=True,
            blocked=True,
            reason=(
                f"Unit {unit_token!r} is not recognized for {field} (expected "
                f"{target_unit}); it is ambiguous and is never guessed."
            ),
            from_unit=unit_token,
        )

    multiplier, is_same_unit = entry
    proposed_value = number * multiplier
    method = "unit_strip" if is_same_unit else "unit_convert"
    if is_same_unit:
        reason = (
            f"{raw_str!r} is already in {target_unit}; confirm to use "
            f"{proposed_value:g} {target_unit}."
        )
    else:
        reason = (
            f"{raw_str!r} must be converted to {target_unit} "
            f"(x{multiplier:g}) = {proposed_value:g} {target_unit}; "
            "confirm the conversion explicitly."
        )
    return NormalizationProposal(
        field=field,
        raw_value=raw_str,
        target_unit=target_unit,
        parseable=True,
        blocked=False,
        reason=reason,
        proposed_value=proposed_value,
        from_unit=unit_token,
        method=method,
        factor=multiplier,
        requires_confirmation=True,
        requires_conversion_confirmation=not is_same_unit,
    )


def values_match(a: Optional[float], b: Optional[float]) -> bool:
    """Tolerant float compare for cross-checking a reviewer-confirmed value."""
    if a is None or b is None:
        return False
    return abs(a - b) <= max(1e-6, 1e-4 * abs(b))
