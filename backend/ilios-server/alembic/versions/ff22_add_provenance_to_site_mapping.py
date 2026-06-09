"""Add provenance columns (company_id, created_by_user_id) to telemetry_sites_mapping.

Revision ID: ff22_site_mapping_provenance
Revises: ff21_telemetry_v2_native_ae
Create Date: 2026-06-09

Background
----------
The V2 (DB-backed) project/site telemetry mapping save path persists mappings
directly to iliOS *without* the legacy GCP / Firestore pipeline. To make each
mapping self-describing and auditable, this migration adds two additive,
nullable provenance columns:

- ``company_id``         -- owning company of the mapped project/site.
- ``created_by_user_id`` -- the user who first created the mapping.

Both columns are nullable, so pre-existing mappings are preserved untouched and
no data is wiped. They are populated going forward by the V2 mapping endpoint.

Rollback
--------
``downgrade()`` drops the two columns.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ff22_site_mapping_provenance"
down_revision = "ff21_telemetry_v2_native_ae"
branch_labels = None
depends_on = None

TABLE = "telemetry_sites_mapping"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "created_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(TABLE, "created_by_user_id")
    op.drop_column(TABLE, "company_id")
