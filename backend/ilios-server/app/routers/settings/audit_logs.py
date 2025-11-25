import logging

from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

import app.static as static
from app.crud.audit_log import AuditLogCRUD
from app.db.session import get_session
from app.helpers.authorization import get_current_admin_user
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_skip_and_limit
from app.schema.audit_log import AuditLogsPaginator

logger = logging.getLogger(__name__)
audit_log_router = APIRouter()


@audit_log_router.get(
    "/",
    dependencies=[Depends(get_current_admin_user), Depends(validate_skip_and_limit)],
    response_model=AuditLogsPaginator,
    description="Return user action logs, sorted by the action time descending",
)
async def retrieve_audit_logs(
    skip: int = static.DEFAULT_PAGINATION_SKIP,
    limit: int = static.DEFAULT_PAGINATION_LIMIT,
    db_session: Session = Depends(get_session),
):
    total, log_records = AuditLogCRUD(db_session).get_logs(skip, limit)
    return {"items": log_records, **pagination_details(skip, limit, total)}
