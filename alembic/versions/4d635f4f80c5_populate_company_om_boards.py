"""populate company om boards

Revision ID: 4d635f4f80c5
Revises: 341fd5adb79e
Create Date: 2024-10-08 17:54:11.989570

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from app.crud.board_related_entity import BoardRelatedEntityCRUD
from app.crud.company import CompanyCRUD
from app.db.session import get_session
from app.helpers.task_tracker.board_defaults_helper import create_default_board
from app.models.board import BoardRelatedEntityTypeEnum, BoardModuleEnum

revision: str = '4d635f4f80c5'
down_revision: Union[str, None] = '341fd5adb79e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create default company O&M board if they don't exist"""
    db_session = next(get_session())
    for company in CompanyCRUD(db_session).get(skip_pagination=True):
        total, _ = BoardRelatedEntityCRUD(db_session).get_by_entity(entity_type=BoardRelatedEntityTypeEnum.company,
                                                                    entity_id=company.id,
                                                                    module=BoardModuleEnum.om)
        if total > 0:
            continue
        create_default_board(company.id, BoardRelatedEntityTypeEnum.company, db_session, module=BoardModuleEnum.om)
        print(f"Added board for company {company.id}")


def downgrade() -> None:
    """Remove all company O&M boards and related entities"""
    conn = op.get_bind()
    # retrieve IDs of company O&M boards based on the related entities
    queryset = conn.execute(sa.text("""SELECT ARRAY(
    SELECT board_id FROM board_related_entities 
        JOIN boards ON board_related_entities.board_id = boards.id 
        WHERE boards.module = 'om' AND board_related_entities.entity_type = 'company');"""))
    boards_to_delete_ids = tuple(queryset.fetchall()[0][0])
    # remove related entities
    conn.execute(sa.text("""DELETE FROM board_related_entities
    USING boards
    WHERE board_related_entities.board_id = boards.id
      AND boards.module = 'om'
      AND board_related_entities.entity_type = 'company';"""))
    # remove boards
    conn.execute(sa.text(f"""DELETE FROM boards WHERE module = 'om' AND id IN {boards_to_delete_ids};"""))
