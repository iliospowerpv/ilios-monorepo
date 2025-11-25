import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.comment import CommentCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_comments_router = APIRouter()


@internal_comments_router.delete(
    "/comments/{comment_id}",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def delete_comment_by_id(
    comment_id: int,
    db_session: Session = Depends(get_session),
):
    deleted_count = CommentCRUD(db_session).delete_by_id(comment_id)
    if not deleted_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
