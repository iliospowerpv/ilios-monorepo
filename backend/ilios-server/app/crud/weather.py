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

from typing import Iterable, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
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


class WeatherObservationBatchCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(model=WeatherObservationBatch, db_session=db_session)

    def create(self, **kwargs) -> WeatherObservationBatch:
        batch = WeatherObservationBatch(**kwargs)
        self.db_session.add(batch)
        self.db_session.commit()
        self.db_session.refresh(batch)
        return batch


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
