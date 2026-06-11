"""DD V2 Phase 1B: generic extraction coverage for all SiteDocumentsEnum doc types.

Revision ID: ff30_dd_v2_generic_extraction_coverage
Revises: ff29_dd_v2_fact_provenance
Create Date: 2026-06-11

Background
----------
Phase 1B of the Due Diligence V2 upgrade ("generic eligibility"). Today only the
~17 specialized document types seeded from ``ai_parsing_config.json`` are
parse-eligible; every other ``SiteDocumentsEnum`` document type returns ``None``
from the extraction pipeline and cannot be AI-parsed.

This data migration ensures that EVERY ``SiteDocumentsEnum`` document type has, in
the Extraction Registry, a parsable :class:`ExtractionDocumentType`, an active
generic schema (wired to a small set of generic canonical fields) and an active
generic prompt — but ONLY where no active schema/prompt already exists. The
specialized types keep their existing active schema/prompt untouched, so their
specialized fields always win.

The work is delegated to
``app.services.extraction_registry_seeding.seed_generic_extraction_coverage`` which
is idempotent (re-runnable), additive-only, and matches existing rows by their
normalized name before creating anything.

Rollback
--------
``downgrade()`` removes only the generic (marker-tagged) schema versions and prompt
templates this seeder created; document-type and canonical-field catalog rows are
left in place (additive catalog entries). Removing the generic active schema/prompt
is what reverts parse-eligibility for the affected types.
"""
from __future__ import annotations

from alembic import op

from app.services.extraction_registry_seeding import (
    remove_generic_extraction_coverage,
    seed_generic_extraction_coverage,
)

revision = "ff30_dd_v2_generic_extraction_coverage"
down_revision = "ff29_dd_v2_fact_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    seed_generic_extraction_coverage(connection)


def downgrade() -> None:
    connection = op.get_bind()
    remove_generic_extraction_coverage(connection)
