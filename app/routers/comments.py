import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud.comment import CommentCRUD
from app.crud.comment_mention import CommentMentionCRUD
from app.crud.commented_entity import CommentedEntityCRUD
from app.db.session import get_session
from app.helpers.authorization import AssetPermissions, AuthorizedUser, DiligencePermissions, OnMPermissions
from app.helpers.comments import validate_commented_entity_permissions, validate_mentioned_users_permissions
from app.helpers.notification_helper import NotificationHandler
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_skip_and_limit
from app.models.comment import CommentedEntityTypeEnum
from app.models.notification import NotificationKindsEnum, NotificationSubjectsEnum
from app.schema.comment import CommentCreationSuccess, CommentsPaginator, PostCommentSchema
from app.schema.user import CurrentUserSchema
from app.static import (
    DEFAULT_PAGINATION_LIMIT,
    DEFAULT_PAGINATION_SKIP,
    HTTP_403_RESPONSE,
    HTTP_404_RESPONSE,
    PermissionsActions,
    PermissionsModules,
)

logger = logging.getLogger(__name__)
comments_router = APIRouter()


@comments_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentCreationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def create(
    comment: PostCommentSchema,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit, validate_query_module_name=True),
                    DiligencePermissions(PermissionsActions.edit, validate_query_module_name=True),
                    OnMPermissions(PermissionsActions.edit, validate_query_module_name=True),
                ]
            )
        ),
    ],
    permission_module: PermissionsModules,
    db_session: Session = Depends(get_session),
):
    entity_type, entity_id = comment.entity_type, comment.entity_id
    commented_entity = validate_commented_entity_permissions(entity_id, entity_type, current_user, db_session)

    # validate people who are mentioned has access to this commented entity
    if comment.mentioned_users_ids:
        validate_mentioned_users_permissions(comment, entity_type, commented_entity, permission_module, db_session)

    comment_payload = {"text": comment.text, "user_id": current_user.id}
    if comment.extra:
        comment_payload["extra"] = comment.extra
    comment_model = CommentCRUD(db_session).create_item(comment_payload)
    comment_id = comment_model.id
    commented_entity = CommentedEntityCRUD(db_session).create_item(
        {"entity_id": entity_id, "entity_type": entity_type, "comment_id": comment_id}
    )

    logger.info(f"Created comment with id {comment_id} and related commented_entity with id {commented_entity.id}")
    if comment.mentioned_users_ids:
        CommentMentionCRUD(db_session).create_items(
            [
                {"user_id": mentioned_user_id, "comment_id": comment_id}
                for mentioned_user_id in comment.mentioned_users_ids
            ]
        )
        logger.info(f"Created {len(comment.mentioned_users_ids)} mentions for comment with id {comment_id}")

        # send notification about mention
        notifications_handler = NotificationHandler(
            db_session=db_session,
            actor=current_user,
            notification_subject=NotificationSubjectsEnum.comment,
            notification_subject_id=comment_id,
        )
        # track extras
        file_id = comment.extra.get("file_id") if comment.extra else None
        for mentioned_user_id in comment.mentioned_users_ids:
            notifications_handler.save_notification(
                recipient_id=mentioned_user_id,
                kind=NotificationKindsEnum.comment_mention,
                extra={"file_id": file_id} if file_id else None,
            )

    return {"code": status.HTTP_201_CREATED, "message": "Comment has been successfully added"}


@comments_router.get(
    "/",
    dependencies=[
        Depends(validate_commented_entity_permissions),
        Depends(validate_skip_and_limit),
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit, validate_query_module_name=True),
                    DiligencePermissions(PermissionsActions.edit, validate_query_module_name=True),
                    OnMPermissions(PermissionsActions.edit, validate_query_module_name=True),
                ]
            )
        ),
    ],
    response_model=CommentsPaginator,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_comments_of_entity(
    entity_type: CommentedEntityTypeEnum,
    entity_id: int,
    # need to keep it here to be prompted from Swagger docs
    permission_module: PermissionsModules,  # noqa: U100
    skip: int = DEFAULT_PAGINATION_SKIP,
    limit: int = DEFAULT_PAGINATION_LIMIT,
    db_session: Session = Depends(get_session),
):
    total, comments = CommentedEntityCRUD(db_session).get_by_entity(entity_type, entity_id, skip, limit)
    return {"items": comments, **pagination_details(skip, limit, total)}
