"""add_inv1_user_projects_company_trigger

Revision ID: 10e7daa5b8b9
Revises: a4cff08eef74
Create Date: 2026-01-29 13:51:13.360743

INV-1 Invariant: UserProject.company_id must match sites.company_id for the referenced site_id.
This trigger enforces the invariant at the database level for defense in depth.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10e7daa5b8b9'
down_revision: Union[str, None] = 'a4cff08eef74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_inv1_user_projects_company_id()
        RETURNS TRIGGER AS $$
        DECLARE
            site_company_id INTEGER;
        BEGIN
            SELECT company_id INTO site_company_id
            FROM sites
            WHERE id = NEW.site_id;
            
            IF site_company_id IS NULL THEN
                RAISE EXCEPTION 'INV-1 Violation: site_id % does not exist in sites table', NEW.site_id;
            END IF;
            
            IF NEW.company_id IS NULL THEN
                NEW.company_id := site_company_id;
            ELSIF NEW.company_id != site_company_id THEN
                RAISE EXCEPTION 'INV-1 Violation: user_projects.company_id (%) must match sites.company_id (%) for site_id %',
                    NEW.company_id, site_company_id, NEW.site_id;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS trg_enforce_inv1_user_projects_company_id ON user_projects;
    """)
    
    op.execute("""
        CREATE TRIGGER trg_enforce_inv1_user_projects_company_id
        BEFORE INSERT OR UPDATE ON user_projects
        FOR EACH ROW
        EXECUTE FUNCTION enforce_inv1_user_projects_company_id();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_enforce_inv1_user_projects_company_id ON user_projects;
    """)
    
    op.execute("""
        DROP FUNCTION IF EXISTS enforce_inv1_user_projects_company_id();
    """)
