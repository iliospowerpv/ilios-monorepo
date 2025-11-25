from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field

from app.models.comment import CommentedEntityTypeEnum
from app.schema.paginator import BasePaginator


class PostCommentSchema(BaseModel):
    entity_type: CommentedEntityTypeEnum
    entity_id: int = Field(examples=[1])
    text: str = Field(examples=["Nobody expects the Spanish Inquisition"], max_length=1000)
    mentioned_users_ids: Optional[list[int]] = Field(
        None, examples=[[1, 2]], description="IDs of users who can be mentioned"
    )
    extra: Optional[Dict] = Field(default=None, description="The dict of additional parameters for the comment")


class CommentsPageSchema(BaseModel):
    id: int = Field(examples=[1])
    entity_id: int = Field(examples=[2])
    text: str = Field(examples=["Why eyes hurt after the solar eclipse?"])
    created_at: datetime
    updated_at: datetime
    first_name: str = Field(examples=["John"])
    last_name: str = Field(examples=["Doe"])


class CommentsPaginator(BasePaginator):
    """Comments schema along pagination fields included"""

    items: list[CommentsPageSchema]


class CommentCreationSuccess(BaseModel):
    message: str = Field(description="Success message", examples=["Comment has been successfully created"])
    code: int = Field(description="Success status code", examples=[201])
