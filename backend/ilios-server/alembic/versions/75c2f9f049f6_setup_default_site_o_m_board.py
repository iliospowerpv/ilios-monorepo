"""setup default site O&M board

Revision ID: 75c2f9f049f6
Revises: 1b3470371c4c
Create Date: 2024-09-16 19:45:26.721850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from app.crud.board_related_entity import BoardRelatedEntityCRUD
from app.crud.site import SiteCRUD
from app.helpers.task_tracker.board_defaults_helper import create_default_board
from app.models.board import BoardRelatedEntityTypeEnum, BoardModuleEnum

revision: str = '75c2f9f049f6'
down_revision: Union[str, None] = '1b3470371c4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create default site O&M board if they don't exist"""
    connection = op.get_bind()
    db_session = sa.orm.Session(bind=connection)
    for site in SiteCRUD(db_session).get(skip_pagination=True):
        total, _ = BoardRelatedEntityCRUD(db_session).get_by_entity(entity_type=BoardRelatedEntityTypeEnum.site,
                                                                    entity_id=site.id,
                                                                    module=BoardModuleEnum.om)
        if total > 0:
            continue
        create_default_board(site.id, BoardRelatedEntityTypeEnum.site, db_session, module=BoardModuleEnum.om)


def downgrade() -> None:
    """Remove all site O&M boards and related entities"""
    conn = op.get_bind()
    conn.execute(sa.text("""DELETE FROM board_related_entities
    USING boards
    WHERE board_related_entities.board_id = boards.id
      AND boards.module = 'om'
      AND board_related_entities.entity_type = 'site';"""))
    conn.execute(sa.text("""DELETE FROM boards WHERE boards.module = 'om';"""))
