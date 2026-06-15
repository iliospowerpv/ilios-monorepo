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

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.site import Site
from app.models.weather import (
    ExpectedWeatherProvenance,
    WeatherApprovalAction,
    WeatherApprovalTargetType,
    WeatherDeviceMapping,
    WeatherObservation,
    WeatherObservationBatch,
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
