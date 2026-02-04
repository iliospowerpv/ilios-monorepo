import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.crud.commented_entity import CommentedEntityCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_file
from app.helpers.permission_guards import require_module_permission
from app.helpers.configs.agreement_names_helper import AgreementNamesMappingHandler
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.files.file_helper import combine_user_ai_parsing_results
from app.models.comment import CommentedEntityTypeEnum
from app.models.file import File as FileModel
from app.models.file import FileParsingStatuses, AIParsingResult
from app.schema.file import FileKeysList, FileParseTriggerSuccess, FileParsingStatus
from app.schema.user import CurrentUserSchema
from app.services.extraction_pipeline_service import ExtractionPipelineService
from app.services.in_app_parsing_service import InAppParsingService
from app.settings import settings
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, HTTP_409_RESPONSE, FileMessages

logger = logging.getLogger(__name__)
files_parsing_router = APIRouter()


class ReprocessRequest(BaseModel):
    schema_version_id: Optional[int] = None
    prompt_template_id: Optional[int] = None
    force: bool = False

    class Config:
        from_attributes = True


class ReprocessResponse(BaseModel):
    job_id: int
    status: str
    message: str
    is_reprocess: bool
    schema_version_id: Optional[int] = None
    prompt_template_id: Optional[int] = None


class EvidenceSchema(BaseModel):
    page: Optional[int] = None
    snippet: Optional[str] = None
    anchor_text: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractedFieldSchema(BaseModel):
    field_name: str
    value: Optional[str] = None
    confidence: Optional[float] = None
    evidence: Optional[EvidenceSchema] = None

    class Config:
        from_attributes = True


class ParseRunSchema(BaseModel):
    id: int
    file_id: int
    status: str
    extraction_run_number: Optional[int] = None
    document_type_id: Optional[int] = None
    schema_version_id: Optional[int] = None
    prompt_template_id: Optional[int] = None
    is_reprocess: Optional[bool] = False
    force_reprocess: Optional[bool] = False
    retries: Optional[int] = 0
    error_message: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    created_at: Optional[str] = None
    correlation_id: Optional[str] = None
    was_truncated: Optional[bool] = None
    char_count: Optional[int] = None
    word_count: Optional[int] = None
    page_count: Optional[int] = None
    extracted_fields: Optional[list[ExtractedFieldSchema]] = None
    is_latest: Optional[bool] = None

    class Config:
        from_attributes = True


class ParseRunHistoryResponse(BaseModel):
    file_id: int
    runs: list[ParseRunSchema]
    total: int


@files_parsing_router.get(
    "/runs/",
    response_model=ParseRunHistoryResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get parse run history for a file, including status, bindings, and retries.",
)
async def get_parse_run_history(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    ai_results_crud = AIParsingResultCRUD(db_session)
    runs = ai_results_crud.get_runs_for_file(file.id)
    latest_run = ai_results_crud.get_latest_run_for_file(file.id)
    latest_run_id = latest_run.id if latest_run else None

    run_schemas = []
    for run in runs:
        metadata = run.parsed_result.get("_metadata", {}) if run.parsed_result and isinstance(run.parsed_result, dict) else {}
        run_schemas.append(ParseRunSchema(
            id=run.id,
            file_id=run.file_id,
            status=run.status.value if run.status else "unknown",
            extraction_run_number=run.extraction_run_number,
            document_type_id=run.document_type_id,
            schema_version_id=run.schema_version_id,
            prompt_template_id=run.prompt_template_id,
            is_reprocess=run.is_reprocess,
            force_reprocess=run.force_reprocess,
            retries=run.retries,
            error_message=run.error_message,
            start_time=run.start_time.isoformat() if run.start_time else None,
            end_time=run.end_time.isoformat() if run.end_time else None,
            created_at=run.created_at.isoformat() if hasattr(run, 'created_at') and run.created_at else None,
            correlation_id=run.correlation_id,
            was_truncated=metadata.get("was_truncated"),
            char_count=metadata.get("char_count"),
            word_count=metadata.get("word_count"),
            page_count=metadata.get("page_count"),
            is_latest=(run.id == latest_run_id),
        ))

    return ParseRunHistoryResponse(
        file_id=file.id,
        runs=run_schemas,
        total=len(run_schemas),
    )


@files_parsing_router.get(
    "/runs/{run_id}/",
    response_model=ParseRunSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get details of a specific parse run.",
)
async def get_parse_run_detail(
    run_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    ai_results_crud = AIParsingResultCRUD(db_session)
    run = ai_results_crud.get_run_by_id(run_id)

    if not run or run.file_id != file.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Parse run not found")

    extracted_fields = None
    if run.parsed_result and isinstance(run.parsed_result, dict):
        fields = []
        for key, val in run.parsed_result.items():
            if key.startswith("_"):
                continue
            if isinstance(val, dict):
                evidence = None
                if "evidence" in val:
                    ev = val["evidence"]
                    evidence = EvidenceSchema(
                        page=ev.get("page"),
                        snippet=ev.get("snippet"),
                        anchor_text=ev.get("anchor_text"),
                    )
                fields.append(ExtractedFieldSchema(
                    field_name=key,
                    value=val.get("value") if isinstance(val.get("value"), str) else str(val.get("value")) if val.get("value") else None,
                    confidence=val.get("confidence"),
                    evidence=evidence,
                ))
            else:
                fields.append(ExtractedFieldSchema(
                    field_name=key,
                    value=str(val) if val is not None else None,
                ))
        extracted_fields = fields if fields else None

    return ParseRunSchema(
        id=run.id,
        file_id=run.file_id,
        status=run.status.value if run.status else "unknown",
        extraction_run_number=run.extraction_run_number,
        document_type_id=run.document_type_id,
        schema_version_id=run.schema_version_id,
        prompt_template_id=run.prompt_template_id,
        is_reprocess=run.is_reprocess,
        force_reprocess=run.force_reprocess,
        retries=run.retries,
        error_message=run.error_message,
        start_time=run.start_time.isoformat() if run.start_time else None,
        end_time=run.end_time.isoformat() if run.end_time else None,
        created_at=run.created_at.isoformat() if hasattr(run, 'created_at') and run.created_at else None,
        extracted_fields=extracted_fields,
    )


def _run_parsing_background(
    file_id: int,
    ai_result_id: int,
    document_type_name: str,
    correlation_id: str,
):
    """Background task to run in-app parsing. Uses its own DB session.
    
    Implements atomic claim pattern:
    1. Attempt to claim the run (status must be 'queued')
    2. If claim fails, exit gracefully (another worker got it)
    3. On any failure, mark run as failed with end_time
    """
    import sys
    import os
    import traceback
    
    print(f"[{correlation_id}] BACKGROUND TASK STARTED for file {file_id}, run {ai_result_id}", file=sys.stderr, flush=True)
    logger.info(f"[{correlation_id}] Background task starting for file {file_id}, run {ai_result_id}")
    
    try:
        print(f"[{correlation_id}] Importing SessionFactory...", file=sys.stderr, flush=True)
        from app.db.session import SessionFactory
        print(f"[{correlation_id}] Importing AIParsingResultCRUD...", file=sys.stderr, flush=True)
        from app.crud.ai_parsing_result import AIParsingResultCRUD
        print(f"[{correlation_id}] Imports successful", file=sys.stderr, flush=True)
    except Exception as import_err:
        print(f"[{correlation_id}] IMPORT ERROR: {type(import_err).__name__}: {import_err}", file=sys.stderr, flush=True)
        print(f"[{correlation_id}] Import traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
        return
    
    print(f"[{correlation_id}] Creating DB session...", file=sys.stderr, flush=True)
    db = SessionFactory()
    print(f"[{correlation_id}] DB session created, starting try block...", file=sys.stderr, flush=True)
    try:
        ai_crud = AIParsingResultCRUD(db)
        worker_id = f"worker-{os.getpid()}"
        print(f"[{correlation_id}] Attempting atomic_claim for run {ai_result_id}...", file=sys.stderr, flush=True)
        
        claimed, run = ai_crud.atomic_claim(ai_result_id, correlation_id, worker_id)
        print(f"[{correlation_id}] atomic_claim returned: claimed={claimed}, run={run}", file=sys.stderr, flush=True)
        
        if not claimed:
            if run and run.status == FileParsingStatuses.processing:
                logger.info(f"[{correlation_id}] Run {ai_result_id} already claimed by {run.worker_id}, exiting")
            else:
                logger.warning(f"[{correlation_id}] Failed to claim run {ai_result_id}, status={run.status if run else 'not found'}")
            return
        
        print(f"[{correlation_id}] Successfully claimed run {ai_result_id}", file=sys.stderr, flush=True)
        logger.info(f"[{correlation_id}] Claimed run {ai_result_id} for file {file_id}")
        
        from app.models.file import File
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            logger.error(f"[{correlation_id}] File {file_id} not found for background parsing")
            ai_crud.mark_failed(ai_result_id, f"File {file_id} not found")
            return
        
        parsing_service = InAppParsingService(db)
        parsing_service.parse_file(file, ai_result_id, document_type_name, correlation_id)
        
    except Exception as e:
        print(f"[{correlation_id}] EXCEPTION in background task: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        print(f"[{correlation_id}] Traceback: {traceback.format_exc()}", file=sys.stderr, flush=True)
        logger.error(f"[{correlation_id}] Background parsing failed: {e}")
        try:
            ai_crud = AIParsingResultCRUD(db)
            ai_crud.mark_failed(ai_result_id, str(e)[:500])
        except Exception as update_err:
            print(f"[{correlation_id}] Failed to mark as failed: {update_err}", file=sys.stderr, flush=True)
            logger.error(f"[{correlation_id}] Failed to update AIParsingResult status: {update_err}")
    finally:
        print(f"[{correlation_id}] Background task cleanup, closing DB session", file=sys.stderr, flush=True)
        db.close()


@files_parsing_router.post(
    "/parsing/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=FileParseTriggerSuccess,
    responses={
        **HTTP_403_RESPONSE,
        **HTTP_404_RESPONSE,
        **HTTP_409_RESPONSE(message=FileMessages.file_parse_conflict),
    },
    description="Trigger in-app AI file parsing asynchronously using Replit AI Integrations (OpenAI).",
)
async def trigger_file_parsing(
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    if file.document.name.value not in AIParsingHandler(db_session).get_parsable_documents_list():
        logger.warning(message := f"Parsing feature is not available for the <{file.document.name.value}> files")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    pipeline_document_name = AgreementNamesMappingHandler(db_session).get_pipeline_agreement_name(file.document.name)
    if not pipeline_document_name:
        logger.warning(message := f"Parsing config is not found for the <{file.document.name.value}> files")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    file_extension = file.filename.split(".")[-1]
    if file_extension not in settings.ai_parsing_allowed_extensions.split(","):
        message = (
            f"Parsing feature is not available for the <{file_extension}> file type. "
            f"Allowed file types: <{settings.ai_parsing_allowed_extensions}>"
        )
        logger.warning(message)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    ai_results_crud = AIParsingResultCRUD(db_session)
    
    parsing_service = InAppParsingService(db_session)
    if not parsing_service.check_openai_available():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI parsing service not configured. OpenAI integration not available.",
        )

    pipeline_service = ExtractionPipelineService(db_session)
    extraction_config = pipeline_service.get_extraction_config(file.document.name.value)
    
    doc_type_id = extraction_config["document_type"]["id"] if extraction_config else None
    schema_version_id = extraction_config["schema_version"]["id"] if extraction_config else None
    prompt_template_id = extraction_config["prompt_template"]["id"] if extraction_config else None

    run_count = db_session.query(AIParsingResult).filter(AIParsingResult.file_id == file.id).count()
    correlation_id = str(uuid.uuid4())[:8]
    
    ai_record_payload = {
        "file_id": file.id,
        "status": FileParsingStatuses.queued,
        "extraction_run_number": run_count + 1,
        "correlation_id": correlation_id,
        "document_type_id": doc_type_id,
        "schema_version_id": schema_version_id,
        "prompt_template_id": prompt_template_id,
    }

    run, is_new = ai_results_crud.create_or_get_active(file.id, ai_record_payload)
    
    if not is_new:
        logger.info(f"Returning existing active run {run.id} for file {file.id} (idempotency)")
        return {
            "code": status.HTTP_202_ACCEPTED,
            "message": FileMessages.file_parse_trigger_success,
            "run_id": run.id,
            "correlation_id": run.correlation_id or correlation_id,
            "status": run.status.value if hasattr(run.status, 'value') else str(run.status),
        }
    
    logger.info(
        f"[{correlation_id}] Created queued parsing job {run.id} for file {file.id}: "
        f"storage_key={file.storage_key}, document_type={pipeline_document_name}"
    )

    background_tasks.add_task(
        _run_parsing_background,
        file.id,
        run.id,
        pipeline_document_name,
        correlation_id,
    )

    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": FileMessages.file_parse_trigger_success,
        "run_id": run.id,
        "correlation_id": correlation_id,
        "status": FileParsingStatuses.queued.value,
    }


@files_parsing_router.get(
    "/parsing-status/",
    response_model=FileParsingStatus,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get actual at the moment file parsing status",
)
async def file_parsing_status(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
    return file.latest_ai_result if file.latest_ai_result else {}


@files_parsing_router.get(
    "/parsing-result/",
    response_model=FileKeysList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get list of file keys with custom User values and values received from AI",
)
async def get_file_parsing_results(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
    response = combine_user_ai_parsing_results(document=file.document, due_diligence_file=file, db_session=db_session)
    # post-process to retrieve comments and related to the result key,
    # DB relationship usage on each entity will decrease the performance,
    # let's retrieve all comments and then attach to the corresponding key object
    keys_ids = [res["id"] for res in response if res["id"]]
    keys_comments = CommentedEntityCRUD(db_session).get_by_entities_grouped(
        entity_type=CommentedEntityTypeEnum.document_key, entities_ids=keys_ids
    )
    for comments_row in keys_comments:
        document_id, comments = comments_row
        document = [document_response for document_response in response if document_response["id"] == document_id][0]
        document["comments"] = comments
    return {"keys": response}


@files_parsing_router.post(
    "/reprocess/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ReprocessResponse,
    responses={
        **HTTP_403_RESPONSE,
        **HTTP_404_RESPONSE,
        **HTTP_409_RESPONSE(message="Reprocess with same bindings already completed"),
    },
    description="Reprocess a file with optional schema/prompt version selection using in-app AI parsing.",
)
async def reprocess_file(
    request: ReprocessRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )

    parsing_service = InAppParsingService(db_session)
    if not parsing_service.check_openai_available():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI parsing service not configured. OpenAI integration not available.",
        )

    pipeline_service = ExtractionPipelineService(db_session)
    ai_results_crud = AIParsingResultCRUD(db_session)

    doc_type_name = file.document.name.value
    extraction_config = pipeline_service.get_extraction_config(doc_type_name)
    if not extraction_config:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Document type '{doc_type_name}' not found in registry"
        )

    doc_type_id = extraction_config["document_type"]["id"]
    schema_version_id = request.schema_version_id or extraction_config["schema_version"]["id"]
    prompt_template_id = request.prompt_template_id or extraction_config["prompt_template"]["id"]

    if not request.force:
        existing_completed = db_session.query(AIParsingResult).filter(
            AIParsingResult.file_id == file.id,
            AIParsingResult.schema_version_id == schema_version_id,
            AIParsingResult.prompt_template_id == prompt_template_id,
            AIParsingResult.status == FileParsingStatuses.completed,
        ).first()

        if existing_completed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Reprocess with same bindings already completed. Use force=true to override."
            )

    run_count = db_session.query(AIParsingResult).filter(
        AIParsingResult.file_id == file.id
    ).count()

    correlation_id = str(uuid.uuid4())[:8]
    payload = {
        "file_id": file.id,
        "status": FileParsingStatuses.queued,
        "document_type_id": doc_type_id,
        "schema_version_id": schema_version_id,
        "prompt_template_id": prompt_template_id,
        "extraction_run_number": run_count + 1,
        "is_reprocess": True,
        "force_reprocess": request.force,
        "correlation_id": correlation_id,
    }
    
    if request.force:
        new_job = ai_results_crud.create_item(payload)
        is_new = True
    else:
        new_job, is_new = ai_results_crud.create_or_get_active(file.id, payload)

    if not is_new:
        logger.info(f"Returning existing active run {new_job.id} for reprocess (idempotency)")
        return ReprocessResponse(
            job_id=new_job.id,
            status=new_job.status.value if new_job.status else "queued",
            message="Existing run in progress",
            is_reprocess=new_job.is_reprocess or False,
            schema_version_id=schema_version_id,
            prompt_template_id=prompt_template_id,
        )

    pipeline_document_name = AgreementNamesMappingHandler(db_session).get_pipeline_agreement_name(file.document.name)
    if not pipeline_document_name:
        ai_results_crud.mark_failed(new_job.id, f"Pipeline config not found for {doc_type_name}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Pipeline config not found for {doc_type_name}")

    logger.info(
        f"[{correlation_id}] Created queued reprocess job {new_job.id} for file {file.id}: "
        f"schema_v={schema_version_id}, prompt_v={prompt_template_id}, force={request.force}"
    )

    background_tasks.add_task(
        _run_parsing_background,
        file.id,
        new_job.id,
        pipeline_document_name,
        correlation_id,
    )

    return ReprocessResponse(
        job_id=new_job.id,
        status="queued",
        message="Reprocess job created successfully",
        is_reprocess=True,
        schema_version_id=schema_version_id,
        prompt_template_id=prompt_template_id,
    )


class BulkAcceptFieldSchema(BaseModel):
    field_name: str
    value: Optional[str] = None

    class Config:
        from_attributes = True


class BulkAcceptRequest(BaseModel):
    run_id: int
    fields: list[BulkAcceptFieldSchema]
    allow_accept_non_latest: bool = False

    class Config:
        from_attributes = True


class BulkAcceptResponse(BaseModel):
    code: int
    message: str
    accepted_count: int
    skipped_count: int
    errors: list[str] = []


@files_parsing_router.post(
    "/bulk-accept/",
    response_model=BulkAcceptResponse,
    responses={
        **HTTP_403_RESPONSE,
        **HTTP_404_RESPONSE,
        **HTTP_409_RESPONSE(message="Acceptance validation failed"),
    },
    description="Bulk accept AI-extracted values with safety validation. Validates run belongs to file, run is succeeded, and run is latest (unless allow_accept_non_latest=true).",
)
async def bulk_accept_ai_values(
    request: BulkAcceptRequest,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    from datetime import datetime, timezone
    from app.crud.document_key import DocumentKeyCRUD
    from app.services.project_facts_service import ProjectFactsService

    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )

    ai_results_crud = AIParsingResultCRUD(db_session)
    run = ai_results_crud.get_run_by_id(request.run_id)

    if not run:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Parse run {request.run_id} not found"
        )

    if run.file_id != file.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Run {request.run_id} does not belong to file {file.id}"
        )

    if run.status != FileParsingStatuses.completed:
        status_name = run.status.value if run.status else "unknown"
        if run.status in [FileParsingStatuses.queued, FileParsingStatuses.processing]:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Cannot accept values from run {request.run_id}: run is still {status_name}"
            )
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept values from run {request.run_id}: run status is {status_name}"
            )

    latest_run = ai_results_crud.get_latest_run_for_file(file.id)
    if latest_run and latest_run.id != run.id and not request.allow_accept_non_latest:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Run {request.run_id} is not the latest run. Latest is {latest_run.id}. Set allow_accept_non_latest=true to override."
        )

    if not request.fields:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for acceptance"
        )

    if not run.parsed_result:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Run {request.run_id} has no parsed results to accept"
        )

    document = file.document
    document_key_crud = DocumentKeyCRUD(db_session)
    allowed_keys = AIParsingHandler(db_session).get_keys_by_document_type(document.name.value)

    accepted_count = 0
    skipped_count = 0
    errors = []

    for field in request.fields:
        if field.field_name not in allowed_keys:
            errors.append(f"Key '{field.field_name}' not allowed for document type '{document.name.value}'")
            skipped_count += 1
            continue

        try:
            payload = {
                "value": field.value,
                "editor_id": current_user.id,
                "file_id": file.id,
                "status": "accepted",
                "accepted_by_id": current_user.id,
                "accepted_at": datetime.now(timezone.utc),
            }

            existing_key = document_key_crud.get_document_key(
                name=field.field_name, document_id=document.id, file_id=file.id
            )

            if not existing_key:
                payload |= {"name": field.field_name, "document_id": document.id}
                document_key = document_key_crud.create_item(payload)
            else:
                document_key_crud.update_by_id(existing_key.id, payload)
                db_session.refresh(existing_key)
                document_key = existing_key

            if document_key and document_key.status == "accepted":
                try:
                    facts_service = ProjectFactsService(db_session)
                    facts_service.create_candidate_from_document_key(document_key, document.site_id)
                except Exception as e:
                    logger.warning(f"Failed to create candidate fact for key '{field.field_name}': {str(e)}")

            accepted_count += 1

        except Exception as e:
            errors.append(f"Failed to accept '{field.field_name}': {str(e)}")
            skipped_count += 1

    if accepted_count == 0 and skipped_count > 0:
        response_code = status.HTTP_400_BAD_REQUEST
        response_message = f"Bulk accept failed: all {skipped_count} fields skipped"
    elif skipped_count > 0:
        response_code = 207
        response_message = f"Bulk accept partial: {accepted_count} accepted, {skipped_count} skipped"
    else:
        response_code = status.HTTP_200_OK
        response_message = f"Bulk accept completed: {accepted_count} accepted"

    return BulkAcceptResponse(
        code=response_code,
        message=response_message,
        accepted_count=accepted_count,
        skipped_count=skipped_count,
        errors=errors,
    )
