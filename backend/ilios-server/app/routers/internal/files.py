import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.schema.file import FileUpdateSuccess, ProcessedFileResult
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_files_router = APIRouter()


@internal_files_router.put(
    "/files/{record_id}/parsing",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=FileUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="API to update file parsing results received from cloud function",
)
async def update_file_processing_results(
    record_id: int,
    results: ProcessedFileResult,
    db_session: Session = Depends(get_session),
):
    ai_results_crud = AIParsingResultCRUD(db_session)
    if not ai_results_crud.get_by_id(record_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    results = results.model_dump()
    results.update({"end_time": datetime.now(timezone.utc)})
    ai_results_crud.update_by_id(record_id, results)
    return {"code": status.HTTP_202_ACCEPTED, "message": "File parsing results has been stored"}
