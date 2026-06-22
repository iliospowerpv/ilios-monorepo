"""DD V2 Phase 2 — Module Datasheet schema, equipment-aware parsing & governed review.

These guard the honesty + safety contract of the Phase 2 work, which replaces the
generic contractual stub assigned to ``module_specs`` with a specialized Module
Datasheet schema routed through the EXISTING governed workflow. The hard constraints
under test:

* the specialized ``module_specs`` schema is additive (the generic stub is retained
  as inactive history) and re-seeding is idempotent (versioning, never duplication);
* ``module_wattage`` is the SINGLE canonical STC/nameplate power field — there is no
  ``module_power_stc_w``;
* the richer parse output (raw value, printed unit, confidence, per-field status, and
  per-variant data) flows through ``combine_user_ai_parsing_results`` VERBATIM — the
  system never converts a unit and never auto-selects a value for an ambiguous /
  multi-variant field (the reviewer must choose);
* the additive ``FileKeySchema`` / ``FileParsingEvidence`` fields are backward
  compatible (old payloads validate; new fields default to ``None``);
* the new physics fields are reconciliation-visible but NOT baseline-driving — the
  reconciliation catalog lists them with ``baseline_target=NONE`` and they never enter
  ``BASELINE_DRIVING_FACT_FIELDS`` / ``FACT_FIELD_TO_COLUMN`` / the baseline-from-facts
  mappings.

The registry idempotency test runs the real seeders inside an ISOLATED engine
connection + transaction that is always rolled back, so it never touches the shared
session-scoped ``db_session`` state. The ``combine`` tests monkeypatch the parsing
config resolver and drive the real transformation with lightweight stand-in objects,
so they need no DB seeding.
"""
from __future__ import annotations

import types

import sqlalchemy as sa

from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.files.file_helper import combine_user_ai_parsing_results
from app.models.file import FileParsingStatuses
from app.schema.file import FileKeySchema, FileParsingEvidence
from app.services import extraction_registry_seeding as seeding
from app.services.telemetry.baseline_from_facts_service import (
    BASELINE_DRIVING_FACT_FIELDS,
    FACT_FIELD_TO_COLUMN,
)
from app.static.reconciliation_catalog import (
    CATALOG_BY_NAME,
    EQUIPMENT,
    HEADER_COLUMN,
    NONE,
    RECONCILIATION_CATALOG,
    _MODULE_DATASHEET_FIELDS,
)

# The exhaustive set of canonical fields that drive the expected/baseline math.
# Phase 2 must NOT widen this beyond the pre-existing four wattage/quantity fields.
EXPECTED_BASELINE_DRIVING = frozenset(
    {"module_wattage", "module_quantity", "inverter_wattage", "inverter_quantity"}
)

# The new physics datasheet fields added in Phase 2. They are reconciliation-visible
# but must never become baseline-driving.
PHASE2_PHYSICS_FIELDS = (
    "thermal_coefficient_pct",
    "power_tolerance_min_pct",
    "power_tolerance_max_pct",
    "year_1_degradation_pct",
    "annual_degradation_pct",
    "module_efficiency_pct",
    "voc",
    "isc",
    "vmp",
    "imp",
    "noct",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _document(doc_type_name: str = "module_specs"):
    """A lightweight stand-in for the ``Document`` ORM object combine() needs."""
    return types.SimpleNamespace(
        name=types.SimpleNamespace(value=doc_type_name), keys=[]
    )


def _completed_file(parsed_result: dict | None = None, result=None, file_id: int = 17):
    """A lightweight stand-in for a ``File`` with a completed parse run."""
    latest = types.SimpleNamespace(
        status=FileParsingStatuses.completed,
        parsed_result=parsed_result,
        result=result,
    )
    return types.SimpleNamespace(id=file_id, latest_ai_result=latest)


def _patch_config(monkeypatch, fields: list[dict]):
    """Stub the registry config resolver so combine() needs no DB seeding."""
    config = {"fields": fields}
    keys = [f["display_name"] for f in fields]
    monkeypatch.setattr(
        AIParsingHandler, "get_extraction_config", lambda self, document_type: config
    )
    monkeypatch.setattr(
        AIParsingHandler, "get_keys_by_document_type", lambda self, document_type: keys
    )


# ---------------------------------------------------------------------------
# Static schema definition (MODULE_FIELDS)
# ---------------------------------------------------------------------------
class TestModuleSchemaDefinition:
    """The specialized Module Datasheet field set is well-formed and canonical."""

    def test_module_fields_are_specialized_not_the_generic_stub(self):
        # The generic contractual stub is 10 fields; the specialized schema is richer.
        assert len(seeding.MODULE_FIELDS) > 10
        assert len(seeding.MODULE_FIELDS) == 18

    def test_field_names_are_unique(self):
        names = [f["name"] for f in seeding.MODULE_FIELDS]
        assert len(names) == len(set(names))

    def test_module_wattage_is_the_single_stc_nameplate_field(self):
        by_name = {f["name"]: f for f in seeding.MODULE_FIELDS}
        assert "module_wattage" in by_name
        assert by_name["module_wattage"]["expected_unit"] == "W"
        assert by_name["module_wattage"]["is_required"] is True
        # The disallowed duplicate STC power field must never exist.
        assert "module_power_stc_w" not in by_name

    def test_physics_fields_present_with_unit_hints(self):
        by_name = {f["name"]: f for f in seeding.MODULE_FIELDS}
        for name in (
            "thermal_coefficient_pct",
            "power_tolerance_min_pct",
            "power_tolerance_max_pct",
            "year_1_degradation_pct",
            "annual_degradation_pct",
        ):
            assert name in by_name, f"{name} missing from MODULE_FIELDS"
            # Additive expected_unit hint is always present (may be a unit string).
            assert "expected_unit" in by_name[name]

    def test_optional_specs_are_not_required(self):
        by_name = {f["name"]: f for f in seeding.MODULE_FIELDS}
        # Optional datasheet specs never force a parse to fail.
        assert by_name["thermal_coefficient_pct"]["is_required"] is False
        assert by_name["year_1_degradation_pct"]["is_required"] is False


# ---------------------------------------------------------------------------
# Registry versioning / idempotency (real seeders, isolated transaction)
# ---------------------------------------------------------------------------
class TestRegistrySeedingIdempotency:
    """Seeding the specialized schema is additive and re-runs are no-ops."""

    def test_module_specs_seeder_is_idempotent_and_specialized(self):
        from tests.conftest import engine

        conn = engine.connect()
        trans = conn.begin()
        try:
            # Generic coverage first creates the module_specs doc type (+ stub).
            seeding.seed_generic_extraction_coverage(conn)

            first = seeding.seed_module_specs_specialized_schema(conn)
            second = seeding.seed_module_specs_specialized_schema(conn)

            # First run creates the specialized schema + prompt and links every field.
            assert first["schema_created"] is True
            assert first["prompt_created"] is True
            assert first["fields_linked"] == len(seeding.MODULE_FIELDS)

            # Second run is a pure no-op (versioning, never duplication).
            assert second["schema_created"] is False
            assert second["prompt_created"] is False
            assert second["fields_linked"] == 0

            # Exactly one active schema for the doc type, and it is the specialized one.
            active = conn.execute(
                sa.text(
                    "SELECT sv.id FROM extraction_schema_versions sv "
                    "JOIN extraction_document_types dt ON dt.id = sv.document_type_id "
                    "WHERE dt.name = :n AND sv.is_active = true"
                ),
                {"n": seeding.MODULE_DOC_TYPE_NAME},
            ).fetchall()
            assert len(active) == 1
            active_schema_id = active[0][0]

            field_count = conn.execute(
                sa.text(
                    "SELECT count(*) FROM extraction_schema_version_fields "
                    "WHERE schema_version_id = :id"
                ),
                {"id": active_schema_id},
            ).scalar_one()
            assert field_count == len(seeding.MODULE_FIELDS)

            rows = conn.execute(
                sa.text(
                    "SELECT cf.name FROM extraction_schema_version_fields svf "
                    "JOIN canonical_fields cf ON cf.id = svf.canonical_field_id "
                    "WHERE svf.schema_version_id = :id"
                ),
                {"id": active_schema_id},
            ).fetchall()
            names = {r[0] for r in rows}
            assert "module_wattage" in names
            assert "thermal_coefficient_pct" in names
            assert "module_power_stc_w" not in names
        finally:
            trans.rollback()
            conn.close()


# ---------------------------------------------------------------------------
# Parser JSON shape — no conversion, no variant selection (real combine())
# ---------------------------------------------------------------------------
class TestCombinePreservesEquipmentMetadata:
    """combine_user_ai_parsing_results carries the richer parse output verbatim."""

    def test_ambiguous_variants_preserved_and_never_auto_selected(self, monkeypatch):
        _patch_config(
            monkeypatch,
            [{"name": "module_wattage", "display_name": "Module Wattage", "expected_unit": "W"}],
        )
        variants = [
            {"label": "Q.PEAK 405", "raw_value": "405", "raw_unit": "W"},
            {"label": "Q.PEAK 410", "raw_value": "410", "raw_unit": "W"},
            {"label": "Q.PEAK 415", "raw_value": "415", "raw_unit": "W"},
        ]
        parsed = {
            "fields": [
                {
                    "field_key": "module_wattage",
                    "value": None,  # ambiguous -> no single value
                    "raw_value": None,
                    "raw_unit": "W",
                    "confidence": "low",
                    "status": "ambiguous",
                    "variants": variants,
                    "evidence": {
                        "page": 1,
                        "table_or_section": "Electrical Data (STC)",
                        "snippet": "405-415 Wp",
                    },
                }
            ]
        }
        keys = combine_user_ai_parsing_results(
            document=_document(), db_session=None, due_diligence_file=_completed_file(parsed)
        )
        mw = next(k for k in keys if k["name"] == "Module Wattage")

        # No value was auto-populated for the reviewer to passively accept.
        assert mw["ai_value"] is None
        assert mw["value"] is None
        # Status + confidence pass through.
        assert mw["extraction_status"] == "ambiguous"
        assert mw["confidence"] == "low"
        # The printed unit is preserved, never converted.
        assert mw["raw_unit"] == "W"
        # The expected/canonical unit is a display hint only.
        assert mw["expected_unit"] == "W"
        # Every variant is preserved EXACTLY — no selection, no rewriting.
        assert mw["variants"] == variants
        assert len(mw["variants"]) == 3
        # Evidence (incl. the additive table/section) survives.
        assert mw["evidence"]["table_or_section"] == "Electrical Data (STC)"

    def test_extracted_field_metadata_passthrough(self, monkeypatch):
        _patch_config(
            monkeypatch,
            [
                {
                    "name": "module_efficiency_pct",
                    "display_name": "Module Efficiency",
                    "expected_unit": "%",
                }
            ],
        )
        parsed = {
            "fields": [
                {
                    "field_key": "module_efficiency_pct",
                    "value": "20.9",
                    "raw_value": "20.9",
                    "raw_unit": "%",
                    "confidence": "high",
                    "status": "extracted",
                    "variants": None,
                    "evidence": {"page": 2},
                }
            ]
        }
        keys = combine_user_ai_parsing_results(
            document=_document(), db_session=None, due_diligence_file=_completed_file(parsed)
        )
        eff = next(k for k in keys if k["name"] == "Module Efficiency")
        assert eff["ai_value"] == "20.9"
        assert eff["raw_value"] == "20.9"
        assert eff["raw_unit"] == "%"
        assert eff["expected_unit"] == "%"
        assert eff["confidence"] == "high"
        assert eff["extraction_status"] == "extracted"
        assert eff["variants"] is None

    def test_contractual_fields_have_null_equipment_metadata(self, monkeypatch):
        """Back-compat: a contractual parse result (no equipment keys) is unaffected."""
        _patch_config(
            monkeypatch,
            [{"name": "lessor_name", "display_name": "Lessor (Landlord) Entity Name", "expected_unit": None}],
        )
        parsed = {
            "fields": [
                {
                    "field_key": "lessor_name",
                    "value": "GreenLife Solar, LLC",
                    "evidence": {"page": 1},
                }
            ]
        }
        keys = combine_user_ai_parsing_results(
            document=_document("site_lease"),
            db_session=None,
            due_diligence_file=_completed_file(parsed),
        )
        lessor = next(k for k in keys if k["name"] == "Lessor (Landlord) Entity Name")
        assert lessor["ai_value"] == "GreenLife Solar, LLC"
        # All additive equipment fields default to None for contractual documents.
        assert lessor["raw_value"] is None
        assert lessor["raw_unit"] is None
        assert lessor["expected_unit"] is None
        assert lessor["confidence"] is None
        assert lessor["extraction_status"] is None
        assert lessor["variants"] is None


# ---------------------------------------------------------------------------
# FileKeySchema / FileParsingEvidence back-compat
# ---------------------------------------------------------------------------
class TestFileSchemaBackCompat:
    """The additive schema fields are optional and default to None."""

    def test_minimal_key_defaults_new_fields_to_none(self):
        k = FileKeySchema(name="Module Wattage")
        assert k.raw_value is None
        assert k.raw_unit is None
        assert k.expected_unit is None
        assert k.confidence is None
        assert k.extraction_status is None
        assert k.variants is None
        assert k.is_baseline_driving is False

    def test_legacy_payload_still_validates(self):
        # An old-shaped payload (no Phase 2 keys) validates unchanged.
        k = FileKeySchema(**{"name": "Lessor", "value": "Y", "ai_value": "Z"})
        assert k.value == "Y"
        assert k.ai_value == "Z"
        assert k.variants is None

    def test_new_fields_round_trip(self):
        k = FileKeySchema(
            name="Module Wattage",
            raw_value="405",
            raw_unit="W",
            expected_unit="W",
            confidence="low",
            extraction_status="ambiguous",
            variants=[{"label": "405W", "raw_value": "405", "raw_unit": "W"}],
        )
        dumped = k.model_dump()
        assert dumped["raw_value"] == "405"
        assert dumped["expected_unit"] == "W"
        assert dumped["extraction_status"] == "ambiguous"
        assert dumped["variants"][0]["raw_value"] == "405"

    def test_evidence_table_or_section_is_optional(self):
        assert FileParsingEvidence(page=1).table_or_section is None
        e = FileParsingEvidence(page=1, table_or_section="Electrical Data (STC)")
        assert e.table_or_section == "Electrical Data (STC)"


# ---------------------------------------------------------------------------
# Reconciliation catalog — new read-only rows, existing rows unchanged
# ---------------------------------------------------------------------------
class TestReconciliationCatalogRows:
    """The module datasheet rows are read-only (no baseline target) and additive."""

    def test_module_datasheet_rows_are_read_only_equipment(self):
        assert len(_MODULE_DATASHEET_FIELDS) == 17
        for field in _MODULE_DATASHEET_FIELDS:
            assert field.category == EQUIPMENT
            assert field.baseline_target == NONE
            assert field.required_for_baseline is False
            assert field.month is None

    def test_module_datasheet_rows_appended_last(self):
        # Appended last so existing row positions are unchanged.
        assert list(RECONCILIATION_CATALOG[-17:]) == _MODULE_DATASHEET_FIELDS

    def test_no_catalog_name_collisions(self):
        assert len(CATALOG_BY_NAME) == len(RECONCILIATION_CATALOG)

    def test_wattage_and_quantity_keep_baseline_rows(self):
        module_names = {f.canonical_name for f in _MODULE_DATASHEET_FIELDS}
        # These keep their pre-existing baseline-driving physics rows; they must NOT
        # be duplicated into the read-only equipment block.
        assert "module_wattage" not in module_names
        assert "module_quantity" not in module_names
        assert CATALOG_BY_NAME["module_wattage"].baseline_target == HEADER_COLUMN
        assert CATALOG_BY_NAME["module_quantity"].baseline_target == HEADER_COLUMN

    def test_module_datasheet_rows_are_not_baseline_driving(self):
        for field in _MODULE_DATASHEET_FIELDS:
            assert field.canonical_name not in BASELINE_DRIVING_FACT_FIELDS
            assert field.canonical_name not in FACT_FIELD_TO_COLUMN


# ---------------------------------------------------------------------------
# Baseline-driving guard — the math inputs never widened
# ---------------------------------------------------------------------------
class TestBaselineDrivingFieldsUnchanged:
    """Phase 2 never widens the set of fields that drive expected/baseline math."""

    def test_baseline_driving_fact_fields_are_exactly_the_four(self):
        assert BASELINE_DRIVING_FACT_FIELDS == EXPECTED_BASELINE_DRIVING

    def test_fact_field_to_column_is_the_identity_four_map(self):
        assert FACT_FIELD_TO_COLUMN == {name: name for name in EXPECTED_BASELINE_DRIVING}

    def test_new_physics_fields_are_not_baseline_driving(self):
        for name in PHASE2_PHYSICS_FIELDS:
            assert name not in BASELINE_DRIVING_FACT_FIELDS
            assert name not in FACT_FIELD_TO_COLUMN
