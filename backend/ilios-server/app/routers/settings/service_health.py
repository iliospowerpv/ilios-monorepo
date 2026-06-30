"""Third-Party Services status dashboard API (superuser-only).

Reports, for each external/infra service the app integrates with:

- whether it is **configured** (presence of the relevant env vars / settings —
  NAMES only, values are never read or returned),
- whether it is **reachable** for the small set of cheap, side-effect-free infra
  probes we can run safely (Postgres, Redis, Object Storage). For external,
  authenticated or billable providers we report configuration status only and
  leave ``reachable=None`` ("Not probed") — we never fabricate a reachability
  result.

Hard rules:
- No secret values are ever returned (only the env/setting *names*).
- No fake checks: ``reachable`` is ``True``/``False`` only when an actual probe
  ran; otherwise it stays ``None``.
- A single failing probe never breaks the dashboard (each probe is isolated and
  time-boxed).
"""

import concurrent.futures
import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Callable, List, Optional, Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authorization.module_based.base import get_current_admin_user
from app.redis_cache.cache import check_redis_health
from app.schema.user import CurrentUserSchema
from app.settings import settings

service_health_router = APIRouter()
logger = logging.getLogger(__name__)

_PROBE_TIMEOUT_SECONDS = 3.0
# Strip credentials embedded in DSN/URL forms from any error message we surface.
_SECRET_IN_URL = re.compile(r"(://[^:/@\s]+:)[^@\s]+(@)")
# Mask `key=value` / `key: value` style secrets (keep the key name, drop the value).
_SECRET_KV = re.compile(
    r"(?i)(\b(?:api[_-]?key|secret|token|password|passwd|authorization|auth"
    r"|access[_-]?key|client[_-]?secret)\b\s*[:=]\s*)\S+"
)
# Mask `Bearer <token>` authorization headers.
_BEARER = re.compile(r"(?i)(bearer\s+)\S+")

ProbeResult = Tuple[bool, Optional[str]]


def _redact(message: Optional[str]) -> Optional[str]:
    """Redact embedded credentials and bound the length of probe error text.

    Masks DSN/URL-embedded passwords, ``key=value`` / ``key: value`` style secrets
    (api_key, token, secret, password, authorization, client_secret, ...) and
    ``Bearer <token>`` headers. This is best-effort defence-in-depth for *server
    logs*; the values returned to clients are fixed generic strings that never
    include probe detail at all.
    """
    if not message:
        return message
    redacted = _SECRET_IN_URL.sub(r"\1***\2", str(message))
    # Bearer first: it must mask the token before _SECRET_KV collapses the
    # "Authorization: Bearer" prefix and orphans the token after it.
    redacted = _BEARER.sub(r"\1***", redacted)
    redacted = _SECRET_KV.sub(r"\1***", redacted)
    if len(redacted) > 300:
        redacted = redacted[:300] + "…"
    return redacted


class ServiceStatus(BaseModel):
    key: str
    name: str
    purpose: str
    category: str
    required: bool
    configured: bool
    config_source: List[str]
    reachable: Optional[bool] = None  # None => not probed (honest "Not probed")
    last_checked: Optional[datetime] = None
    error_summary: Optional[str] = None
    notes: Optional[str] = None


class ServiceHealthResponse(BaseModel):
    services: List[ServiceStatus]
    generated_at: datetime
    total_count: int
    configured_count: int
    probed_count: int


def _run_with_timeout(label: str, fn: Callable[[], ProbeResult], timeout: Optional[float] = None) -> ProbeResult:
    """Run a probe in a worker thread, time-boxed and exception-isolated.

    The probe's own error detail is only ever logged server-side (after credential
    redaction); the value returned to the client is a fixed, secret-free message, so
    no provider exception text (which may embed tokens, headers or DSNs) can leak
    into the API response. On timeout the worker thread is abandoned without waiting
    so a wedged probe can never hang the request beyond ``timeout``.
    """
    if timeout is None:
        timeout = _PROBE_TIMEOUT_SECONDS
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        ok, detail = future.result(timeout=timeout)
        if not ok:
            logger.warning("Service probe %s reported unhealthy: %s", label, _redact(detail))
            return False, f"{label} is configured but not reachable."
        return True, None
    except concurrent.futures.TimeoutError:
        logger.warning("Service probe %s timed out after %.0fs", label, timeout)
        return False, f"Probe timed out after {timeout:.0f}s."
    except Exception as exc:  # noqa: BLE001 - any probe failure is reported, never raised
        logger.warning("Service probe %s errored: %s", label, _redact(str(exc)))
        return False, f"{label} probe failed (see server logs)."
    finally:
        # Never block on a hung probe thread; reclaim it in the background so the
        # request always returns within ``timeout``.
        executor.shutdown(wait=False, cancel_futures=True)


# ---------------------------------------------------------------------------
# Probes (cheap, read-only / side-effect-free only)
# ---------------------------------------------------------------------------
def _probe_redis() -> ProbeResult:
    result = check_redis_health()
    if result.get("status") == "healthy":
        return True, None
    return False, _redact(result.get("message"))


def _probe_storage() -> ProbeResult:
    # exists() is a read-only lookup; a reachable backend returns a bool without
    # raising. A misconfigured / unreachable backend raises, which we capture.
    from app.helpers.files.storage_service import get_storage_service

    get_storage_service().exists("__ilios_health_probe__/__does_not_exist__")
    return True, None


def _bucket_id() -> Optional[str]:
    return os.environ.get("DEFAULT_OBJECT_STORAGE_BUCKET_ID")


def _build_services(db_session: Session) -> List[ServiceStatus]:
    now = datetime.now(timezone.utc)
    services: List[ServiceStatus] = []

    # --- Postgres (required) -- probed inline (uses request-scoped session) ----
    db_reachable: Optional[bool] = None
    db_error: Optional[str] = None
    try:
        # Bound the probe so a wedged DB cannot hang the dashboard, and never
        # surface raw driver error text (it can embed connection credentials).
        db_session.execute(text("SET LOCAL statement_timeout = '3s'"))
        db_session.execute(text("SELECT 1"))
        db_reachable = True
    except Exception as exc:  # noqa: BLE001
        db_reachable = False
        db_error = "Database probe failed (see server logs)."
        logger.warning("Service probe PostgreSQL failed: %s", _redact(str(exc)))
    finally:
        # Reset statement_timeout / clear any aborted transaction state on the
        # request-scoped session.
        try:
            db_session.rollback()
        except Exception:  # noqa: BLE001
            pass
    services.append(
        ServiceStatus(
            key="postgres",
            name="PostgreSQL Database",
            purpose="Primary relational datastore for the entire application.",
            category="Infrastructure",
            required=True,
            configured=bool(getattr(settings, "db_dsn", None)),
            config_source=["DATABASE_URL", "PGHOST", "PGUSER", "PGPASSWORD", "PGDATABASE", "db_dsn"],
            reachable=db_reachable,
            last_checked=now,
            error_summary=db_error,
        )
    )

    # --- Redis (optional) -- probed ------------------------------------------
    try:
        redis_configured = bool(settings.redis_connection_string)
    except Exception:  # noqa: BLE001 - missing config must read as "not configured", not crash
        redis_configured = False
    redis_reachable: Optional[bool] = None
    redis_error: Optional[str] = None
    if redis_configured:
        redis_reachable, redis_error = _run_with_timeout("Redis", _probe_redis)
    services.append(
        ServiceStatus(
            key="redis",
            name="Redis Cache",
            purpose="Caching and rate-limit / session counters.",
            category="Infrastructure",
            required=False,
            configured=redis_configured,
            config_source=["REDIS_URL", "REDIS_CONNECTION_URL"],
            reachable=redis_reachable,
            last_checked=now if redis_configured else None,
            error_summary=redis_error,
            notes=None if redis_configured else "Not configured — caching falls back to no-op.",
        )
    )

    # --- Object Storage (required) -- probed ---------------------------------
    provider = settings.storage_provider
    if provider == "gcs":
        storage_configured = bool(settings.due_diligence_gcs_bucket or settings.service_account_key_file_path)
        storage_sources = [
            "storage_provider",
            "service_account_key_file_path",
            "due_diligence_gcs_bucket",
            "task_attachments_gcs_bucket",
            "device_documents_gcs_bucket",
            "sv_uploads_gcs_bucket",
        ]
    else:
        storage_configured = bool(_bucket_id())
        storage_sources = ["storage_provider", "DEFAULT_OBJECT_STORAGE_BUCKET_ID"]
    storage_reachable: Optional[bool] = None
    storage_error: Optional[str] = None
    if storage_configured:
        storage_reachable, storage_error = _run_with_timeout("Object storage", _probe_storage)
    services.append(
        ServiceStatus(
            key="object_storage",
            name="Object Storage (Files)",
            purpose="Stores uploaded documents, attachments and site-visit media.",
            category="Infrastructure",
            required=True,
            configured=storage_configured,
            config_source=storage_sources,
            reachable=storage_reachable,
            last_checked=now if storage_configured else None,
            error_summary=storage_error,
            notes=f"Provider: {provider}.",
        )
    )

    # --- Mailgun email (optional) -- configuration only ----------------------
    services.append(
        ServiceStatus(
            key="mailgun",
            name="Mailgun (Email)",
            purpose="Transactional email: invitations and password resets.",
            category="External API",
            required=False,
            configured=bool(
                settings.mailgun_api_key and settings.mailgun_domain_name and settings.mailgun_rest_api_endpoint
            ),
            config_source=[
                "mailgun_api_key",
                "mailgun_domain_name",
                "mailgun_rest_api_endpoint",
                "default_email_sender",
            ],
            reachable=None,
            notes="Configuration status only (no active probe — avoids sending email / API cost).",
        )
    )

    # --- PowerBI (optional) -- configuration only ----------------------------
    services.append(
        ServiceStatus(
            key="powerbi",
            name="PowerBI (Reporting)",
            purpose="Embedded business-intelligence reports.",
            category="External API",
            required=False,
            configured=bool(
                settings.pbi_tenant_id
                and settings.pbi_client_id
                and settings.pbi_client_secret
                and settings.pbi_workspace_id
            ),
            config_source=["pbi_tenant_id", "pbi_client_id", "pbi_client_secret", "pbi_workspace_id"],
            reachable=None,
            notes="Configuration status only (no active probe — token acquisition is authenticated / rate-limited).",
        )
    )

    # --- Rombus camera/security (optional) -- configuration only -------------
    services.append(
        ServiceStatus(
            key="rombus",
            name="Rombus (Camera / Security)",
            purpose="Camera feeds and physical-security integration.",
            category="External API",
            required=False,
            configured=bool(settings.rombus_api_key),
            config_source=["rombus_api_key"],
            reachable=None,
            notes="Configuration status only (no active probe).",
        )
    )

    # --- Replit AI gateway / OpenAI (optional) -- configuration only ---------
    services.append(
        ServiceStatus(
            key="ai_gateway_openai",
            name="AI Gateway (OpenAI via Replit)",
            purpose="In-app document parsing and the native read-only AI Assistant.",
            category="External API",
            required=False,
            configured=bool(
                os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
                and os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
            ),
            config_source=["AI_INTEGRATIONS_OPENAI_API_KEY", "AI_INTEGRATIONS_OPENAI_BASE_URL"],
            reachable=None,
            notes=(
                f"Feature flag native_assistant_enabled={settings.native_assistant_enabled}. "
                "Configuration status only (no active probe — model calls are billable)."
            ),
        )
    )

    # --- Legacy ML gateway / cloud functions (optional) -- configuration only -
    services.append(
        ServiceStatus(
            key="legacy_ai_functions",
            name="Legacy AI Cloud Functions",
            purpose="Legacy Due-Diligence chatbot, file-parse and co-terminus functions.",
            category="External API",
            required=False,
            configured=bool(settings.ml_api_key),
            config_source=[
                "ml_api_key",
                "file_parse_function_url",
                "co_terminus_function_url",
                "chatbot_session_token_function_url",
                "chatbot_upload_file_function_url",
            ],
            reachable=None,
            notes="Configuration status only (no active probe).",
        )
    )

    # --- Telemetry BigQuery (optional, legacy) -- configuration only ---------
    services.append(
        ServiceStatus(
            key="telemetry_bigquery",
            name="Telemetry BigQuery (Legacy)",
            purpose="Legacy DAS telemetry chart/health fallbacks via BigQuery.",
            category="External API",
            required=False,
            configured=bool(settings.service_account_key_file_path and settings.telemetry_bq_project_id),
            config_source=["telemetry_bq_project_id", "service_account_key_file_path", "gcp_project_id"],
            reachable=None,
            notes=(
                f"Feature flag legacy_telemetry_enabled={settings.legacy_telemetry_enabled}. "
                "Configuration status only (no active probe)."
            ),
        )
    )

    # --- Weather provider (Open-Meteo, optional, public) -- configuration only -
    services.append(
        ServiceStatus(
            key="weather_openmeteo",
            name="Weather Provider (Open-Meteo)",
            purpose="Native historical weather import (W2).",
            category="External API",
            required=False,
            configured=True,
            config_source=[],
            reachable=None,
            notes="Public API (no credentials). Active probe skipped to avoid a network dependency on page load.",
        )
    )

    return services


@service_health_router.get(
    "/",
    response_model=ServiceHealthResponse,
    summary="Third-party service status dashboard",
    description=(
        "Reports configuration and (where a safe probe exists) reachability for "
        "each third-party / infrastructure service. Superuser-only. Never returns "
        "secret values; never fabricates reachability."
    ),
)
async def get_service_health(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    db_session: Session = Depends(get_session),
) -> ServiceHealthResponse:
    services = _build_services(db_session)
    return ServiceHealthResponse(
        services=services,
        generated_at=datetime.now(timezone.utc),
        total_count=len(services),
        configured_count=sum(1 for s in services if s.configured),
        probed_count=sum(1 for s in services if s.reachable is not None),
    )
