import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.co_terminus_check import CoTerminusCheckCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.models.file import FileParsingStatuses
from app.schema.co_terminus_checks import CoTerminusCheckResultUpdateRequestSchema, CoTerminusResultSavingSuccess
from app.static import CoTerminusMessages
from app.static.co_terminus_checks import CoTerminusComparisonStatuses
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_co_terminus_router = APIRouter()


@internal_co_terminus_router.patch(
    "/co-terminus-checks/{record_id}/results",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CoTerminusResultSavingSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="""Save AI processing results of the co-terminus check.
    \nIf processing status is completed - actual statuses from request are set.
    \nIf it failed - all terms statuses with 'Pending' changed to 'Error'.""",
)
async def store_co_terminus_check_results(
    record_id: int,
    payload: CoTerminusCheckResultUpdateRequestSchema,
    db_session: Session = Depends(get_session),
):
    co_term_crud = CoTerminusCheckCRUD(db_session)
    co_termius_check_record = co_term_crud.get_by_id(record_id)
    if not co_termius_check_record:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    co_terminus_check_results = co_termius_check_record.result
    # if processing was finished successfully - update preliminary comparison results with statuses from request
    if payload.status == FileParsingStatuses.completed:
        # transform request results into dict for faster lookup
        ai_processed_results = {item.name: item.status.value for item in payload.items}
        for check_item in co_terminus_check_results:
            term_name = check_item["name"]
            if term_name in ai_processed_results:
                check_item["status"] = ai_processed_results[term_name]
    # otherwise, set all processing statuses to the Error
    else:
        for check_item in co_terminus_check_results:
            if check_item["status"] == CoTerminusComparisonStatuses.pending.value:
                check_item["status"] = CoTerminusComparisonStatuses.error.value
    co_term_crud.update_by_id(
        record_id,
        {"status": payload.status, "end_time": datetime.now(timezone.utc), "result": co_terminus_check_results},
    )
    return {"code": status.HTTP_202_ACCEPTED, "message": CoTerminusMessages.check_results_save_success}
