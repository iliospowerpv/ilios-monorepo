"""DD V2 Phase 1C: baseline-aware specialized schema/prompt v2 for the As-Built PVsyst report.

Revision ID: ff31_dd_v2_pvsyst_specialized_schema_v2
Revises: ff30_dd_v2_generic_extraction_coverage
Create Date: 2026-06-11

Background
----------
Phase 1C of the Due Diligence V2 upgrade. The As-Built (Second Buyer) PVsyst report
is the document that supplies the energy-production baseline inputs (module/inverter
specs and monthly Year-1 production). This data migration adds a specialized
schema/prompt **v2** for that document type which:

* retains every existing v1 display-name key (the v2 field set is a clone of v1, so
  nothing is lost), and
* guarantees every baseline-driving field (``DueDiligenceBQKeys``) is present and
  flagged ``is_required``, and
* uses a specialized prompt emphasizing precise extraction of the baseline-driving
  equipment/production figures.

It flips ``is_active`` so v2 becomes active; the prior v1 rows are deactivated but
never mutated. The work is delegated to
``app.services.extraction_registry_seeding.seed_pvsyst_specialized_schema_v2`` which
is idempotent and a defensive no-op if the PVsyst doc type is absent.

This migration does NOT create or activate any baseline, and does not change any
baseline calculation.
"""
from __future__ import annotations

from alembic import op

from app.services.extraction_registry_seeding import (
    remove_pvsyst_specialized_schema_v2,
    seed_pvsyst_specialized_schema_v2,
)

revision = "ff31_dd_v2_pvsyst_specialized_schema_v2"
down_revision = "ff30_dd_v2_generic_extraction_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    seed_pvsyst_specialized_schema_v2(connection)


def downgrade() -> None:
    connection = op.get_bind()
    remove_pvsyst_specialized_schema_v2(connection)
