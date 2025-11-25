"""add document task board

Revision ID: a5adab2cb707
Revises: fe2ae822442c
Create Date: 2024-07-30 11:12:13.097224

"""
import sqlalchemy as sa
from typing import Sequence, Union

from alembic import op
from app.crud.board import BoardCRUD
from app.crud.user import UserCRUD
from app.helpers.task_tracker.board_defaults_helper import create_default_board, create_default_document_tasks
from app.models.board import BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum

# revision identifiers, used by Alembic.
revision: str = 'a5adab2cb707'
down_revision: Union[str, None] = 'fe2ae822442c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """For all documents of sites, create default board and default task"""
    connection = op.get_bind()
    db_session = sa.orm.Session(bind=connection)
    # by default, task creator will be the system user
    system_user = UserCRUD(db_session).get_system_user()
    sites = connection.execute(sa.text("SELECT id FROM sites"))
    for site in sites:
        default_board = create_default_board(site.id, BoardRelatedEntityTypeEnum.site, db_session,
                                             BoardRelatedEntityTypeExtraEnum.document)
        create_default_document_tasks(db_session, default_board, site.documents, system_user.id)


def downgrade() -> None:
    connection = op.get_bind()
    db_session = sa.orm.Session(bind=connection)
    sites = connection.execute(sa.text("SELECT id FROM sites"))
    for site in sites:
        for related_board in [related_entity for related_entity in site.related_boards if
                              related_entity.extra_entity_type == 'document']:
            BoardCRUD(db_session).delete_by_id(related_board.board_id)
