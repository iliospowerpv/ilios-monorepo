"""DD V2 Phase 2: Module Datasheet specialized schema/prompt for the "Module Specs" doc type.

Revision ID: ff35_dd_v2_module_specs_specialized_schema
Revises: ff34_baseline_physics_validation
Create Date: 2026-06-22

Background
----------
Phase 2 of the Due Diligence V2 upgrade. The "Module Specs" document type previously
only had the generic Phase 1B contractual stub schema (10 document-agnostic fields).
This migration:

* adds a nullable, additive ``expected_unit`` column to ``canonical_fields`` (a
  display/hint-only canonical unit such as "W", "%", "%/°C" — it never triggers a
  unit conversion), and
* replaces the generic stub *as the active schema* for the Module Specs doc type with
  a specialized Module Datasheet field set + an equipment-aware prompt, via
  ``app.services.extraction_registry_seeding.seed_module_specs_specialized_schema``
  (idempotent; a defensive no-op if the doc type is absent).

The generic stub schema/prompt are deactivated but NEVER mutated (retained as
history). This migration touches ONLY the Module Specs doc type. It does NOT add any
field to ``BASELINE_DRIVING_FACT_FIELDS`` / the baseline-from-facts mappings, does NOT
create or change any baseline, and changes no baseline calculation.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.services.extraction_registry_seeding import (
    remove_module_specs_specialized_schema,
    seed_module_specs_specialized_schema,
)

revision = "ff35_dd_v2_module_specs_specialized_schema"
down_revision = "ff34_baseline_physics_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Additive, nullable column. Must exist before the seeder, which writes it.
    op.add_column(
        "canonical_fields",
        sa.Column("expected_unit", sa.String(length=50), nullable=True),
    )
    connection = op.get_bind()
    seed_module_specs_specialized_schema(connection)


def downgrade() -> None:
    connection = op.get_bind()
    remove_module_specs_specialized_schema(connection)
    op.drop_column("canonical_fields", "expected_unit")
