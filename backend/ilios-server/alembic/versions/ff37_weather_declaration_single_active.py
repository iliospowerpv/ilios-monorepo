"""Weather Semantics Governed Declaration (WS.2) — single-active partial unique indexes.

Revision ID: ff37_weather_declaration_single_active
Revises: ff36_weather_semantics_governed_declaration
Create Date: 2026-06-22

Background
----------
WS.2 promises that a *governed* ``weather_device_mappings`` lineage holds at most
one ``active`` declaration at a time. The service enforces this with a
``SELECT ... FOR UPDATE`` lock on existing active rows, but that lock cannot
serialize two concurrent activations of an *empty* lineage (both observe zero
active rows and both proceed). This migration adds the durable, DB-level backstop:
two PARTIAL UNIQUE indexes that make a second active row in the same lineage a
constraint violation regardless of application logic or concurrency.

The lineage key is ``(site_id, device_id, metric)`` for device-backed rows and
``(site_id, external_device_id, metric)`` when ``device_id`` is NULL, so the
guarantee is split across two complementary partial indexes:

* ``uq_weather_device_mappings_active_device`` —
  ``UNIQUE (site_id, device_id, metric) WHERE declaration_status = 'active'
  AND device_id IS NOT NULL``
* ``uq_weather_device_mappings_active_external`` —
  ``UNIQUE (site_id, external_device_id, metric) WHERE declaration_status = 'active'
  AND device_id IS NULL``

Both are PARTIAL (``WHERE declaration_status = 'active'``) so legacy/ungoverned
rows (NULL status), drafts, and superseded rows are never constrained — only the
single live row per lineage is. ``metric`` is NOT NULL, so the index always has a
complete key. The indexes are checked per-statement (non-deferrable), which is why
the activation service supersedes the prior active row BEFORE flipping the new
draft to active, so the lineage never holds two active rows at any flush point.

This migration is ADDITIVE ONLY and changes no existing behavior at deploy: it
creates no columns, writes no rows, and touches nothing in the resolver/expected
math, ingestion, rollups, the scheduler, device eligibility/classification,
baselines, or O&M. At deploy time there are no governed ``active`` rows yet (WS.1
only just introduced the status column, and legacy rows carry NULL status, which
the partial predicate excludes), so index creation is safe on existing data.

Rollback
--------
``downgrade()`` drops both partial unique indexes. No data is affected.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ff37_weather_declaration_single_active"
down_revision = "ff36_weather_semantics_governed_declaration"
branch_labels = None
depends_on = None


TABLE = "weather_device_mappings"
IDX_ACTIVE_DEVICE = "uq_weather_device_mappings_active_device"
IDX_ACTIVE_EXTERNAL = "uq_weather_device_mappings_active_external"


def upgrade() -> None:
    op.create_index(
        IDX_ACTIVE_DEVICE,
        TABLE,
        ["site_id", "device_id", "metric"],
        unique=True,
        postgresql_where=sa.text(
            "declaration_status = 'active' AND device_id IS NOT NULL"
        ),
    )
    op.create_index(
        IDX_ACTIVE_EXTERNAL,
        TABLE,
        ["site_id", "external_device_id", "metric"],
        unique=True,
        postgresql_where=sa.text(
            "declaration_status = 'active' AND device_id IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(IDX_ACTIVE_EXTERNAL, table_name=TABLE)
    op.drop_index(IDX_ACTIVE_DEVICE, table_name=TABLE)
