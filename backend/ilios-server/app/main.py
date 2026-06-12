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
from app.middlewares.security_headers import SecurityHeadersMiddleware

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
    om_glossary_router,
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
    auth_security_events_router,
    global_admin_router,
    role_profiles_router,
    extraction_registry_router,
    reconciliation_router,
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


PROD_LIKE_ENV_NAMES = {"production", "prod", "staging", "stage", "live"}


def _is_production() -> bool:
    return (settings.environment_name or "").strip().lower() in PROD_LIKE_ENV_NAMES


def _resolve_cors_origins() -> list[str]:
    """Resolve allowed CORS origins from CORS_ALLOWED_ORIGINS env var.

    - If CORS_ALLOWED_ORIGINS is set, use the comma-separated list verbatim.
    - Otherwise default to safe values per environment:
        prod  -> https://app.iliospower.com plus the public Replit deploy URL.
        dev   -> common local origins plus REPLIT_DEV_DOMAIN if present.
    """
    raw = (os.environ.get("CORS_ALLOWED_ORIGINS") or "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]

    if _is_production():
        return [
            "https://app.iliospower.com",
            "https://ilios-monorepo.replit.app",
        ]

    dev_origins = [
        "http://localhost:5000",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:3000",
    ]
    replit_dev = os.environ.get("REPLIT_DEV_DOMAIN")
    if replit_dev:
        dev_origins.append(f"https://{replit_dev}")
    return dev_origins


def _validate_configuration():
    """Validate critical configuration at startup."""
    logger.info(f"Storage provider: {settings.storage_provider}")
    logger.info(f"Registry fallback: {settings.allow_config_fallback}")

    if settings.storage_provider.lower() == "replit":
        bucket_id = os.environ.get("DEFAULT_OBJECT_STORAGE_BUCKET_ID")
        if bucket_id:
            logger.info(f"Replit Object Storage bucket: {bucket_id[:20]}...")
        else:
            logger.warning("Replit storage enabled but DEFAULT_OBJECT_STORAGE_BUCKET_ID not set")

    openai_api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    openai_base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
    if openai_api_key and openai_base_url:
        logger.info("In-app AI parsing configured via Replit AI Integrations (OpenAI)")
    else:
        logger.warning(
            "AI parsing not configured. Install OpenAI integration via Replit AI Integrations "
            "to enable document parsing."
        )

    # Production-mode safety checks
    env_name = (settings.environment_name or "unknown").strip().lower()
    is_prod = env_name in PROD_LIKE_ENV_NAMES
    logger.info("=" * 60)
    logger.info(f"Environment: {env_name} (production_mode={is_prod})")

    if is_prod:
        # Hard-fail: demo telemetry in prod would silently feed fake data to real users.
        demo_telemetry = (os.environ.get("DEMO_TELEMETRY") or "").strip().lower()
        if demo_telemetry in {"1", "true", "yes", "on"}:
            raise RuntimeError(
                "PRODUCTION SAFETY: DEMO_TELEMETRY is enabled in a production environment. "
                "Refusing to start. Unset DEMO_TELEMETRY in the production env scope."
            )

        # Flag any other demo-mode env vars we know about.
        for flag in ("DEMO_MODE", "USE_DEMO_DATA", "ENABLE_DEMO"):
            val = (os.environ.get(flag) or "").strip().lower()
            if val in {"1", "true", "yes", "on"}:
                raise RuntimeError(
                    f"PRODUCTION SAFETY: {flag} is enabled in a production environment. "
                    f"Refusing to start. Unset {flag} in the production env scope."
                )

        # Telemetry credential backend.
        #
        # The selected backend is decided once by credential_store at import
        # time, so we ask it directly rather than re-deriving the rule here.
        # Two modes:
        #   - telemetry_v2_enabled == True  -> in-memory is a HARD FAIL.
        #   - telemetry_v2_enabled == False -> in-memory boots with a loud
        #     warning, and the v2 credential write/test routes are blocked
        #     server-side (see require_durable_credential_store).
        from app.integrations.telemetry.credential_store import (
            is_credential_store_durable,
        )

        durable = is_credential_store_durable()
        v2_enabled = bool(getattr(settings, "telemetry_v2_enabled", False))
        if not durable:
            if v2_enabled:
                raise RuntimeError(
                    "PRODUCTION SAFETY: telemetry_v2_enabled=true but the "
                    "telemetry V2 credential store is in-memory. Refusing to "
                    "start. Configure a durable backend by setting "
                    "GOOGLE_APPLICATION_CREDENTIALS_JSON (preferred) or "
                    "service_account_key_file_path, then redeploy. To boot "
                    "without telemetry V2, set telemetry_v2_enabled=false."
                )
            logger.warning("=" * 60)
            logger.warning(
                "PRODUCTION WARNING: Telemetry V2 credentials will use the "
                "IN-MEMORY backend. telemetry_v2_enabled is false, so the "
                "credential save/test routes will return 503 until a durable "
                "backend is configured. See docs/RUNBOOK.md §11."
            )
            logger.warning("=" * 60)
        else:
            logger.info("Telemetry V2 credential backend: durable (GCP)")

        logger.info("Production safety checks: PASSED")
    else:
        logger.info("Non-production environment; production safety checks skipped.")
    logger.info("=" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: U100
    _validate_configuration()
    db = next(get_session())
    AppInitHelper(db).set_predefined_data()

    # Native V2 telemetry scheduler (Task #38). Started only behind the gate
    # (flag + telemetry_v2_enabled + non-prod-or-durable store); a daemon thread
    # bridges the synchronous ingestion/rollup services. Stopped gracefully after
    # yield so an in-flight run can release its DB lease.
    scheduler_runner = None
    try:
        from app.services.telemetry.scheduler_runner import (
            TelemetrySchedulerRunner,
            scheduler_should_run,
            scheduler_topology_warnings,
        )

        # Surface production-topology advisories (Reserved VM requirement, prod
        # without a durable store) whenever the scheduler is enabled, regardless
        # of whether it actually starts. Logged at WARNING so ops notice; never
        # blocks startup.
        for warning in scheduler_topology_warnings():
            logger.warning("Telemetry scheduler topology: %s", warning)

        should_run, reason = scheduler_should_run()
        if should_run:
            scheduler_runner = TelemetrySchedulerRunner()
            scheduler_runner.start()
        else:
            logger.info("Telemetry scheduler not started: %s", reason)
    except Exception:  # noqa: BLE001 — scheduler must never block app startup
        logger.exception("Telemetry scheduler failed to start")

    try:
        yield
    finally:
        if scheduler_runner is not None:
            try:
                scheduler_runner.stop()
            except Exception:  # noqa: BLE001
                logger.exception("Telemetry scheduler failed to stop cleanly")


def ilios_api() -> FastAPI:  # noqa: CFQ001
    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=__version__,
        docs_url="/docs",
        lifespan=lifespan,
        responses=HTTP_422_RESPONSE,
    )
    cors_origins = _resolve_cors_origins()
    logger.info(f"CORS allowed origins: {cors_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        # Retry-After is not a CORS-safelisted response header, so it must be
        # explicitly exposed for the browser to read it on a 429 (manual
        # telemetry refresh/backfill cooldown) and drive the UI countdown.
        expose_headers=["Retry-After"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
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
        om_glossary_router, prefix="/api/operations-and-maintenance/glossary", tags=[tags.OM_SITES_TAG]
    )
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
    app.include_router(reconciliation_router, prefix="/api/due-diligence/sites/{site_id}", tags=[tags.DOCUMENTS_TAG])
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
    app.include_router(
        auth_security_events_router,
        prefix="/api/admin/auth-security-events",
        tags=["Admin - Auth Security"],
    )
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
