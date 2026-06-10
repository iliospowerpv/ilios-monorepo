"""grant Telemetry.admin to Operations Manager and Company Admin roles

Backfills the new ``Telemetry`` permission module (``admin`` action) onto the
existing global role rows so that the telemetry scheduler / manual-refresh
controls become visible and usable for the roles the product treats as
super-admins:

* "Company Admin"      (project_site_owner)
* "Operations Manager" (project_site_owner)
* "Operations Manager" (operation_maintenance_contractor)

Roles are global (one row per name+company_type, shared across every company via
``company_type_role_mapping``), so updating these rows covers existing *and*
future companies. The system account bypasses the gate entirely, and Company
Admin already passed via the legacy ``Settings Page.edit`` fallback; granting the
explicit ``Telemetry.admin`` key keeps the backend gate and frontend hook
consistent and is what newly seeded environments get from ``default_roles``.

We use an additive ``jsonb_set`` rather than the wholesale ``set_permissions``
helper: it only ever writes the single ``{Telemetry: {admin: true}}`` key,
creating it when absent (current rows have no ``Telemetry`` key) and leaving all
other module permissions untouched. The downgrade removes just that key.

Revision ID: ff26_telemetry_admin_permission
Revises: ff25_telemetry_scheduler_state
Create Date: 2026-06-10
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ff26_telemetry_admin_permission"
down_revision: Union[str, None] = "ff25_telemetry_scheduler_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (role name, company_type) pairs that should carry Telemetry.admin.
_TARGET_ROLES = (
    ("Company Admin", "project_site_owner"),
    ("Operations Manager", "project_site_owner"),
    ("Operations Manager", "operation_maintenance_contractor"),
)

_WHERE_TARGETS = " OR ".join(
    f"(r.name = '{name}' AND m.company_type = '{ctype}')"
    for name, ctype in _TARGET_ROLES
)


def upgrade() -> None:
    # ``roles.permissions`` is a ``json`` column, so cast to ``jsonb`` for the
    # set operation and back to ``json`` for assignment.
    op.execute(
        f"""
        UPDATE roles AS r
        SET permissions = jsonb_set(
            COALESCE(r.permissions::jsonb, '{{}}'::jsonb),
            '{{Telemetry}}',
            '{{"admin": true}}'::jsonb,
            true
        )::json
        FROM company_type_role_mapping AS m
        WHERE m.role_id = r.id
          AND ({_WHERE_TARGETS})
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE roles AS r
        SET permissions = (r.permissions::jsonb - 'Telemetry')::json
        FROM company_type_role_mapping AS m
        WHERE m.role_id = r.id
          AND ({_WHERE_TARGETS})
        """
    )
