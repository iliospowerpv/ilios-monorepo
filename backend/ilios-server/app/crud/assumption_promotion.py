from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.project_facts import AssumptionPromotion


class AssumptionPromotionCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(AssumptionPromotion, db_session)

    def get_promotions_for_site(self, site_id: int) -> list[AssumptionPromotion]:
        return self.db_session.query(AssumptionPromotion).filter(
            AssumptionPromotion.site_id == site_id
        ).order_by(AssumptionPromotion.promoted_at.desc()).all()

    def get_promotions_for_file(self, file_id: int) -> list[AssumptionPromotion]:
        return self.db_session.query(AssumptionPromotion).filter(
            AssumptionPromotion.file_id == file_id
        ).order_by(AssumptionPromotion.promoted_at.desc()).all()

    def get_latest_promotion_for_document(self, document_id: int) -> AssumptionPromotion | None:
        return self.db_session.query(AssumptionPromotion).filter(
            AssumptionPromotion.document_id == document_id
        ).order_by(AssumptionPromotion.promoted_at.desc()).first()

    def create_promotion_record(
        self,
        site_id: int,
        document_id: int,
        file_id: int,
        promoted_by_id: int,
        notes: str | None,
        diff_json: dict
    ) -> AssumptionPromotion:
        return self.create_item({
            "site_id": site_id,
            "document_id": document_id,
            "file_id": file_id,
            "promoted_by_id": promoted_by_id,
            "notes": notes,
            "diff_json": diff_json,
        })
