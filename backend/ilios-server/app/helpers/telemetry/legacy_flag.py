"""Feature flag for legacy telemetry side effects.

The legacy DAS telemetry pipeline (Firestore mapping sync, BigQuery chart/health
fallbacks, the external ``rea-telemetry`` Cloud Run job) is being decommissioned
in favor of the in-platform Telemetry V2 path. These legacy side effects are
gated behind ``settings.legacy_telemetry_enabled`` (default ``False``) so they
are inert unless explicitly re-enabled, without deleting the code this sprint.

The settings model uses ``case_sensitive=True``, so the environment variable key
must be the lowercase ``legacy_telemetry_enabled``.
"""
from app.settings import settings


def legacy_telemetry_enabled() -> bool:
    """Return True when legacy telemetry side effects are explicitly enabled."""
    return bool(getattr(settings, "legacy_telemetry_enabled", False))
