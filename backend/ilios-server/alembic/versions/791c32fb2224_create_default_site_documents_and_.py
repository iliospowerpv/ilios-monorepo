"""Create default site documents and sections

Revision ID: 791c32fb2224
Revises: 873cdb4bf114
Create Date: 2024-08-07 13:56:18.943423

"""
import sqlalchemy as sa
from typing import Sequence, Union

from sqlalchemy.orm.session import Session

from alembic import op
from app.helpers.due_diligence.due_diligence_helper import (
    create_default_site_document_sections,
    drop_default_site_document_sections,
    generate_default_site_documents,
)
from app.models.document import Document

# revision identifiers, used by Alembic.
revision: str = '791c32fb2224'
down_revision: Union[str, None] = '873cdb4bf114'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    db_session = Session(bind=connection)
    sites = connection.execute(sa.text("SELECT id FROM sites"))
    site_ids = [site.id for site in sites]
    # Create default sections for each site
    create_default_site_document_sections(site_ids=site_ids, db_session=db_session)
    print("Created site sections")
    # Insert default values for each site
    op.bulk_insert(Document.__table__, generate_default_site_documents(site_ids=site_ids, db_session=db_session))
    print("Created default site documents")


def downgrade() -> None:
    connection = op.get_bind()
    db_session = Session(bind=connection)
    sites = connection.execute(sa.text("SELECT id FROM sites"))
    site_ids = [site.id for site in sites]
    drop_default_site_document_sections(site_ids=site_ids, db_session=db_session)
