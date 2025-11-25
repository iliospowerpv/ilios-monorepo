import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud.site import SiteCRUD
from app.crud.user import UserCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.helpers.task_tracker.board_defaults_helper import create_default_board, create_default_document_tasks
from app.models.board import BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.schema.documents import SiteIDSchema
from app.schema.site import SiteUpdateSuccess
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_documents_router = APIRouter()


# TODO justify if needed
@internal_documents_router.post(
    "/documents/default-tasks",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SiteUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def create_default_tasks_for_site_documents(
    payload: SiteIDSchema,
    db_session: Session = Depends(get_session),
):
    system_user = UserCRUD(db_session).get_system_user()
    sites_to_process = SiteCRUD(db_session).get(skip_pagination=True)
    if payload.site_ids:
        sites_to_process = [site for site in sites_to_process if site.id in payload.site_ids]
    for site in sites_to_process:
        default_board = [
            related_entity for related_entity in site.related_boards if related_entity.extra_entity_type == "document"
        ]
        if not default_board:
            logger.info("Creating default documents board for site ID:", site.id)
            default_board = create_default_board(
                site.id, BoardRelatedEntityTypeEnum.site, db_session, BoardRelatedEntityTypeExtraEnum.document
            )
        else:
            default_board = default_board[0]
        create_default_document_tasks(db_session, default_board, site.documents, system_user.id, freeze_external_id=True)
    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": "Default site documents tasks has been successfully created",
    }
