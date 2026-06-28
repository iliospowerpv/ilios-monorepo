"""Read-only external-weather CONTEXT aggregation (Phase D / D1).

This service answers one question for a site: "what external (modeled) weather
has been pulled into the platform, and over what windows?" — purely for audit /
provenance / cosmetic labelling.

It is **strictly read-only** and deliberately decoupled from expected math:

* It NEVER calls or alters ``compute_weather_readiness`` (the POA+cell expected
  eligibility verdict). The readiness panel renders this context in a *separate*
  section, so the readiness verdict is byte-identical whether or not any external
  weather exists — the resolver-invariance gate holds by construction.
* Every external source it reports is context-only and structurally
  ``expected_eligible_capable=False``; external values carry ghi/ambient/unknown
  semantics and are never transposed to poa/cell here or anywhere.
* It fabricates nothing: a source/metric with no stored observations simply
  yields no coverage row (a missing reading is the ABSENCE of a row, never 0).

It performs ZERO writes/commits and touches no telemetry, ingestion, scheduler,
baseline, reconciliation, or resolver code.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.crud.weather import (
    WeatherObservationBatchCRUD,
    WeatherObservationCRUD,
    WeatherSourceCRUD,
)
from app.models.site import Site
from app.models.weather import WeatherSource, WeatherSourceType
from app.schema.weather import (
    ExternalWeatherContextMetric,
    ExternalWeatherContextResponse,
    ExternalWeatherContextSource,
    ProviderPullBatchResponse,
)


def _enum_value(value: object) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _is_external_source(source: WeatherSource) -> bool:
    return (
        getattr(source, "source_type", None)
        == WeatherSourceType.external_modeled_provider
    )


def build_external_weather_context(
    db: Session, *, site: Site, batch_limit: int = 50
) -> ExternalWeatherContextResponse:
    """Aggregate a site's external (modeled) weather into a context response.

    Resolves the site's external sources, summarizes their stored coverage per
    metric via a single grouped query (no per-row load), and attaches the most
    recent provider pull plus recent pull provenance. Pure read; never mutates,
    never computes expected math, never fabricates a value.
    """
    source_crud = WeatherSourceCRUD(db)
    observation_crud = WeatherObservationCRUD(db)
    batch_crud = WeatherObservationBatchCRUD(db)

    external_sources = [
        src for src in source_crud.list_for_site(site.id) if _is_external_source(src)
    ]
    source_by_id = {src.id: src for src in external_sources}

    # Grouped coverage rows: (source_id, metric, count, earliest, latest).
    coverage_rows = (
        observation_crud.summarize_by_source_metric(
            site.id, source_ids=list(source_by_id.keys())
        )
        if source_by_id
        else []
    )

    metrics_by_source: dict[int, list[ExternalWeatherContextMetric]] = {}
    counts_by_source: dict[int, int] = {}
    earliest_by_source: dict[int, object] = {}
    latest_by_source: dict[int, object] = {}
    total_observation_count = 0

    for source_id, metric, count, earliest, latest in coverage_rows:
        count = int(count or 0)
        total_observation_count += count
        metrics_by_source.setdefault(source_id, []).append(
            ExternalWeatherContextMetric(
                metric=metric,
                observation_count=count,
                earliest_obs=earliest,
                latest_obs=latest,
            )
        )
        counts_by_source[source_id] = counts_by_source.get(source_id, 0) + count
        if earliest is not None and (
            earliest_by_source.get(source_id) is None
            or earliest < earliest_by_source[source_id]
        ):
            earliest_by_source[source_id] = earliest
        if latest is not None and (
            latest_by_source.get(source_id) is None
            or latest > latest_by_source[source_id]
        ):
            latest_by_source[source_id] = latest

    sources: list[ExternalWeatherContextSource] = []
    for source in external_sources:
        source_metrics = sorted(
            metrics_by_source.get(source.id, []), key=lambda m: m.metric
        )
        sources.append(
            ExternalWeatherContextSource(
                weather_source_id=source.id,
                source_type=_enum_value(source.source_type) or "",
                provider_key=getattr(source, "provider_key", None),
                display_name=source.display_name,
                is_modeled=bool(getattr(source, "is_modeled", True)),
                default_confidence=_enum_value(
                    getattr(source, "default_confidence", None)
                ),
                licensing_note=getattr(source, "licensing_note", None),
                active=bool(getattr(source, "active", True)),
                observation_count=counts_by_source.get(source.id, 0),
                earliest_obs=earliest_by_source.get(source.id),
                latest_obs=latest_by_source.get(source.id),
                metrics=source_metrics,
            )
        )

    batches = batch_crud.list_provider_pulls_for_site(site.id, limit=batch_limit)
    recent_batches = [ProviderPullBatchResponse.from_model(b) for b in batches]
    last_pull = recent_batches[0] if recent_batches else None

    return ExternalWeatherContextResponse(
        site_id=site.id,
        source_count=len(sources),
        total_observation_count=total_observation_count,
        sources=sources,
        last_pull=last_pull,
        recent_batches=recent_batches,
    )
