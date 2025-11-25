import logging

from fastapi import Depends, HTTPException, status

from app.crud.attachment import AttachmentCRUD
from app.crud.sv_uploads import SiteVisitUploadCRUD
from app.crud.task import TaskCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import validate_entity_exists
from app.models.board import BoardModuleEnum, BoardRelatedEntityTypeEnum
from app.static import TaskMessages

from ...site_visits_uploads_helper import get_sv_upload_section
from .board import get_authorized_board

logger = logging.getLogger(__name__)


def get_authorized_task(
    task_id: int,
    board=Depends(get_authorized_board),
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """Get task object and validate user has access to it parent entity"""
    # check task exists
    task = TaskCRUD(db_session).get_by_id(task_id)
    validate_entity_exists(task, task_id, "task")
    # check user has access to it
    if task.board_id != board.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access task {task_id} which attached to different board"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return task


def get_authorized_breadcrumbs_task(
    task_id: int,
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """Get task object and validate user has access to it parent entity"""
    # check task exists
    task = TaskCRUD(db_session).get_by_id(task_id)
    validate_entity_exists(task, task_id, "task")
    board = get_authorized_board(task.board_id, current_user, db_session)
    # check user has access to it
    if task.board_id != board.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access task {task_id} which attached to different board"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return task


def get_authorized_attachment(
    attachment_id,
    task=Depends(get_authorized_task),
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """Ensure user has access to the attachment"""
    attachment = AttachmentCRUD(db_session).get_by_id(attachment_id)
    validate_entity_exists(attachment, attachment_id, "attachment")
    # validate attachment belongs to the task from request path
    if attachment.task_id != task.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access attachment {attachment_id} which belongs to different task_id"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return attachment


def get_authorized_site_visit_task(
    task=Depends(get_authorized_task),
):
    """Special case to validate this is O&M site-level task"""
    if not (
        task.board.module == BoardModuleEnum.om
        and task.board.related_entity.entity_type == BoardRelatedEntityTypeEnum.site
    ):
        logger.warning(
            f"Cannot manage site visits for the <{task.board.related_entity.entity_type.value}> level task "
            f"of the <{task.board.module.value}> board"
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=TaskMessages.site_visit_not_applicable)
    return task


def get_authorized_site_visit(
    task=Depends(get_authorized_site_visit_task),
):
    """Validates if site visit exists"""
    if not task.site_visit:
        logger.warning(f"There is no site visit object attached to the task with id <{task.id}>")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=TaskMessages.site_visit_not_found)

    return task.site_visit


def get_authorized_site_visit_upload(
    upload_id,
    site_visit=Depends(get_authorized_site_visit),
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
    upload_section=Depends(get_sv_upload_section),
):
    attachment = SiteVisitUploadCRUD(db_session).get_by_id(upload_id)
    validate_entity_exists(attachment, upload_id, "site_visit_upload")
    # validate upload belongs to the site visit from the path
    if attachment.site_visit_id != site_visit.id:
        logger.warning(
            f"Scope mismatch! User {current_user.id} tried to access site visit attachment "
            f"{upload_id} which belongs to different site visit object"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # validate upload section name corresponds requested
    if attachment.section_name != upload_section.value:
        logger.warning(
            f"User {current_user.id} tried to access site visit attachment "
            f"{upload_id} which belongs to different site visit section"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return attachment
