"""Baseline-input unit normalization (Scope B) — pure, DB-free.

Guards :mod:`app.services.telemetry.baseline_input_normalization`:

* it only ever *proposes* a normalized value — never applies one (the caller
  requires an explicit reviewer confirmation);
* it NEVER guesses a unit: ambiguous / unknown / missing units block;
* the two unit-bearing physics fields have DIFFERENT canonical units
  (``module_wattage`` = W, ``inverter_wattage`` = kW) and a plain unit *strip*
  is distinguished from a real unit *conversion* (which needs an extra
  conversion confirmation);
* quantities are unitless counts and are intentionally NOT normalizable.
"""
from __future__ import annotations

import pytest

from app.services.telemetry import baseline_input_normalization as norm


# ---------------------------------------------------------------------------
# Field eligibility
# ---------------------------------------------------------------------------
def test_only_wattage_fields_are_normalizable():
    assert norm.is_normalizable_field("module_wattage") is True
    assert norm.is_normalizable_field("inverter_wattage") is True
    assert norm.is_normalizable_field("module_quantity") is False
    assert norm.is_normalizable_field("inverter_quantity") is False
    assert norm.is_normalizable_field("cec_efficiency_pct") is False


def test_non_normalizable_field_is_blocked():
    p = norm.propose("module_quantity", "1000 pcs")
    assert p.blocked is True
    assert p.proposed_value is None
    assert "normalizable unit" in p.reason


# ---------------------------------------------------------------------------
# module_wattage (target unit: W)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw", ["340 W", "340Wp", " 340  watt ", "340 watts"])
def test_module_wattage_same_unit_is_a_strip(raw):
    p = norm.propose("module_wattage", raw)
    assert p.blocked is False
    assert p.method == "unit_strip"
    assert p.requires_conversion_confirmation is False
    assert p.requires_confirmation is True
    assert p.proposed_value == pytest.approx(340.0)
    assert p.target_unit == "W"


def test_module_wattage_kw_is_a_conversion():
    p = norm.propose("module_wattage", "0.34 kW")
    assert p.blocked is False
    assert p.method == "unit_convert"
    assert p.requires_conversion_confirmation is True
    assert p.factor == pytest.approx(1000.0)
    assert p.proposed_value == pytest.approx(340.0)


def test_module_wattage_comma_thousands_parses():
    p = norm.propose("module_wattage", "1,200 W")
    assert p.blocked is False
    assert p.proposed_value == pytest.approx(1200.0)


# ---------------------------------------------------------------------------
# inverter_wattage (target unit: kW)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw", ["66 kW", "66kWac", "66 kWp"])
def test_inverter_wattage_same_unit_is_a_strip(raw):
    p = norm.propose("inverter_wattage", raw)
    assert p.blocked is False
    assert p.method == "unit_strip"
    assert p.requires_conversion_confirmation is False
    assert p.proposed_value == pytest.approx(66.0)
    assert p.target_unit == "kW"


def test_inverter_wattage_watts_is_a_conversion():
    p = norm.propose("inverter_wattage", "66000 W")
    assert p.blocked is False
    assert p.method == "unit_convert"
    assert p.requires_conversion_confirmation is True
    assert p.factor == pytest.approx(0.001)
    assert p.proposed_value == pytest.approx(66.0)


def test_inverter_kva_is_never_treated_as_kw():
    # kVA is apparent power, not real power — it must block (never guessed).
    p = norm.propose("inverter_wattage", "66 kVA")
    assert p.blocked is True
    assert p.proposed_value is None
    assert "ambiguous" in p.reason or "not recognized" in p.reason


# ---------------------------------------------------------------------------
# Blocked / unparseable paths (units are never assumed)
# ---------------------------------------------------------------------------
def test_unknown_unit_blocks():
    p = norm.propose("module_wattage", "340 foo")
    assert p.blocked is True
    assert p.parseable is True  # parsed as number+unit, but unit unrecognized
    assert p.from_unit == "foo"


def test_bare_number_without_unit_blocks():
    # A unit is never assumed — a bare number is reported as not normalizable.
    p = norm.propose("module_wattage", "340")
    assert p.blocked is True
    assert p.parseable is False


def test_empty_value_blocks():
    p = norm.propose("module_wattage", "")
    assert p.blocked is True
    assert p.parseable is False


def test_none_value_blocks():
    p = norm.propose("module_wattage", None)
    assert p.blocked is True


# ---------------------------------------------------------------------------
# values_match — tolerant cross-check of a reviewer-confirmed value
# ---------------------------------------------------------------------------
def test_values_match_within_tolerance():
    assert norm.values_match(340.0, 340.00001) is True
    assert norm.values_match(340.0, 340.0) is True


def test_values_match_rejects_divergence_and_none():
    assert norm.values_match(340.0, 350.0) is False
    assert norm.values_match(None, 340.0) is False
    assert norm.values_match(340.0, None) is False
