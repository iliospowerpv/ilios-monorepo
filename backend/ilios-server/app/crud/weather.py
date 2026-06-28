"""Minimal CRUD helpers for the W0 weather provenance foundation.

Intentionally small: just enough create/list to exercise the schema and to give
W1 (the WeatherResolver) a stable seam. The one non-trivial helper is the
idempotent observation upsert, which mirrors the telemetry ingestion contract —
re-importing the same window is a no-op because rows dedupe on ``dedupe_key``.

These helpers do NOT touch ``expected_service``, telemetry ingestion, the
scheduler, DD, baselines, or reconciliation, and contain no external-provider,
secret, BigQuery, or Firestore logic.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.site import Site
from app.models.weather import (
    ExpectedWeatherProvenance,
    WeatherApprovalAction,
    WeatherApprovalTargetType,
    WeatherDeclarationStatus,
    WeatherDeviceMapping,
    WeatherObservation,
    WeatherObservationBatch,
    WeatherObservationBatchKind,
    WeatherProviderAccount,
    WeatherProviderCatalog,
    WeatherSource,
    WeatherSourceApproval,
    WeatherSourceProfile,
    WeatherSourceProfileStatus,
)


class WeatherSourceCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(model=WeatherSource, db_session=db_session)

    def create(self, **kwargs) -> WeatherSource:
        source = WeatherSource(**kwargs)
        self.db_session.add(source)
        self.db_session.commit()
        self.db_session.refresh(source)
        return source

    def get(self, source_id: int) -> Optional[WeatherSource]:
        return (
            self.db_session.query(WeatherSource)
            .filter(WeatherSource.id == source_id)
            .one_or_none()
        )

    def get_visible_to_site(
        self, *, site_id: int, source_id: int
    ) -> Optional[WeatherSource]:
        """Return the source IFF it is visible to ``site_id``.

        A source is visible when it is site-scoped to this exact site, OR
        company-scoped to the site's company, OR global (no site/company). A
        source bound to a DIFFERENT site (or a different company) returns
        ``None`` so callers can never attach another tenant's weather source to
        this site. Pure read; no writes.
        """
        source = self.get(source_id)
        if source is None:
            return None
        if source.site_id is not None:
            return source if source.site_id == site_id else None
        if source.company_id is not None:
            site = self.db_session.get(Site, site_id)
            if site is None or source.company_id != site.company_id:
                return None
        return source

    def list_for_site(
        self, site_id: int, *, active_only: bool = False
    ) -> list[WeatherSource]:
        query = self.db_session.query(WeatherSource).filter(
            WeatherSource.site_id == site_id
        )
        if active_only:
            query = query.filter(WeatherSource.active.is_(True))
        return query.order_by(WeatherSource.id).all()


class WeatherSourceProfileCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(model=WeatherSourceProfile, db_session=db_session)

    def create(self, **kwargs) -> WeatherSourceProfile:
        """Create a profile row. Versioned by NEW ROW — never mutate in place,
        and never auto-activate (status defaults to ``draft``)."""
        profile = WeatherSourceProfile(**kwargs)
        self.db_session.add(profile)
        self.db_session.commit()
        self.db_session.refresh(profile)
        return profile

    def get(self, profile_id: int) -> Optional[WeatherSourceProfile]:
        return (
            self.db_session.query(WeatherSourceProfile)
            .filter(WeatherSourceProfile.id == profile_id)
            .one_or_none()
        )

    def list_for_site(self, site_id: int) -> list[WeatherSourceProfile]:
        return (
            self.db_session.query(WeatherSourceProfile)
            .filter(WeatherSourceProfile.site_id == site_id)
            .order_by(
                WeatherSourceProfile.priority.desc(),
                WeatherSourceProfile.id,
            )
            .all()
        )

    def set_lifecycle_status(
        self,
        profile_id: int,
        *,
        status: WeatherSourceProfileStatus,
        approved_by: Optional[int] = None,
        approved_at: Optional[datetime] = None,
    ) -> Optional[WeatherSourceProfile]:
        """Transition ONLY the lifecycle fields of a profile.

        Mutates ``status`` and, when supplied, ``approved_by`` / ``approved_at``.
        It deliberately NEVER touches policy fields (role, source, priority,
        effective window, fallback/modeled flags, min-confidence) — a policy
        change must be expressed as a NEW profile row, preserving the W0
        versioned-by-new-row invariant. Returns ``None`` if no such profile.
        """
        profile = self.get(profile_id)
        if profile is None:
            return None
        profile.status = status
        if approved_by is not None:
            profile.approved_by = approved_by
        if approved_at is not None:
            profile.approved_at = approved_at
        self.db_session.add(profile)
        self.db_session.commit()
        self.db_session.refresh(profile)
        return profile


class WeatherObservationBatchCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(model=WeatherObservationBatch, db_session=db_session)

    def create(self, **kwargs) -> WeatherObservationBatch:
        batch = WeatherObservationBatch(**kwargs)
        self.db_session.add(batch)
        self.db_session.commit()
        self.db_session.refresh(batch)
        return batch

    def get(self, batch_id: int) -> Optional[WeatherObservationBatch]:
        return (
            self.db_session.query(WeatherObservationBatch)
            .filter(WeatherObservationBatch.id == batch_id)
            .one_or_none()
        )

    def list_provider_pulls_for_site(
        self, site_id: int, *, limit: int = 100
    ) -> list[WeatherObservationBatch]:
        """List ``provider_pull`` provenance batches for a site (newest-first).

        Read-only audit feed for the third-party provider framework. Scoped to
        ``batch_kind=provider_pull`` so file/manual/telemetry-backfill batches
        never leak into the provider-pull history view. Never mutates anything.
        """
        return (
            self.db_session.query(WeatherObservationBatch)
            .filter(
                WeatherObservationBatch.site_id == site_id,
                WeatherObservationBatch.batch_kind
                == WeatherObservationBatchKind.provider_pull,
            )
            .order_by(
                WeatherObservationBatch.created_at.desc(),
                WeatherObservationBatch.id.desc(),
            )
            .limit(limit)
            .all()
        )


class WeatherObservationCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(model=WeatherObservation, db_session=db_session)

    def upsert(self, rows: Iterable[dict]) -> int:
        """Idempotently insert observation rows, deduping on ``dedupe_key``.

        Returns the number of rows actually inserted (re-running with the same
        ``dedupe_key`` values inserts nothing). Existing rows are never updated
        or deleted — weather history is append-only.
        """
        rows = [dict(r) for r in rows]
        if not rows:
            return 0
        stmt = (
            pg_insert(WeatherObservation)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["dedupe_key"])
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        return result.rowcount or 0

    def list_for_site(
        self, site_id: int, *, metric: Optional[str] = None
    ) -> list[WeatherObservation]:
        query = self.db_session.query(WeatherObservation).filter(
            WeatherObservation.site_id == site_id
        )
        if metric is not None:
            query = query.filter(WeatherObservation.metric == metric)
        return query.order_by(
            WeatherObservation.metric, WeatherObservation.obs_ts
        ).all()

    def get_window(
        self,
        site_id: int,
        *,
        start: datetime,
        end: datetime,
        metrics: Optional[Iterable[str]] = None,
        weather_source_id: Optional[int] = None,
    ) -> list[WeatherObservation]:
        """Read observations for a site whose ``obs_ts`` falls in ``[start, end]``.

        Read-only window fetch used by the readiness/resolver historical paths.
        ``obs_ts`` is naive-UTC (the existing telemetry convention); the window
        bounds are inclusive on both ends to mirror the rollup ``get_series``
        contract. Optionally narrows to specific ``metrics`` and/or a single
        ``weather_source_id``. Never mutates anything.
        """
        query = self.db_session.query(WeatherObservation).filter(
            WeatherObservation.site_id == site_id,
            WeatherObservation.obs_ts >= start,
            WeatherObservation.obs_ts <= end,
        )
        metric_list = list(metrics) if metrics is not None else None
        if metric_list:
            query = query.filter(WeatherObservation.metric.in_(metric_list))
        if weather_source_id is not None:
            query = query.filter(
                WeatherObservation.weather_source_id == weather_source_id
            )
        return query.order_by(
            WeatherObservation.metric, WeatherObservation.obs_ts
        ).all()

    def summarize_by_source_metric(
        self, site_id: int, *, source_ids: Optional[Iterable[int]] = None
    ) -> list[tuple[int, str, int, Optional[datetime], Optional[datetime]]]:
        """Aggregate a site's observations to ``(source, metric)`` coverage rows.

        Returns ``(weather_source_id, metric, count, earliest_obs_ts,
        latest_obs_ts)`` grouped per source+metric — the read-only coverage
        summary the external-weather-context surface needs without loading every
        observation row. Optionally narrows to ``source_ids``. Never mutates
        anything; an absent (source, metric) pair simply yields no row (it is
        never fabricated as a zero-count entry).
        """
        query = self.db_session.query(
            WeatherObservation.weather_source_id,
            WeatherObservation.metric,
            func.count(WeatherObservation.id),
            func.min(WeatherObservation.obs_ts),
            func.max(WeatherObservation.obs_ts),
        ).filter(WeatherObservation.site_id == site_id)
        id_list = list(source_ids) if source_ids is not None else None
        if id_list is not None:
            if not id_list:
                return []
            query = query.filter(WeatherObservation.weather_source_id.in_(id_list))
        return query.group_by(
            WeatherObservation.weather_source_id, WeatherObservation.metric
        ).all()


class WeatherSourceApprovalCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(model=WeatherSourceApproval, db_session=db_session)

    def record(
        self,
        *,
        site_id: int,
        target_type: WeatherApprovalTargetType,
        target_id: int,
        action: WeatherApprovalAction,
        approved_by: Optional[int] = None,
        approved_at=None,
        rationale: Optional[str] = None,
    ) -> WeatherSourceApproval:
        """Append an immutable approval-ledger entry (never updates a prior row)."""
        entry = WeatherSourceApproval(
            site_id=site_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            approved_by=approved_by,
            approved_at=approved_at,
            rationale=rationale,
        )
        self.db_session.add(entry)
        self.db_session.commit()
        self.db_session.refresh(entry)
        return entry

    def list_for_target(
        self, target_type: WeatherApprovalTargetType, target_id: int
    ) -> list[WeatherSourceApproval]:
        return (
            self.db_session.query(WeatherSourceApproval)
            .filter(
                WeatherSourceApproval.target_type == target_type,
                WeatherSourceApproval.target_id == target_id,
            )
            .order_by(WeatherSourceApproval.id)
            .all()
        )


class WeatherDeviceMappingCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(model=WeatherDeviceMapping, db_session=db_session)

    def create(self, **kwargs) -> WeatherDeviceMapping:
        """Create a device-weather semantics mapping. Plane/temperature default
        to ``unknown`` so unmapped DAS weather is never assumed to be POA/cell."""
        mapping = WeatherDeviceMapping(**kwargs)
        self.db_session.add(mapping)
        self.db_session.commit()
        self.db_session.refresh(mapping)
        return mapping

    def list_for_site(self, site_id: int) -> list[WeatherDeviceMapping]:
        return (
            self.db_session.query(WeatherDeviceMapping)
            .filter(WeatherDeviceMapping.site_id == site_id)
            .order_by(WeatherDeviceMapping.id)
            .all()
        )

    def list_for_device(self, device_id: int) -> list[WeatherDeviceMapping]:
        """All declarations for a device, oldest-first (history is append-only)."""
        return (
            self.db_session.query(WeatherDeviceMapping)
            .filter(WeatherDeviceMapping.device_id == device_id)
            .order_by(WeatherDeviceMapping.id)
            .all()
        )

    def get_current_for_device(
        self, device_id: int, *, metric: Optional[str] = None
    ) -> Optional[WeatherDeviceMapping]:
        """The current semantics for a device: prefer the ACTIVE governed row.

        Resolution order (WS.2):
          1. The ``active`` governed declaration (single-active is enforced by the
             service on activation), highest ``id`` first as a defensive tie-break.
          2. Fallback to the latest row by ``id`` — this covers legacy NULL-status
             (ungoverned) rows and bare drafts, so pre-WS.2 behavior is preserved
             when no governed declaration has been activated yet.

        Optionally narrows to a single ``metric``. Pure read (no writes)."""
        base = self.db_session.query(WeatherDeviceMapping).filter(
            WeatherDeviceMapping.device_id == device_id
        )
        if metric is not None:
            base = base.filter(WeatherDeviceMapping.metric == metric)

        active = (
            base.filter(
                WeatherDeviceMapping.declaration_status
                == WeatherDeclarationStatus.active
            )
            .order_by(WeatherDeviceMapping.id.desc())
            .first()
        )
        if active is not None:
            return active
        return base.order_by(WeatherDeviceMapping.id.desc()).first()


class ExpectedWeatherProvenanceCRUD(BaseCRUD):
    """W0 placeholder CRUD. The runtime does NOT write provenance in W0; this
    exists only so the model has a consistent access seam for W1+."""

    def __init__(self, db_session: Session):
        super().__init__(model=ExpectedWeatherProvenance, db_session=db_session)

    def list_for_site(self, site_id: int) -> list[ExpectedWeatherProvenance]:
        return (
            self.db_session.query(ExpectedWeatherProvenance)
            .filter(ExpectedWeatherProvenance.site_id == site_id)
            .order_by(ExpectedWeatherProvenance.id)
            .all()
        )


# ---------------------------------------------------------------------------
# Third-party weather provider framework (Phases A–D) — read helpers.
# ---------------------------------------------------------------------------
class WeatherProviderCatalogCRUD(BaseCRUD):
    """Read helpers for the seeded third-party weather provider catalog.

    Catalog rows are seeded by migration (never user-created) and default to
    ``is_enabled=false`` so a provider stays dark until explicitly turned on.
    These helpers are read-only; the framework never marks an external provider
    as physics-/expected-eligible.
    """

    def __init__(self, db_session: Session):
        super().__init__(model=WeatherProviderCatalog, db_session=db_session)

    def get_by_key(self, provider_key: str) -> Optional[WeatherProviderCatalog]:
        return (
            self.db_session.query(WeatherProviderCatalog)
            .filter(WeatherProviderCatalog.provider_key == provider_key)
            .one_or_none()
        )

    def list_all(self, *, enabled_only: bool = False) -> list[WeatherProviderCatalog]:
        query = self.db_session.query(WeatherProviderCatalog)
        if enabled_only:
            query = query.filter(WeatherProviderCatalog.is_enabled.is_(True))
        return query.order_by(WeatherProviderCatalog.display_name).all()


class WeatherProviderAccountCRUD(BaseCRUD):
    """Read helpers for per-company weather provider accounts.

    The row stores only a ``secret_name`` REFERENCE into the durable credential
    store, never the API key itself. Account creation/rotation lives in the
    router so it can own the durability gate and compensating secret cleanup.
    """

    def __init__(self, db_session: Session):
        super().__init__(model=WeatherProviderAccount, db_session=db_session)

    def get_for_company(
        self, *, company_id: int, account_id: int
    ) -> Optional[WeatherProviderAccount]:
        return (
            self.db_session.query(WeatherProviderAccount)
            .filter(
                WeatherProviderAccount.id == account_id,
                WeatherProviderAccount.company_id == company_id,
            )
            .one_or_none()
        )

    def list_for_company(
        self, company_id: int, *, include_archived: bool = False
    ) -> list[WeatherProviderAccount]:
        query = self.db_session.query(WeatherProviderAccount).filter(
            WeatherProviderAccount.company_id == company_id
        )
        if not include_archived:
            query = query.filter(WeatherProviderAccount.is_archived.is_(False))
        return query.order_by(WeatherProviderAccount.id).all()
