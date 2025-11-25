import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.document import DocumentCRUD
from app.crud.document_key import DocumentKeyCRUD
from app.crud.task import TaskCRUD
from app.crud.user import UserCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import get_authorized_board
from app.helpers.authorization.project_access import get_authorized_document, get_authorized_site
from app.helpers.roles_documents_mapping.handlers_factory import RoleDocumentsHandlerFactory
from app.models.comment import CommentedEntityTypeEnum
from app.schema.user import CurrentUserSchema

logger = logging.getLogger(__name__)


def validate_commented_entity_permissions(
    entity_id: int,
    entity_type: CommentedEntityTypeEnum,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Validate current user's permissions to access the commented entity: document, task, etc.

    For "document" entity type validate user has document's site access.
    For "task" entity type validate user has task's board access.
    For "document_key" entity type validate user has document's access.
    """
    entity_crud_mapping = {
        CommentedEntityTypeEnum.document: DocumentCRUD,
        CommentedEntityTypeEnum.task: TaskCRUD,
        CommentedEntityTypeEnum.document_key: DocumentKeyCRUD,
    }
    entity_crud = entity_crud_mapping.get(entity_type)
    if not entity_crud:  # pragma: no cover
        logger.warning(message := f"Comments not allowed for the entity: {entity_type}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)

    commented_entity = entity_crud(db_session).get_by_id(entity_id)
    if not commented_entity:
        logger.warning(f"There is no {entity_type} with id {entity_id}")
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Commented entity {entity_type.value} with id {entity_id} not found"
        )
    if entity_type == CommentedEntityTypeEnum.document:
        get_authorized_site(commented_entity.site_id, current_user, db_session)
    elif entity_type == CommentedEntityTypeEnum.task:
        get_authorized_board(commented_entity.board_id, current_user, db_session)
    elif entity_type == CommentedEntityTypeEnum.document_key:
        site = get_authorized_site(commented_entity.document.site_id, current_user, db_session)
        get_authorized_document(commented_entity.document_id, site, current_user, db_session)
    return commented_entity


def validate_mentioned_users_permissions(comment, entity_type, commented_entity, permission_module, db_session):
    """Validate users to be mentioned in the DD module has access to the document based on their role.
    For the task commenting, use the regular flow to check users by the project access attribute
    """
    allowed_mentions = []
    if entity_type in [CommentedEntityTypeEnum.document, CommentedEntityTypeEnum.document_key]:
        commented_entity_users_source = None
        document_object = None

        # for the document, retrieve users who have access to the site document attached to
        if entity_type in CommentedEntityTypeEnum.document:
            commented_entity_users_source = commented_entity.site
            document_object = commented_entity
        # for the document key, retrieve users who have access to the site parent of the key document it is attached to
        elif entity_type == CommentedEntityTypeEnum.document_key:
            commented_entity_users_source = commented_entity.document.site
            document_object = commented_entity.document

        # get allowed mentioned without role-based access filtering
        unfiltered_allowed_mentions = commented_entity_users_source.get_active_users_ids(permission_module.value)

        # then filter users depending on their access to the document
        output_roles_ids = RoleDocumentsHandlerFactory.get_available_roles_by_document(
            document=document_object, db_session=db_session
        )
        users_with_expected_roles_queryset = UserCRUD(db_session).get_users_by_roles(output_roles_ids)
        users_with_expected_roles_ids = [row.id for row in users_with_expected_roles_queryset]
        allowed_mentions = list(set(unfiltered_allowed_mentions).intersection(users_with_expected_roles_ids))

    elif entity_type == CommentedEntityTypeEnum.task:
        # for the task, both company and site has get_active_users_ids method implemented,
        # so just call it on the entity
        allowed_mentions = commented_entity.board.related_entity.entity.get_active_users_ids(permission_module.value)

    if not all([user_id in allowed_mentions for user_id in comment.mentioned_users_ids]):
        logger.error(
            "Some of mentioned users do not have access to the commented resource: "
            f"request mentions={comment.mentioned_users_ids}, allowed mentions={allowed_mentions}"
        )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Some of users you're trying to tag do not have access to the commented resource",
        )
