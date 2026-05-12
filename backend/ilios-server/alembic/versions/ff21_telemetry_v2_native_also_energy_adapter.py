"""Switch also_energy provider to the native (non-Cloud-Function) adapter.

Revision ID: ff21_telemetry_v2_native_ae
Revises: ff20_auth_security_events
Create Date: 2026-05-12

Background
----------
The legacy ``CloudFunctionAdapter`` path requires a GCP ID token to invoke
a Google Cloud Function gateway. Ilios cannot fetch that ID token in its
current runtime environment, so V2 ``Test Credentials`` calls fail with
``Provider call failed: ConnectionError`` even when stored credentials are
correct.

This migration flips the ``telemetry_provider_catalog`` row for
``also_energy`` to point at the new
``NativeAlsoEnergyAdapter`` which talks to ``api.alsoenergy.com``
directly.

Rollback
--------
``downgrade()`` restores the original ``AlsoEnergyAdapter`` (Cloud
Function-backed) so operators can revert without code changes.
"""
from __future__ import annotations

from alembic import op

revision = "ff21_telemetry_v2_native_ae"
down_revision = "ff20_auth_security_events"
branch_labels = None
depends_on = None

PROVIDER_KEY = "also_energy"
PREVIOUS_ADAPTER_CLASS = (
    "app.integrations.telemetry.also_energy_adapter.AlsoEnergyAdapter"
)
NEW_ADAPTER_CLASS = (
    "app.integrations.telemetry.native_also_energy_adapter.NativeAlsoEnergyAdapter"
)


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE telemetry_provider_catalog
           SET adapter_class = '{NEW_ADAPTER_CLASS}',
               updated_at    = NOW()
         WHERE provider_key  = '{PROVIDER_KEY}'
           AND adapter_class = '{PREVIOUS_ADAPTER_CLASS}'
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE telemetry_provider_catalog
           SET adapter_class = '{PREVIOUS_ADAPTER_CLASS}',
               updated_at    = NOW()
         WHERE provider_key  = '{PROVIDER_KEY}'
           AND adapter_class = '{NEW_ADAPTER_CLASS}'
        """
    )
