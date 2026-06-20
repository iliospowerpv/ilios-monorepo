"""WA baseline physics validation — additive audit columns.

Adds two nullable-only columns to ``telemetry_expected_baselines`` so the
activation gate can persist its structured physics-validation verdict alongside
the policy version that produced it:

* ``validation_result_json`` (JSONB) — the full
  :class:`BaselineValidationReport` (field classifications, cross-field checks,
  Fahrenheit/Celsius smoke-test probes + checks, temperature-unit contract,
  timestamp, source mode). Audit/history only.
* ``validation_policy_version`` (String) — the ``baseline-physics-v1`` policy id
  that judged the row, so a later policy change can never silently reinterpret a
  stored verdict.

ADDITIVE ONLY. Both columns are NULL for every existing row and for drafts /
superseded baselines. A NULL verdict NEVER implies "valid": the live O&M read
path validates the active baseline on read regardless of what is stored here.
No existing column, enum, index, or data is touched; no backfill is performed.

Revision ID: ff34_baseline_physics_validation
Revises: ff33_device_eligibility_classification
Create Date: 2026-06-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "ff34_baseline_physics_validation"
down_revision: Union[str, None] = "ff33_device_eligibility_classification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telemetry_expected_baselines",
        sa.Column("validation_result_json", JSONB(), nullable=True),
    )
    op.add_column(
        "telemetry_expected_baselines",
        sa.Column("validation_policy_version", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telemetry_expected_baselines", "validation_policy_version")
    op.drop_column("telemetry_expected_baselines", "validation_result_json")
