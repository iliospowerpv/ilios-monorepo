import logging

from fastapi import APIRouter, BackgroundTasks, Depends, status

from src.deployment.fast_api.auth import api_key_check
from src.deployment.fast_api.models.input import FileUploadInput
from src.deployment.fast_api.models.output import SimpleResponse
from src.deployment.fast_api.settings import settings
from src.pipelines.file_enrichment.pipeline import FileEnrichmentPipeline
from src.vectordb.pg_vector.connector import PGVectorConnector


file_processing_router = APIRouter(tags=["process_file"], prefix="/process_file")
logger = logging.getLogger(__name__)


def file_processing_background_task(upload_input: FileUploadInput) -> None:
    """Background task to process the file and store it in the Vector Database."""
    pipeline = FileEnrichmentPipeline()
    logger.info(f"Processing file: {upload_input.file_link}")
    file_data = pipeline.run(metadata=upload_input.model_dump())
    logger.info(f"Creating Document: {upload_input.file_link}")
    logger.info(f"Storing Document in PGVector: {upload_input.file_link}")
    pg_connector = PGVectorConnector(config=settings.get_pg_vector_config())
    pg_connector.store_documents(file_data)
    logger.info(f"Pipeline complete: {upload_input.file_link}")


@file_processing_router.post(
    "/upload_file", response_model=SimpleResponse, dependencies=[Depends(api_key_check)]
)
async def upload_file(
    upload_input: FileUploadInput, background_task: BackgroundTasks
) -> SimpleResponse:
    """
    Enrich and upload the file to the Vector Database.
    """
    logger.info(f"Uploading file. Accepted payload: {upload_input.model_dump()}")
    try:
        background_task.add_task(file_processing_background_task, upload_input)
    except Exception:
        return SimpleResponse(
            message="Failed to upload the file",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return SimpleResponse(
        message="File uploaded successfully", status=status.HTTP_200_OK
    )


@file_processing_router.post(
    "/delete_file", response_model=SimpleResponse, dependencies=[Depends(api_key_check)]
)
async def delete_file(file_id: int) -> SimpleResponse:
    """Delete the file from the Vector Database."""
    logger.info(f"Deleting file: {file_id}")
    try:
        pg_connector = PGVectorConnector(config=settings.get_pg_vector_config())
        pg_connector.delete_document(file_id)
    except Exception as e:
        return SimpleResponse(
            message=f"Failed to delete file {file_id}: Error: {e}",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return SimpleResponse(
        message=f"File {file_id} deleted successfully.", status=status.HTTP_200_OK
    )


@file_processing_router.post(
    "/mark_actual", response_model=SimpleResponse, dependencies=[Depends(api_key_check)]
)
async def mark_actual(file_id: int, actual: bool) -> SimpleResponse:
    """
    Mark the file as actual or not actual.
    """
    logger.info(f"Marking file: {file_id} as actual: {actual}")
    try:
        pg_connector = PGVectorConnector(config=settings.get_pg_vector_config())
        pg_connector.mark_actual(file_id, actual)
    except Exception as e:
        return SimpleResponse(
            message=f"Failed to mark file {file_id} as actual with status: {actual}: "
            f"Error: {e}",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return SimpleResponse(
        message=f"File {file_id} updated successfully with status: {actual}",
        status=status.HTTP_200_OK,
    )
