import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware

from app.db.session import get_session
from app.helpers.initial_setup_helper import AppInitHelper
from app.middlewares.logging_middleware import RequestsLoggerMiddleware

from . import __version__
from .middlewares.audit_middleware import AuditingMiddleware
from .routers import (
    account_router,
    agreements_router,
    alerts_router,
    attachments_router,
    audit_log_router,
    auth_router,
    board_router,
    board_statuses_router,
    breadcrumbs_router,
    cameras_router,
    chatbot_router,
    co_terminus_router,
    comments_router,
    companies_router,
    contractors_router,
    dashboard_notifications_router,
    dashboard_tasks_router,
    device_documents_router,
    devices_router,
    documents_router,
    files_parsing_router,
    files_router,
    health_router,
    internal_ai_router,
    internal_router,
    internal_sites_router,
    investor_companies_router,
    my_company_router,
    om_companies_router,
    om_site_cameras_router,
    om_sites_router,
    reports_companies_router,
    reports_router,
    reports_sites_router,
    roles_router,
    settings_connections_router,
    settings_sites_router,
    site_visits_router,
    sites_router,
    sv_uploads_router,
    tasks_router,
    users_router,
)
from .routers.internal.base import internal_telemetry_router
from .routers.investor_dashboard import investor_sites_router
from .routers.telemetry import telemetry_router
from .settings import settings
from .static import HTTP_422_RESPONSE, tags
from .utils import http_500_exception_handler, http_exception_handler, validation_exception_handler

# logging.basicConfig(level=logging.DEBUG,
logging.basicConfig(
    level=settings.log_level,
    # specify logging format for the gunicorn
    format="%(levelname)s::%(name)s::%(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: U100
    db = next(get_session())
    AppInitHelper(db).set_predefined_data()
    yield


def ilios_api() -> FastAPI:  # noqa: CFQ001
    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=__version__,
        docs_url="/docs",
        lifespan=lifespan,
        responses=HTTP_422_RESPONSE,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestsLoggerMiddleware)
    app.add_middleware(AuditingMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, http_500_exception_handler)
    app.include_router(health_router)
    # authorization related APIs
    app.include_router(auth_router, prefix="/api/auth", tags=[tags.AUTH_TAG])
    # account related APIs
    app.include_router(account_router, prefix="/api/users/account", tags=[tags.ACCOUNT_USER_TAG])
    app.include_router(dashboard_tasks_router, prefix="/api/account/dashboard", tags=[tags.ACCOUNT_DASHBOARD_TAG])
    app.include_router(
        dashboard_notifications_router, prefix="/api/account/dashboard/notifications", tags=[tags.ACCOUNT_DASHBOARD_TAG]
    )
    # investor dashboard
    app.include_router(
        investor_companies_router, prefix="/api/investor-dashboard/companies", tags=[tags.INVESTOR_DASHBOARD_TAG]
    )
    app.include_router(investor_sites_router, prefix="/api/investor-dashboard/sites", tags=[tags.INVESTOR_DASHBOARD_TAG])
    # assets management related APIs
    app.include_router(companies_router, prefix="/api/companies", tags=[tags.COMPANIES_TAG])
    app.include_router(sites_router, prefix="/api/sites", tags=[tags.SITES_TAG])
    app.include_router(devices_router, prefix="/api/sites/{site_id}/devices", tags=[tags.DEVICES_TAG])
    app.include_router(
        device_documents_router,
        prefix="/api/sites/{site_id}/devices/{device_id}/documents",
        tags=[tags.DEVICE_DOCUMENTS_TAG],
    )
    # O&M related APIs
    app.include_router(alerts_router, prefix="/api/operations-and-maintenance/alerts", tags=[tags.ALERTS_TAG])
    app.include_router(
        om_companies_router, prefix="/api/operations-and-maintenance/companies", tags=[tags.OM_COMPANIES_TAG]
    )
    app.include_router(om_sites_router, prefix="/api/operations-and-maintenance/sites", tags=[tags.OM_SITES_TAG])
    app.include_router(
        om_site_cameras_router,
        prefix="/api/operations-and-maintenance/sites/{site_id}/cameras",
        tags=[tags.OM_SITE_CAMERAS_TAG],
    )
    # settings related APIs
    app.include_router(audit_log_router, prefix="/api/settings/audit-logs", tags=[tags.AUDIT_LOG_TAG])
    app.include_router(contractors_router, prefix="/api/contractors", tags=[tags.CONTRACTORS_TAG])
    app.include_router(
        settings_connections_router,
        prefix="/api/contractors/{company_id}/connections",
        tags=[tags.SETTINGS_CONNECTIONS_TAG],
    )
    app.include_router(my_company_router, prefix="/api/my-company", tags=[tags.MY_COMPANY_TAG])
    app.include_router(roles_router, prefix="/api/roles", tags=[tags.ROLES_TAG])
    app.include_router(settings_sites_router, prefix="/api/settings/sites", tags=[tags.SETTINGS_SITES_TAG])
    app.include_router(users_router, prefix="/api/users", tags=[tags.USERS_TAG])
    # due diligence related APIs
    app.include_router(documents_router, prefix="/api/due-diligence/{site_id}/documents", tags=[tags.DOCUMENTS_TAG])
    app.include_router(agreements_router, prefix="/api/due-diligence/{site_id}/agreements", tags=[tags.DOCUMENTS_TAG])
    app.include_router(co_terminus_router, prefix="/api/due-diligence/{site_id}/co-terminus", tags=[tags.DOCUMENTS_TAG])
    app.include_router(
        files_router, prefix="/api/due-diligence/{site_id}/documents/{document_id}/files", tags=[tags.FILES_TAG]
    )
    # TODO add file_id to this path and remove it from router module
    app.include_router(
        files_parsing_router,
        prefix="/api/due-diligence/{site_id}/documents/{document_id}/files/{file_id}",
        tags=[tags.FILES_PARSING_TAG],
    )
    app.include_router(chatbot_router, prefix="/api/due-diligence/chatbot/{site_id}", tags=[tags.CHATBOT_TAG])
    # task tracker related APIs
    app.include_router(board_router, prefix="/api/task-tracker/boards", tags=[tags.BOARD_TAG])
    app.include_router(
        board_statuses_router, prefix="/api/task-tracker/boards/{board_id}/statuses", tags=[tags.BOARD_STATUSES_TAG]
    )
    app.include_router(tasks_router, prefix="/api/task-tracker/boards/{board_id}/tasks", tags=[tags.BOARD_TASKS_TAG])
    app.include_router(
        attachments_router,
        prefix="/api/task-tracker/boards/{board_id}/tasks/{task_id}/attachments",
        tags=[tags.ATTACHMENTS_TAG],
    )
    app.include_router(
        site_visits_router,
        prefix="/api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits",
        tags=[tags.SITE_VISITS_TAG],
    )
    app.include_router(
        sv_uploads_router,
        prefix="/api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits",
        tags=[tags.SITE_VISITS_UPLOADS_TAG],
    )
    # comments related APIs
    app.include_router(comments_router, prefix="/api/comments", tags=[tags.COMMENTS_TAG])
    # security related APIs
    app.include_router(cameras_router, prefix="/api/security/cameras", tags=[tags.CAMERAS_TAG])
    # telemetry related APIs
    app.include_router(telemetry_router, prefix="/api/telemetry", tags=[tags.TELEMETRY_TAG])
    # reports related APIs
    app.include_router(reports_companies_router, prefix="/api/reporting/companies", tags=[tags.REPORTING_TAG])
    app.include_router(
        reports_sites_router, prefix="/api/reporting/companies/{company_id}/sites", tags=[tags.REPORTING_TAG]
    )
    app.include_router(reports_router, prefix="/api/reporting/reports", tags=[tags.REPORTING_TAG])
    # internal APIs
    app.include_router(internal_router, prefix="/api/internal", tags=[tags.INTERNAL_TAG])
    app.include_router(internal_ai_router, prefix="/api/internal", tags=[tags.INTERNAL_AI_TAG])
    app.include_router(internal_telemetry_router, prefix="/api/internal", tags=[tags.INTERNAL_TELEMETRY_TAG])
    app.include_router(internal_sites_router, prefix="/api/internal", tags=[tags.INTERNAL_SITES_TAG])
    # Breadcrumbs related APIs
    app.include_router(breadcrumbs_router, prefix="/api/breadcrumbs", tags=[tags.BREADCRUMBS_TAG])
    return app


app = application = api = ilios_api()
