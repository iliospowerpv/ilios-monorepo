from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.telemetry import CompanyDASProvider, DASProvidersEnum


class CompanyDASProviderCRUD:

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_providers(self, company_id: int) -> List[CompanyDASProvider]:
        return (
            self.db_session.query(CompanyDASProvider)
            .filter(CompanyDASProvider.company_id == company_id)
            .order_by(CompanyDASProvider.provider)
            .all()
        )

    def get_provider_enums(self, company_id: int) -> List[DASProvidersEnum]:
        rows = self.get_providers(company_id)
        return [row.provider for row in rows]

    def has_provider(self, company_id: int, provider: DASProvidersEnum) -> bool:
        return (
            self.db_session.query(CompanyDASProvider)
            .filter(
                CompanyDASProvider.company_id == company_id,
                CompanyDASProvider.provider == provider,
            )
            .first()
            is not None
        )

    def assign_provider(self, company_id: int, provider: DASProvidersEnum) -> CompanyDASProvider:
        existing = (
            self.db_session.query(CompanyDASProvider)
            .filter(
                CompanyDASProvider.company_id == company_id,
                CompanyDASProvider.provider == provider,
            )
            .first()
        )
        if existing:
            return existing

        record = CompanyDASProvider(company_id=company_id, provider=provider)
        self.db_session.add(record)
        self.db_session.commit()
        self.db_session.refresh(record)
        return record

    def remove_provider(self, company_id: int, provider: DASProvidersEnum) -> bool:
        deleted = (
            self.db_session.query(CompanyDASProvider)
            .filter(
                CompanyDASProvider.company_id == company_id,
                CompanyDASProvider.provider == provider,
            )
            .delete()
        )
        self.db_session.commit()
        return deleted > 0
