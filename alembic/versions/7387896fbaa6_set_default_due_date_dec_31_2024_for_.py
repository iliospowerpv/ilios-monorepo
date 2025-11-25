"""Set default due date Dec 31 2024 for empty due_date tasks field

Revision ID: 7387896fbaa6
Revises: f4bb45002531
Create Date: 2024-07-18 15:29:08.398603

"""

from datetime import date
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from app.models.task import Task


# revision identifiers, used by Alembic.
revision: str = "7387896fbaa6"
down_revision: Union[str, None] = "f4bb45002531"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    for task_id, due_date in conn.execute(text("SELECT id, due_date FROM tasks;")).fetchall():
        if due_date is None:
            # Set default task date Dec 31 2024
            conn.execute(
                Task.__table__.update()
                .where(Task.id == task_id)
                .values(
                    due_date=date(2024, 12, 31),
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    for task_id, due_date in conn.execute(text("SELECT id, due_date FROM tasks")).fetchall():
        if due_date == date(2024, 12, 31):
            # Set default task date to None if date is Dec 31 2024
            conn.execute(
                Task.__table__.update()
                .where(Task.id == task_id)
                .values(
                    due_date=None,
                )
            )
