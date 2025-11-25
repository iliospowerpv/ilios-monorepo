"""Setup default company boards

Revision ID: f4bb45002531
Revises: a57a1c87dc7c
Create Date: 2024-07-16 13:46:07.285559

"""

from typing import Sequence, Union

from app.crud.board import BoardCRUD
from app.crud.board_related_entity import BoardRelatedEntityCRUD
from app.crud.company import CompanyCRUD
from app.db.session import get_session
from app.helpers.task_tracker.board_defaults_helper import create_default_board
from app.models.board import BoardRelatedEntityTypeEnum

# revision identifiers, used by Alembic.
revision: str = "f4bb45002531"
down_revision: Union[str, None] = "a57a1c87dc7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    db_session = next(get_session())
    for company in CompanyCRUD(db_session).get(skip_pagination=True):
        if BoardRelatedEntityCRUD(db_session).get_entity_default_board(company.id, BoardRelatedEntityTypeEnum.company):
            continue
        create_default_board(company.id, BoardRelatedEntityTypeEnum.company, db_session)


def downgrade() -> None:
    db_session = next(get_session())
    for company in CompanyCRUD(db_session).get(skip_pagination=True):
        related_entity_board = BoardRelatedEntityCRUD(db_session).get_entity_default_board(
            company.id, BoardRelatedEntityTypeEnum.company
        )
        if related_entity_board:
            BoardCRUD(db_session).delete_by_id(related_entity_board.board_id)
