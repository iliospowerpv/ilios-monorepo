from typing import Optional

from pydantic import BaseModel, Field

from app.models.board import BoardModuleEnum
from app.schema.message import Success
from app.schema.paginator import BasePaginator


class BoardBaseSchema(BaseModel):
    name: Optional[str] = Field(examples=["Dev Board"], default=None)
    description: Optional[str] = Field(examples=["Collection of engineering tasks"], default=None)
    is_active: Optional[bool] = Field(examples=[True], default=True)


class BoardCreateSchema(BoardBaseSchema):
    module: BoardModuleEnum


class BoardsPageSchema(BoardBaseSchema):
    id: int = Field(examples=[1])


class BoardsPaginator(BasePaginator):
    items: list[BoardsPageSchema]


class BoardCreationSuccess(Success):
    message: str = Field(description="Success message", examples=["Board has been successfully added"])


class BoardUpdateSuccess(Success):
    message: str = Field(description="Success message", examples=["Board has been successfully updated"])


class BoardRemovalSuccess(Success):
    message: str = Field(description="Success message", examples=["Board has been successfully deleted"])
