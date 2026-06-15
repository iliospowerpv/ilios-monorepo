"""Device Eligibility Expansion — additive telemetry classification columns.

Adds nullable-only telemetry classification/eligibility metadata to ``devices`` so
meters, power/DAS loggers, gateways, and weather-source sensors can be classified
and mapped for inspection WITHOUT changing their canonical ``category`` and WITHOUT
auto-driving expected/O&M math. Every column is NULL by default and means "derive
from category/type" via ``app.services.telemetry.device_classification`` — so this
migration changes no behavior on its own and requires no data backfill.

This migration is ADDITIVE ONLY. It does not touch existing columns, enums, the
``DeviceCategories``/``DeviceTypes`` enums, telemetry readings/rollups, mappings,
or any synced provider device. No DB enum type is created (``device_role`` is a
plain string so the role taxonomy can grow without future migrations).

Revision ID: ff33_device_eligibility_classification
Revises: ff32_weather_provenance_foundation
Create Date: 2026-06-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ff33_device_eligibility_classification"
down_revision: Union[str, None] = "ff32_weather_provenance_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STRING_COLUMNS = (
    "device_role",
    "source_provider",
    "external_device_type",
    "eligibility_reason",
    "ineligibility_reason",
)

_BOOLEAN_COLUMNS = (
    "telemetry_capable",
    "weather_source_capable",
    "production_meter_capable",
    "gateway_capable",
    "virtual_device",
)


def upgrade() -> None:
    for name in _STRING_COLUMNS:
        op.add_column("devices", sa.Column(name, sa.String(), nullable=True))
    for name in _BOOLEAN_COLUMNS:
        op.add_column("devices", sa.Column(name, sa.Boolean(), nullable=True))


def downgrade() -> None:
    for name in reversed(_BOOLEAN_COLUMNS):
        op.drop_column("devices", name)
    for name in reversed(_STRING_COLUMNS):
        op.drop_column("devices", name)
