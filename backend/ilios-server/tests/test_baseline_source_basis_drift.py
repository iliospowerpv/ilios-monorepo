"""Unit tests for the read-only source-basis drift resolver (Phase B4).

These exercise the pure resolver
(:func:`app.services.telemetry.baseline_source_basis_drift.resolve_source_basis_drift`)
with in-memory baseline/fact stand-ins — no DB session is involved, which is
itself the zero-write guarantee (the resolver takes no `Session`).
"""
import datetime

from app.models.project_facts import ProjectFact
from app.models.telemetry_expected import TelemetryExpectedBaseline
from app.services.telemetry import baseline_source_basis_drift as drift
from app.services.telemetry.baseline_from_facts_service import _coerce_number


def _sf(column, value, fact_id):
    return {
        "canonical_name": column,
        "column": column,
        "fact_id": fact_id,
        "value": value,
        "document_id": None,
        "ai_confidence": None,
    }


def _params(*, source_facts=None, field_sources=None, signature="sig"):
    return {
        "source_fact_signature": signature,
        "source_facts": source_facts or [],
        "field_sources": field_sources or {},
    }


def _baseline(params, *, baseline_id=900, **cols):
    b = TelemetryExpectedBaseline(id=baseline_id, model_parameters_json=params)
    b.created_at = datetime.datetime(2025, 1, 1)
    b.approved_at = None
    b.active_from = None
    for key, value in cols.items():
        setattr(b, key, value)
    return b


def _fact(fact_id, raw):
    return ProjectFact(id=fact_id, value={"v": raw})


def test_no_active_baseline_returns_honest_empty_result():
    result = drift.resolve_source_basis_drift(None, {})
    assert result.state == drift.STATE_BASIS_UNKNOWN
    assert result.unknown_basis is True
    assert result.baseline_id is None
    assert result.drifted_fields == []


def test_same_value_new_fact_id_is_up_to_date():
    # Site 4 false-positive guard: a new fact id carrying the SAME value is NOT drift.
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)]),
        module_wattage=340,
    )
    result = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, 340.0)}
    )
    assert result.state == drift.STATE_UP_TO_DATE
    assert result.drifted_fields == []


def test_changed_value_is_drifted_with_field_payload():
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)]),
        module_wattage=340,
    )
    result = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, 400.0)}
    )
    assert result.state == drift.STATE_DRIFTED
    assert len(result.drifted_fields) == 1
    field = result.drifted_fields[0]
    assert field.field == "module_wattage"
    assert field.current_fact_id == 99


def test_string_form_change_equal_value_is_up_to_date():
    # Equal value expressed differently ("0.34 kWp" == 340 Wp) must NOT drift;
    # the signature would mismatch, but value comparison resolves it.
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)]),
        module_wattage=340,
    )
    result = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, "0.34 kWp")}
    )
    assert result.state == drift.STATE_UP_TO_DATE


def test_text_with_unit_equal_is_up_to_date():
    assert _coerce_number("340 Wp") is None  # plain coercion alone is insufficient
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)]),
        module_wattage=340,
    )
    result = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, "340 Wp")}
    )
    assert result.state == drift.STATE_UP_TO_DATE


def test_text_with_unit_drift_requires_normalization():
    # Without unit normalization "350 Wp" would coerce to None and be missed;
    # the resolver must normalize and report drift.
    assert _coerce_number("350 Wp") is None
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)]),
        module_wattage=340,
    )
    result = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, "350 Wp")}
    )
    assert result.state == drift.STATE_DRIFTED
    assert result.drifted_fields[0].field == "module_wattage"


def test_empty_source_facts_and_null_signature_is_basis_unknown():
    # Site 4 #4: typed columns exist but no recorded lineage → basis_unknown, never drift.
    baseline = _baseline(
        _params(source_facts=[], signature=None), module_wattage=340
    )
    result = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, 999.0)}
    )
    assert result.state == drift.STATE_BASIS_UNKNOWN
    assert result.unknown_basis is True
    assert result.drifted_fields == []


def test_reviewer_supplied_field_is_no_fact_lineage():
    baseline = _baseline(
        _params(
            source_facts=[_sf("module_wattage", 340.0, fact_id=10)],
            field_sources={"thermal_coefficient_pct": {"source": "reviewer_supplied"}},
        ),
        module_wattage=340,
    )
    result = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, 340.0)}
    )
    assert "thermal_coefficient_pct" in result.no_fact_lineage_fields
    assert result.state == drift.STATE_UP_TO_DATE


def test_retired_basis_fact_with_no_active_replacement_is_source_retired():
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)]),
        module_wattage=340,
    )
    result = drift.resolve_source_basis_drift(
        baseline, {}, retired_fact_ids=frozenset({10})
    )
    assert result.state == drift.STATE_SOURCE_RETIRED


def test_missing_active_fact_without_retirement_is_no_fact_lineage():
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)]),
        module_wattage=340,
    )
    result = drift.resolve_source_basis_drift(baseline, {})
    assert result.state == drift.STATE_UP_TO_DATE
    assert "module_wattage" in result.no_fact_lineage_fields


def test_quantity_field_compares_by_count_only():
    baseline = _baseline(
        _params(source_facts=[_sf("module_quantity", 100.0, fact_id=10)]),
        module_quantity=100,
    )
    drifted = drift.resolve_source_basis_drift(
        baseline, {"module_quantity": _fact(99, 120)}
    )
    assert drifted.state == drift.STATE_DRIFTED
    # A unit-bearing quantity is uncoercible (never normalized) → neutral, not drift.
    neutral = drift.resolve_source_basis_drift(
        baseline, {"module_quantity": _fact(99, "120 units")}
    )
    assert neutral.state == drift.STATE_UP_TO_DATE


def test_field_without_recorded_basis_is_not_drifted():
    # Only module_wattage has a recorded basis; module_quantity has none and must
    # never be flagged even when its active fact differs.
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)]),
        module_wattage=340,
        module_quantity=100,
    )
    result = drift.resolve_source_basis_drift(
        baseline,
        {
            "module_wattage": _fact(99, 340.0),
            "module_quantity": _fact(98, 500),
        },
    )
    assert result.state == drift.STATE_UP_TO_DATE
    assert all(f.field != "module_quantity" for f in result.drifted_fields)


def test_basis_value_falls_back_to_typed_column_when_value_omitted():
    baseline = _baseline(
        _params(source_facts=[_sf("module_wattage", None, fact_id=10)]),
        module_wattage=340,
    )
    same = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, 340.0)}
    )
    assert same.state == drift.STATE_UP_TO_DATE
    changed = drift.resolve_source_basis_drift(
        baseline, {"module_wattage": _fact(99, 360.0)}
    )
    assert changed.state == drift.STATE_DRIFTED


def test_resolver_does_not_mutate_inputs():
    params = _params(source_facts=[_sf("module_wattage", 340.0, fact_id=10)])
    baseline = _baseline(params, module_wattage=340)
    active = {"module_wattage": _fact(99, 400.0)}
    before = dict(baseline.model_parameters_json)
    before_value = dict(active["module_wattage"].value)
    drift.resolve_source_basis_drift(baseline, active)
    assert baseline.model_parameters_json == before
    assert active["module_wattage"].value == before_value
