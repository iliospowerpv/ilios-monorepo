"""add timezone column to sites

Adds a per-site IANA timezone (e.g. "America/New_York"). It drives the
inherently site-local telemetry computations (the daily/"today" production
boundary and reporting/performance analysis); the app's general UI timestamps
continue to render in the viewer's browser timezone and are unaffected.

Existing rows default to 'UTC' (column-only, no data backfill): each site's
accurate zone is set afterward via the site edit form, which doubles as the
end-to-end test. We avoid backfilling specific ids here because migrations run
across environments where the same id may map to a different site.

Revision ID: ff27_site_timezone
Revises: ff26_telemetry_admin_permission
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ff27_site_timezone"
down_revision: Union[str, None] = "ff26_telemetry_admin_permission"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sites",
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
    )


def downgrade() -> None:
    op.drop_column("sites", "timezone")
