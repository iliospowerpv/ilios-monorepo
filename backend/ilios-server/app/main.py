import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
    auth_router,
    board_router,
    board_statuses_router,
    breadcrumbs_router,
    cameras_router,
    chatbot_router,
    co_terminus_router,
    comments_router,
    companies_router,
    dashboard_notifications_router,
    dashboard_tasks_router,
    device_documents_router,
    devices_router,
    documents_router,
    files_parsing_router,
    files_router,
    finance_actuals_router,
    finance_budgets_router,
    finance_data_router,
    finance_integrations_router,
    finance_obligations_router,
    finance_portfolio_router,
    finance_vendors_router,
    health_router,
    internal_ai_router,
    internal_router,
    internal_sites_router,
    investor_companies_router,
    om_companies_router,
    om_site_cameras_router,
    om_sites_router,
    performance_report_router,
    reports_companies_router,
    reports_router,
    reports_sites_router,
    sales_router,
    site_visits_router,
    project_import_router,
    sites_router,
    sv_uploads_router,
    tasks_router,
    workspace_router,
    access_health_router,
    global_admin_router,
    role_profiles_router,
    extraction_registry_router,
    summary_stats_router,
    contacts_router,
    entities_router,
    users_router,
)
from .routers.project_assumptions import assumptions_router
from .routers.debug import router as debug_router
from .routers.internal.base import internal_telemetry_router
from .routers.investor_dashboard import investor_sites_router
from .routers.telemetry import telemetry_router, telemetry_v2_router
from .security.redaction import configure_redaction
from .settings import settings
from .static import HTTP_422_RESPONSE, tags
from .utils import http_500_exception_handler, http_exception_handler, validation_exception_handler

# logging.basicConfig(level=logging.DEBUG,
logging.basicConfig(
    level=settings.log_level,
    # specify logging format for the gunicorn
    format="%(levelname)s::%(name)s::%(message)s",
)
configure_redaction()


logger = logging.getLogger(__name__)


def _validate_configuration():
    """Validate critical configuration at startup."""
    logger.info(f"Storage provider: {settings.storage_provider}")
    logger.info(f"Registry fallback: {settings.allow_config_fallback}")

    if settings.storage_provider.lower() == "replit":
        import os
        bucket_id = os.environ.get("DEFAULT_OBJECT_STORAGE_BUCKET_ID")
        if bucket_id:
            logger.info(f"Replit Object Storage bucket: {bucket_id[:20]}...")
        else:
            logger.warning("Replit storage enabled but DEFAULT_OBJECT_STORAGE_BUCKET_ID not set")

    import os
    openai_api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    openai_base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    if openai_api_key and openai_base_url:
        logger.info("In-app AI parsing configured via Replit AI Integrations (OpenAI)")
    else:
        logger.warning(
            "AI parsing not configured. Install OpenAI integration via Replit AI Integrations "
            "to enable document parsing."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: U100
    _validate_configuration()
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
    app.include_router(users_router, prefix="/api/users", tags=[tags.USERS_TAG])
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
    app.include_router(project_import_router, prefix="/api/projects/import", tags=[tags.SITES_TAG])
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
    # workspace APIs
    app.include_router(workspace_router, prefix="/api/workspace", tags=[tags.WORKSPACE_TAG])
    # role profiles API
    app.include_router(role_profiles_router, prefix="/api/role-profiles", tags=[tags.ROLES_TAG])
    # contacts API (CRM-style address book at portfolio/company/project levels)
    app.include_router(contacts_router, prefix="/api/contacts", tags=["Contacts"])
    # due diligence related APIs
    app.include_router(documents_router, prefix="/api/due-diligence/{site_id}/documents", tags=[tags.DOCUMENTS_TAG])
    app.include_router(agreements_router, prefix="/api/due-diligence/{site_id}/agreements", tags=[tags.DOCUMENTS_TAG])
    app.include_router(co_terminus_router, prefix="/api/due-diligence/{site_id}/co-terminus", tags=[tags.DOCUMENTS_TAG])
    app.include_router(summary_stats_router, prefix="/api/due-diligence/sites/{site_id}", tags=[tags.DOCUMENTS_TAG])
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
    app.include_router(assumptions_router, prefix="/api/projects/{site_id}/assumptions", tags=["Project Assumptions"])
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
    app.include_router(telemetry_v2_router, prefix="/api/telemetry", tags=[tags.TELEMETRY_TAG])
    # reports related APIs
    app.include_router(reports_companies_router, prefix="/api/reporting/companies", tags=[tags.REPORTING_TAG])
    app.include_router(
        reports_sites_router, prefix="/api/reporting/companies/{company_id}/sites", tags=[tags.REPORTING_TAG]
    )
    app.include_router(reports_router, prefix="/api/reporting/reports", tags=[tags.REPORTING_TAG])
    app.include_router(performance_report_router, prefix="/api/reporting/sites", tags=[tags.REPORTING_TAG])
    # finance related APIs
    app.include_router(
        finance_vendors_router,
        prefix="/api/finance/companies/{company_id}/vendors",
        tags=[tags.FINANCE_VENDORS_TAG],
    )
    app.include_router(
        finance_budgets_router,
        prefix="/api/finance/companies/{company_id}/budgets",
        tags=[tags.FINANCE_BUDGETS_TAG],
    )
    app.include_router(
        finance_obligations_router,
        prefix="/api/finance/companies/{company_id}/obligations",
        tags=[tags.FINANCE_OBLIGATIONS_TAG],
    )
    app.include_router(
        finance_actuals_router,
        prefix="/api/finance/companies/{company_id}/actuals",
        tags=[tags.FINANCE_ACTUALS_TAG],
    )
    app.include_router(
        finance_portfolio_router,
        prefix="/api/finance/companies/{company_id}/portfolio",
        tags=[tags.FINANCE_PORTFOLIO_TAG],
    )
    # finance integration configuration APIs
    app.include_router(
        finance_integrations_router,
        prefix="/api",
        tags=["Finance Integrations"],
    )
    # finance data read-only endpoints (accounts, transactions, sync-runs)
    app.include_router(
        finance_data_router,
        prefix="/api/finance",
        tags=["Finance Data"],
    )
    # internal APIs
    app.include_router(internal_router, prefix="/api/internal", tags=[tags.INTERNAL_TAG])
    app.include_router(internal_ai_router, prefix="/api/internal", tags=[tags.INTERNAL_AI_TAG])
    app.include_router(internal_telemetry_router, prefix="/api/internal", tags=[tags.INTERNAL_TELEMETRY_TAG])
    app.include_router(internal_sites_router, prefix="/api/internal", tags=[tags.INTERNAL_SITES_TAG])
    # Breadcrumbs related APIs
    app.include_router(breadcrumbs_router, prefix="/api/breadcrumbs", tags=[tags.BREADCRUMBS_TAG])
    # Sales related APIs
    app.include_router(sales_router)
    app.include_router(entities_router)
    # Admin APIs
    app.include_router(access_health_router, prefix="/api/admin/access-health", tags=[tags.ADMIN_ACCESS_HEALTH_TAG])
    app.include_router(extraction_registry_router, prefix="/api/admin/extraction", tags=["Admin - Extraction Registry"])
    app.include_router(global_admin_router, prefix="/api/admin/global-admins", tags=["Admin - Global Admins"])
    # Debug APIs (admin-only)
    app.include_router(debug_router, prefix="/api")

    # ------------------------------------------------------------------
    # Serve the built React frontend from the same origin.
    #
    # In production the deployment runs only the FastAPI backend; the
    # frontend's compiled `build/` directory is served from here so that
    # the browser sees one origin (no CORS, no proxy). All API/docs
    # routes registered above keep precedence over the SPA catch-all
    # because they are explicit routes registered first.
    # ------------------------------------------------------------------
    frontend_build_dir = os.environ.get(
        "FRONTEND_BUILD_DIR",
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "rea-investment-fe", "build")
        ),
    )
    index_file = os.path.join(frontend_build_dir, "index.html")
    # Only enable SPA serving when an actual React build exists. The
    # dev workflow runs the frontend on its own port via npm start, so
    # in dev there is typically no index.html here and we skip mounting.
    if os.path.isfile(index_file):
        static_dir = os.path.join(frontend_build_dir, "static")
        if os.path.isdir(static_dir):
            app.mount("/static", StaticFiles(directory=static_dir), name="frontend-static")

        build_root = os.path.abspath(frontend_build_dir)

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):  # noqa: U100
            # API/docs routes are matched before this catch-all because
            # they are registered earlier with explicit paths. Anything
            # reaching here is a frontend asset or a client-side route.
            if full_path:
                candidate = os.path.normpath(os.path.join(build_root, full_path))
                # Prevent path traversal: candidate must stay inside build dir
                if candidate.startswith(build_root + os.sep) and os.path.isfile(candidate):
                    return FileResponse(candidate)
            return FileResponse(index_file)

        logger.info(f"Serving frontend SPA from {build_root}")
    else:
        logger.info(
            f"Frontend index.html not found at {index_file}; SPA serving disabled (dev mode — frontend served by npm start)"
        )

    return app


app = application = api = ilios_api()
