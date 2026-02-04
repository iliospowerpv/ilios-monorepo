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
    extracted_fields: Optional[list[ExtractedFieldSchema]] = None

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

    run_schemas = []
    for run in runs:
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
    from app.db.session import SessionLocal
    from app.crud.ai_parsing_result import AIParsingResultCRUD
    import os
    
    db = SessionLocal()
    try:
        ai_crud = AIParsingResultCRUD(db)
        worker_id = f"worker-{os.getpid()}"
        
        claimed, run = ai_crud.atomic_claim(ai_result_id, correlation_id, worker_id)
        
        if not claimed:
            if run and run.status == FileParsingStatuses.processing:
                logger.info(f"[{correlation_id}] Run {ai_result_id} already claimed by {run.worker_id}, exiting")
            else:
                logger.warning(f"[{correlation_id}] Failed to claim run {ai_result_id}, status={run.status if run else 'not found'}")
            return
        
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
        logger.error(f"[{correlation_id}] Background parsing failed: {e}")
        try:
            ai_crud = AIParsingResultCRUD(db)
            ai_crud.mark_failed(ai_result_id, str(e)[:500])
        except Exception as update_err:
            logger.error(f"[{correlation_id}] Failed to update AIParsingResult status: {update_err}")
    finally:
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
        return {"code": status.HTTP_202_ACCEPTED, "message": FileMessages.file_parse_trigger_success}
    
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

    return {"code": status.HTTP_202_ACCEPTED, "message": FileMessages.file_parse_trigger_success}


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
