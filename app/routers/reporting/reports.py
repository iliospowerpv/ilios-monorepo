import io
import logging

from fastapi import APIRouter, Body, Depends, responses

from app.helpers.authorization import AuthorizedUser
from app.helpers.authorization.module_based.reporting import ReportingPermissions
from app.helpers.powerbi import PowerBIHandler
from app.schema.reports import ReportEmbedTokenSchema, ReportsPaginator
from app.static import PermissionsActions

logger = logging.getLogger(__name__)
reports_router = APIRouter()


@reports_router.get(
    "",
    response_model=ReportsPaginator,
    description="Get all available reports for the platform.",
    dependencies=[Depends(AuthorizedUser(ReportingPermissions(PermissionsActions.view)))],
)
async def get_reports_list():
    return {"items": PowerBIHandler().list_reports()}


@reports_router.get(
    "/{report_id}/generate-embedding-token",
    response_model=ReportEmbedTokenSchema,
    description="Generate embedding token for the specific report",
    dependencies=[Depends(AuthorizedUser(ReportingPermissions(PermissionsActions.view)))],
)
async def generate_report_embedding_token(report_id: str):
    token = PowerBIHandler().generate_embed_token(report_id)
    return {"embed_token": token}


@reports_router.get(
    "/{report_id}/pages",
    description="Proxy: get report pages.",
    dependencies=[Depends(AuthorizedUser(ReportingPermissions(PermissionsActions.view)))],
)
async def retrieve_report_pages(report_id: str):
    return PowerBIHandler().get_report_pages(report_id)


@reports_router.post(
    "/{report_id}/export-to-file",
    description="Proxy: export report to file. Please, note: the `format` parameter is required.",
    dependencies=[Depends(AuthorizedUser(ReportingPermissions(PermissionsActions.view)))],
)
async def export_report_to_file(report_id: str, export_params: dict = Body({"format": "PDF"})):
    return PowerBIHandler().export_report_to_file(report_id, export_params)


@reports_router.get(
    "/{report_id}/exports/{export_id}/status",
    description="Proxy: get export status.",
    dependencies=[Depends(AuthorizedUser(ReportingPermissions(PermissionsActions.view)))],
)
async def get_export_report_status(report_id: str, export_id: str):
    return PowerBIHandler().get_export_status(report_id, export_id)


@reports_router.get(
    "/{report_id}/exports/{export_id}/file",
    description="Proxy: get export file, return streaming file response with corresponding content type.",
    dependencies=[Depends(AuthorizedUser(ReportingPermissions(PermissionsActions.view)))],
)
async def get_export_report_file_content(report_id: str, export_id: str):
    file_content, content_type = PowerBIHandler().get_export_file(report_id, export_id)
    # TODO experiment with different media types: "application/octet-stream" proved to return a file,
    #  but need to align with FE
    return responses.StreamingResponse(io.BytesIO(file_content), media_type=content_type)
