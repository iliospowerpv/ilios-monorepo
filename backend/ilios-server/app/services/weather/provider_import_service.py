"""Third-party weather provider import (Phase C) — native-PostgreSQL pulls.

This service pulls weather observations from a registered third-party provider
adapter and persists them into the W0 ``weather_observations`` table with an
immutable ``weather_observation_batches`` (``batch_kind=provider_pull``)
provenance record. It is the provider-fed sibling of the file-fed
:mod:`app.services.weather.historical_weather_import_service` and deliberately
reuses that module's row normalization, idempotency key, and summary helpers so
both paths obey the identical W0 invariants.

CONTEXT-ONLY contract (Phases A–D):

* External weather is **never** physics-/expected-eligible. A pull stores the
  provider's honest measurement semantics (e.g. GHI irradiance / ambient
  temperature) verbatim and converts NOTHING — no GHI->POA transposition, no
  ambient->cell conversion. ``physics_usable_rows`` is therefore 0.
* It never touches the :class:`~app.services.weather.weather_resolver.WeatherResolver`,
  the expected formula, telemetry ingestion, rollups, the scheduler, baselines,
  reconciliation, or ``expected_weather_provenance``.
* It never fabricates a value: a genuinely missing reading is the ABSENCE of a
  row, never a fabricated/zero value.

Cost / safety controls:

* **Gap-only.** Each requested window is chunked, and a chunk whose hourly slots
  are already fully stored for the resolved source is SKIPPED — a metered call is
  never re-spent on data already held.
* **Idempotent.** Every row carries the same deterministic ``dedupe_key`` as the
  file path, so an overlapping re-pull inserts nothing (``ON CONFLICT DO NOTHING``).
* **Rate-limited.** A best-effort Redis token counter enforces the provider's
  declared per-minute/per-day quota; it fails OPEN on cache-infra errors so a
  cache outage never blocks a legitimate (keyless/free) pull, and a provider 429
  stops the run with an honest ``partial``/``failed`` status.
* **Partial-tolerant.** A per-chunk transport/mapping failure is recorded and the
  run continues; whatever was retrieved is persisted and the batch records an
  honest ``succeeded`` / ``partial`` / ``failed`` ``pull_status``.
"""
from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy.orm import Session

from app.crud.weather import (
    WeatherObservationBatchCRUD,
    WeatherObservationCRUD,
    WeatherSourceCRUD,
)
from app.integrations.weather.base import (
    WeatherCredentialError,
    WeatherNoData,
    WeatherProviderAdapter,
    WeatherProviderError,
    WeatherProviderUnavailable,
    WeatherRateLimited,
    WeatherMappingError,
)
from app.integrations.weather.models import (
    NormalizedWeatherRow,
    WeatherProviderCapabilities,
)
from app.models.weather import (
    WeatherConfidence,
    WeatherIrradiancePlane,
    WeatherObservationBatchKind,
    WeatherProviderCatalog,
    WeatherProviderPullStatus,
    WeatherSourceType,
    WeatherTemperatureType,
)
from app.models.site import Site
from app.schema.weather import (
    ProviderImportPreviewResponse,
    ProviderImportRequest,
    ProviderImportResponse,
)
from app.services.weather.historical_weather_import_service import (
    NormalizedObservation,
    _summarize,
    build_dedupe_key,
)

logger = logging.getLogger(__name__)

# Enum value sets, validated at the service boundary so adapter strings get the
# same protection the file-import path gives.
_VALID_PLANES = {e.value for e in WeatherIrradiancePlane}
_VALID_TEMPS = {e.value for e in WeatherTemperatureType}
_VALID_CONFIDENCES = {e.value for e in WeatherConfidence}

# Default per-call chunk span. Bounds provider response sizes and isolates a
# partial failure to a single chunk; ON CONFLICT dedupe makes an over-small
# chunk harmless (it just re-confirms existing rows).
_DEFAULT_MAX_CHUNK_DAYS = 31
_HOUR_SECONDS = 3600
_ERROR_SUMMARY_MAX = 2000


class ProviderImportError(Exception):
    """A pre-flight problem that should surface as an HTTP error.

    Carries a ``status_code`` so the router can translate without the service
    importing FastAPI/HTTP types.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Rate limiter (best-effort, Redis-backed fixed-window counter)
# ---------------------------------------------------------------------------
def _seconds_to_utc_midnight(now: datetime) -> int:
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(int((tomorrow - now).total_seconds()), 1)


class ProviderRateLimiter:
    """Fixed-window per-(provider, account) request counter backed by Redis.

    Enforces the provider's declared ``requests_per_minute`` / ``requests_per_day``
    quota across processes. It FAILS OPEN on any Redis error (a cache outage must
    not block a legitimate, free, keyless pull) and is a no-op when the provider
    declares no limits. Inject a fake client in tests for determinism.
    """

    def __init__(self, redis_client: Any = None, *, use_default_cache: bool = True):
        self._client = redis_client
        self._use_default_cache = use_default_cache if redis_client is None else False

    def _client_or_none(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._use_default_cache:
            return None
        try:
            from app.redis_cache.cache import get_cache

            return get_cache()
        except Exception:  # noqa: BLE001 - cache infra is optional; fail open
            logger.warning("weather_provider_rate_limiter_unavailable")
            return None

    @staticmethod
    def _keys(provider_key: str, account_key: str, now: datetime) -> tuple[str, str]:
        minute = int(now.timestamp() // 60)
        day = now.strftime("%Y%m%d")
        base = f"weather:rl:{provider_key}:{account_key}"
        return f"{base}:m:{minute}", f"{base}:d:{day}"

    def remaining(
        self,
        *,
        provider_key: str,
        account_key: str,
        rpm: Optional[int],
        rpd: Optional[int],
        now: Optional[datetime] = None,
    ) -> tuple[Optional[int], Optional[int]]:
        """Peek remaining quota WITHOUT consuming (for preview). None == unknown."""
        now = now or datetime.now(timezone.utc)
        client = self._client_or_none()
        if client is None:
            return (None, None)
        mkey, dkey = self._keys(provider_key, account_key, now)
        try:
            rem_min = max(rpm - int(client.get(mkey) or 0), 0) if rpm else None
            rem_day = max(rpd - int(client.get(dkey) or 0), 0) if rpd else None
        except Exception:  # noqa: BLE001
            logger.warning("weather_provider_rate_limiter_peek_failed")
            return (None, None)
        return (rem_min, rem_day)

    def consume(
        self,
        *,
        provider_key: str,
        account_key: str,
        rpm: Optional[int],
        rpd: Optional[int],
        now: Optional[datetime] = None,
    ) -> tuple[bool, Optional[int]]:
        """Consume one request. Returns ``(allowed, retry_after_seconds)``.

        Fails OPEN on infra error and when no limit is declared.
        """
        now = now or datetime.now(timezone.utc)
        if not rpm and not rpd:
            return (True, None)
        client = self._client_or_none()
        if client is None:
            return (True, None)
        mkey, dkey = self._keys(provider_key, account_key, now)
        try:
            if rpm and int(client.get(mkey) or 0) + 1 > rpm:
                return (False, 60 - int(now.timestamp()) % 60)
            if rpd and int(client.get(dkey) or 0) + 1 > rpd:
                return (False, _seconds_to_utc_midnight(now))
            if rpm:
                client.incr(mkey)
                client.expire(mkey, 60)
            if rpd:
                client.incr(dkey)
                client.expire(dkey, 86400)
        except Exception:  # noqa: BLE001
            logger.warning("weather_provider_rate_limiter_consume_failed")
            return (True, None)
        return (True, None)


# ---------------------------------------------------------------------------
# Row normalization (provider row -> validated NormalizedObservation)
# ---------------------------------------------------------------------------
def _coerce_enum(value: Any, default: str, valid: set[str], field: str) -> str:
    if value is None:
        return default
    raw = value.value if hasattr(value, "value") else value
    if raw not in valid:
        raise ValueError(f"invalid {field}: {raw!r}")
    return raw


def _normalize_provider_row(
    row: NormalizedWeatherRow,
) -> tuple[Optional[NormalizedObservation], Optional[str]]:
    """Validate + normalize ONE adapter row. Returns ``(obs_or_None, warning)``.

    Provider pulls are best-effort: an invalid row is SKIPPED with a warning
    (the run becomes ``partial``) rather than aborting the whole pull. Semantics
    are validated against the W0 enums and are NEVER converted.
    """
    try:
        plane = _coerce_enum(
            row.irradiance_plane,
            WeatherIrradiancePlane.unknown.value,
            _VALID_PLANES,
            "irradiance_plane",
        )
        temp = _coerce_enum(
            row.temperature_type,
            WeatherTemperatureType.unknown.value,
            _VALID_TEMPS,
            "temperature_type",
        )
        conf = _coerce_enum(
            row.confidence,
            WeatherConfidence.unknown.value,
            _VALID_CONFIDENCES,
            "confidence",
        )
        value = float(row.value)
        if not math.isfinite(value):
            raise ValueError("value must be a finite number")
        ts = row.obs_ts
        if not isinstance(ts, datetime):
            raise ValueError("obs_ts must be a datetime")
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        metric = str(row.metric).strip()
        if not metric:
            raise ValueError("metric is required")
    except (TypeError, ValueError) as exc:
        return None, f"skipped invalid provider row: {exc}"

    return (
        NormalizedObservation(
            obs_ts=ts,
            metric=metric,
            value=value,
            unit=str(row.unit) if row.unit is not None else None,
            irradiance_plane=plane,
            temperature_type=temp,
            is_modeled=bool(row.is_modeled),
            confidence=conf,
            source_row_id=str(row.source_row_id)
            if row.source_row_id is not None
            else None,
        ),
        None,
    )


# ---------------------------------------------------------------------------
# Planning helpers (metrics, chunking, gap-fill coverage)
# ---------------------------------------------------------------------------
def resolve_metrics(
    capabilities: WeatherProviderCapabilities, requested: Optional[Sequence[str]]
) -> list[str]:
    """Resolve the metric set to pull: the request's, else the provider's full set.

    Requested metrics outside the provider's advertised set are dropped (a
    provider can only return what it offers). Returns a sorted, de-duplicated
    list; empty means nothing to pull.
    """
    advertised = {str(m) for m in (capabilities.metrics or set())}
    if requested:
        wanted = {str(m).strip() for m in requested if str(m).strip()}
        chosen = wanted & advertised if advertised else wanted
        return sorted(chosen)
    return sorted(advertised)


def plan_chunks(
    window_start: datetime,
    window_end: datetime,
    *,
    max_chunk_days: int = _DEFAULT_MAX_CHUNK_DAYS,
    max_history_days: Optional[int] = None,
    provider_now: Optional[datetime] = None,
) -> tuple[list[tuple[datetime, datetime]], Optional[datetime]]:
    """Split ``[window_start, window_end]`` into bounded chunks (naive-UTC).

    When ``max_history_days`` is declared the window start is clamped to
    ``provider_now - max_history_days`` (providers refuse data older than their
    archive horizon). Returns ``(chunks, clamped_start_or_None)``; an empty list
    means the (possibly clamped) window is non-positive.
    """
    clamped_start: Optional[datetime] = None
    start = window_start
    if max_history_days is not None and max_history_days > 0:
        now = provider_now or datetime.now(timezone.utc).replace(tzinfo=None)
        horizon = now - timedelta(days=max_history_days)
        if start < horizon:
            start = horizon
            clamped_start = horizon
    if window_end <= start:
        return [], clamped_start

    chunks: list[tuple[datetime, datetime]] = []
    span = timedelta(days=max(max_chunk_days, 1))
    cursor = start
    while cursor < window_end:
        chunk_end = min(cursor + span, window_end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end
    return chunks, clamped_start


def _expected_hourly_slots(cs: datetime, ce: datetime, n_metrics: int) -> int:
    if n_metrics <= 0 or ce <= cs:
        return 0
    hours = int((ce - cs).total_seconds() // _HOUR_SECONDS) + 1
    return hours * n_metrics


def _chunk_fully_covered(
    db: Session,
    *,
    site_id: int,
    source_id: Optional[int],
    metrics: list[str],
    cs: datetime,
    ce: datetime,
) -> bool:
    """True iff every expected hourly slot for ``metrics`` is already stored.

    Coverage is scoped to the resolved provider source when known, so a DIFFERENT
    source's data never suppresses this source's pull. The check is conservative:
    it only skips a chunk that is PROVABLY full, so a slightly under-counted
    expectation merely re-pulls (idempotently) rather than missing a gap.
    """
    existing = WeatherObservationCRUD(db).get_window(
        site_id, start=cs, end=ce, metrics=metrics, weather_source_id=source_id
    )
    covered = len({(o.metric, o.obs_ts) for o in existing})
    expected = _expected_hourly_slots(cs, ce, len(metrics))
    return expected > 0 and covered >= expected


def _find_existing_provider_source(
    db: Session, *, site_id: int, provider_key: str
) -> Optional[Any]:
    """Find a previously-created external-modeled source for this provider/site."""
    for src in WeatherSourceCRUD(db).list_for_site(site_id):
        if (
            getattr(src, "source_type", None) == WeatherSourceType.external_modeled_provider
            and getattr(src, "provider_key", None) == provider_key
        ):
            return src
    return None


# ---------------------------------------------------------------------------
# Hashing / sanitization
# ---------------------------------------------------------------------------
def _combine_hashes(hashes: list[Optional[str]]) -> Optional[str]:
    present = [h for h in hashes if h]
    if not present:
        return None
    if len(present) == 1:
        return present[0][:128]
    digest = hashlib.sha256("|".join(present).encode("utf-8")).hexdigest()
    return digest[:128]


def _combine_api_versions(versions: set[Optional[str]]) -> Optional[str]:
    present = sorted({v for v in versions if v})
    if not present:
        return None
    return ",".join(present)[:64]


def _build_error_summary(messages: list[str]) -> Optional[str]:
    seen: list[str] = []
    for msg in messages:
        text = (msg or "").strip()
        if text and text not in seen:
            seen.append(text)
    if not seen:
        return None
    return "; ".join(seen)[:_ERROR_SUMMARY_MAX]


# ---------------------------------------------------------------------------
# Preview (dry-run; writes NOTHING)
# ---------------------------------------------------------------------------
def preview_provider_import(
    db: Session,
    *,
    site: Site,
    catalog: WeatherProviderCatalog,
    adapter: WeatherProviderAdapter,
    coordinates: tuple[float, float],
    request: ProviderImportRequest,
    rate_limiter: Optional[ProviderRateLimiter] = None,
) -> ProviderImportPreviewResponse:
    """Dry-run plan for a provider pull. Writes NOTHING.

    Resolves metrics + chunk plan + gap-fill so the operator sees the real
    metered cost (``estimated_provider_calls``) and the context-only verdict
    before committing. Never creates a source/batch and never calls the provider.
    """
    capabilities = adapter.capabilities()
    metrics = resolve_metrics(capabilities, request.metrics)
    warnings: list[str] = ["context_only_not_expected_eligible"]
    if capabilities.is_modeled:
        warnings.append("provider_is_modeled")
    if not metrics:
        warnings.append("no_metrics_resolved")

    chunks, clamped_start = plan_chunks(
        request.window_start,
        request.window_end,
        max_history_days=capabilities.max_history_days,
    )
    if clamped_start is not None:
        warnings.append("window_clamped_to_max_history")
    effective_start = clamped_start or request.window_start
    if not chunks:
        warnings.append("empty_effective_window")

    existing_source = _find_existing_provider_source(
        db, site_id=site.id, provider_key=request.provider_key
    )
    source_id = existing_source.id if existing_source is not None else None
    gap_fill = request.granularity == "hourly"

    chunks_to_pull = 0
    chunks_covered = 0
    for cs, ce in chunks:
        if (
            gap_fill
            and metrics
            and _chunk_fully_covered(
                db, site_id=site.id, source_id=source_id, metrics=metrics, cs=cs, ce=ce
            )
        ):
            chunks_covered += 1
        else:
            chunks_to_pull += 1

    existing_count = 0
    if metrics and chunks:
        existing_count = len(
            WeatherObservationCRUD(db).get_window(
                site.id,
                start=effective_start,
                end=request.window_end,
                metrics=metrics,
                weather_source_id=source_id,
            )
        )

    limiter = rate_limiter or ProviderRateLimiter()
    rem_min, rem_day = limiter.remaining(
        provider_key=request.provider_key,
        account_key=str(request.account_id) if request.account_id else "keyless",
        rpm=capabilities.rate_limit.requests_per_minute,
        rpd=capabilities.rate_limit.requests_per_day,
    )

    return ProviderImportPreviewResponse(
        provider_key=request.provider_key,
        display_name=catalog.display_name,
        licensing_class=capabilities.licensing_class or catalog.licensing_class,
        context_only=True,
        expected_eligible_capable=False,
        requested_metrics=metrics,
        native_plane=capabilities.native_plane,
        native_temperature_type=capabilities.native_temperature_type,
        is_modeled=capabilities.is_modeled,
        window_start=request.window_start,
        window_end=request.window_end,
        effective_window_start=effective_start if chunks else None,
        effective_window_end=request.window_end if chunks else None,
        chunk_count=len(chunks),
        chunks_to_pull=chunks_to_pull,
        chunks_already_covered=chunks_covered,
        estimated_provider_calls=chunks_to_pull,
        existing_observation_count=existing_count,
        rate_limit_remaining_minute=rem_min,
        rate_limit_remaining_day=rem_day,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Run (pull + persist)
# ---------------------------------------------------------------------------
@dataclass
class _PullAccumulator:
    normalized: list[NormalizedObservation]
    warnings: list[str]
    errors: list[str]
    request_hashes: list[Optional[str]]
    response_hashes: list[Optional[str]]
    api_versions: set[Optional[str]]
    chunks_pulled: int = 0
    chunks_skipped: int = 0
    chunks_failed: int = 0
    rows_skipped: int = 0
    partial: bool = False
    rate_limited: bool = False
    fatal_credential: bool = False


def _resolve_run_source_id(
    db: Session, *, site: Site, request: ProviderImportRequest, capabilities
) -> int:
    existing = _find_existing_provider_source(
        db, site_id=site.id, provider_key=request.provider_key
    )
    if existing is not None:
        return existing.id
    created = WeatherSourceCRUD(db).create(
        site_id=site.id,
        company_id=None,
        source_type=WeatherSourceType.external_modeled_provider,
        display_name=(
            f"{request.provider_key} (provider pull)"
            if not request.account_id
            else f"{request.provider_key} account {request.account_id}"
        ),
        provider_key=request.provider_key,
        is_modeled=bool(capabilities.is_modeled),
        default_confidence=WeatherConfidence.unknown,
        licensing_note=None,
    )
    return created.id


def run_provider_import(
    db: Session,
    *,
    site: Site,
    catalog: WeatherProviderCatalog,
    adapter: WeatherProviderAdapter,
    credentials: dict[str, str],
    coordinates: tuple[float, float],
    request: ProviderImportRequest,
    account_id: Optional[int] = None,
    imported_by: Optional[int] = None,
    rate_limiter: Optional[ProviderRateLimiter] = None,
) -> ProviderImportResponse:
    """Pull a window from a provider and persist it (gap-only + idempotent).

    Best-effort and partial-tolerant: a per-chunk transport/mapping failure is
    recorded and the run continues; a credential rejection or rate-limit stops
    the run. The provider-pull batch records an honest ``succeeded`` / ``partial``
    / ``failed`` status, and observations are written via idempotent upsert so an
    overlapping window inserts nothing. NEVER fabricates a value or converts
    semantics.
    """
    capabilities = adapter.capabilities()
    metrics = resolve_metrics(capabilities, request.metrics)
    lat, lon = coordinates

    chunks, clamped_start = plan_chunks(
        request.window_start,
        request.window_end,
        max_history_days=capabilities.max_history_days,
    )
    effective_start = clamped_start or request.window_start

    base_warnings: list[str] = ["context_only_not_expected_eligible"]
    if clamped_start is not None:
        base_warnings.append("window_clamped_to_max_history")

    # Nothing to do: no metrics or empty effective window.
    if not metrics or not chunks:
        return ProviderImportResponse(
            status=WeatherProviderPullStatus.succeeded.value,
            pull_status=WeatherProviderPullStatus.succeeded.value,
            batch_id=None,
            site_id=site.id,
            weather_source_id=None,
            provider_key=request.provider_key,
            account_id=account_id,
            rows_pulled=0,
            rows_inserted=0,
            rows_duplicate=0,
            warnings=base_warnings
            + (["no_metrics_resolved"] if not metrics else ["empty_effective_window"]),
        )

    limiter = rate_limiter or ProviderRateLimiter()
    account_key = str(account_id) if account_id else "keyless"
    rpm = capabilities.rate_limit.requests_per_minute
    rpd = capabilities.rate_limit.requests_per_day
    gap_fill = request.granularity == "hourly"

    # Resolve (or create) the external-modeled provider source. Resolved BEFORE
    # the loop so even a fully-failed pull records a batch tied to a real source.
    source_id = _resolve_run_source_id(
        db, site=site, request=request, capabilities=capabilities
    )

    acc = _PullAccumulator(
        normalized=[],
        warnings=list(base_warnings),
        errors=[],
        request_hashes=[],
        response_hashes=[],
        api_versions=set(),
    )

    for cs, ce in chunks:
        if gap_fill and _chunk_fully_covered(
            db, site_id=site.id, source_id=source_id, metrics=metrics, cs=cs, ce=ce
        ):
            acc.chunks_skipped += 1
            continue

        allowed, retry_after = limiter.consume(
            provider_key=request.provider_key,
            account_key=account_key,
            rpm=rpm,
            rpd=rpd,
        )
        if not allowed:
            acc.rate_limited = True
            acc.errors.append(
                "rate limit reached before pull"
                + (f"; retry after {retry_after}s" if retry_after else "")
            )
            break

        try:
            result = adapter.get_observations(
                credentials,
                latitude=lat,
                longitude=lon,
                window_start=cs,
                window_end=ce,
                requested_metrics=metrics,
                granularity=request.granularity,
            )
        except WeatherRateLimited as exc:
            acc.rate_limited = True
            ra = exc.retry_after
            acc.errors.append(
                "provider rate limited" + (f"; retry after {ra}s" if ra else "")
            )
            break
        except WeatherCredentialError as exc:
            acc.fatal_credential = True
            acc.errors.append(str(exc) or "provider credentials were rejected")
            break
        except WeatherNoData as exc:
            acc.warnings.append(str(exc) or "provider reported no data for a window")
            acc.chunks_pulled += 1
            acc.request_hashes.append(None)
            acc.response_hashes.append(None)
            continue
        except (WeatherProviderUnavailable, WeatherMappingError) as exc:
            acc.chunks_failed += 1
            acc.errors.append(str(exc) or exc.__class__.__name__)
            continue
        except WeatherProviderError as exc:  # any other structured provider error
            acc.chunks_failed += 1
            acc.errors.append(str(exc) or exc.__class__.__name__)
            continue

        acc.chunks_pulled += 1
        acc.request_hashes.append(result.request_hash)
        acc.response_hashes.append(result.response_hash)
        acc.api_versions.add(result.api_version)
        if result.partial:
            acc.partial = True
        acc.warnings.extend(result.warnings or ())
        acc.errors.extend(result.errors or ())
        for row in result.rows:
            obs, warn = _normalize_provider_row(row)
            if warn:
                acc.warnings.append(warn)
                acc.rows_skipped += 1
                continue
            if obs is not None:
                acc.normalized.append(obs)

    summary = _summarize(acc.normalized)

    # A skipped invalid provider row means the pull is incomplete: the run is
    # honestly downgraded to ``partial`` (it never silently passes as a clean
    # ``succeeded``), but a malformed row is NEVER fabricated into a value.
    any_error = (
        bool(acc.errors)
        or acc.partial
        or acc.rate_limited
        or acc.chunks_failed > 0
        or acc.rows_skipped > 0
    )
    if acc.fatal_credential and not acc.normalized:
        pull_status = WeatherProviderPullStatus.failed
    elif not acc.normalized and any_error:
        pull_status = WeatherProviderPullStatus.failed
    elif acc.normalized and any_error:
        pull_status = WeatherProviderPullStatus.partial
    else:
        pull_status = WeatherProviderPullStatus.succeeded

    if summary["stored_not_usable_rows"] > 0:
        acc.warnings.append("stored_not_usable_rows_present")
    if summary["modeled_rows"] > 0:
        acc.warnings.append("modeled_rows_present")

    # Create the immutable provider-pull provenance batch (even on 0 rows so a
    # failed/empty attempt is still auditable).
    batch = WeatherObservationBatchCRUD(db).create(
        site_id=site.id,
        weather_source_id=source_id,
        batch_kind=WeatherObservationBatchKind.provider_pull,
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        row_count=len(acc.normalized),
        imported_by=imported_by,
        account_id=account_id,
        pull_status=pull_status,
        provider_request_hash=_combine_hashes(acc.request_hashes),
        provider_response_hash=_combine_hashes(acc.response_hashes),
        provider_api_version=_combine_api_versions(acc.api_versions),
        error_summary=_build_error_summary(acc.errors),
    )

    inserted = 0
    if acc.normalized:
        rows_to_insert = [
            {
                "site_id": site.id,
                "batch_id": batch.id,
                "weather_source_id": source_id,
                "metric": o.metric,
                "value": o.value,
                "unit": o.unit,
                "obs_ts": o.obs_ts,
                "irradiance_plane": o.irradiance_plane,
                "temperature_type": o.temperature_type,
                "is_modeled": o.is_modeled,
                "confidence": o.confidence,
                "dedupe_key": build_dedupe_key(
                    site_id=site.id, source_id=source_id, obs=o
                ),
            }
            for o in acc.normalized
        ]
        inserted = WeatherObservationCRUD(db).upsert(rows_to_insert)
        if inserted < len(acc.normalized):
            acc.warnings.append("idempotent_duplicates_skipped")

    # De-duplicate warnings while preserving order.
    seen: set[str] = set()
    deduped_warnings = [w for w in acc.warnings if not (w in seen or seen.add(w))]

    return ProviderImportResponse(
        status=pull_status.value,
        pull_status=pull_status.value,
        batch_id=batch.id,
        site_id=site.id,
        weather_source_id=source_id,
        provider_key=request.provider_key,
        account_id=account_id,
        context_only=True,
        expected_eligible_capable=False,
        rows_pulled=len(acc.normalized),
        rows_inserted=inserted,
        rows_duplicate=len(acc.normalized) - inserted,
        distinct_metrics=summary["distinct_metrics"],
        physics_usable_rows=summary["physics_usable_rows"],
        stored_not_usable_rows=summary["stored_not_usable_rows"],
        modeled_rows=summary["modeled_rows"],
        chunks_pulled=acc.chunks_pulled,
        chunks_skipped=acc.chunks_skipped,
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        api_version=_combine_api_versions(acc.api_versions),
        rate_limited=acc.rate_limited,
        warnings=deduped_warnings,
        errors=acc.errors,
    )
