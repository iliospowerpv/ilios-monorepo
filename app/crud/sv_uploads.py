from typing import List

from sqlalchemy.sql.functions import coalesce, concat

from app.crud.base_crud import BaseCRUD
from app.models.attachment import Attachment
from app.models.sv_uploads import SiteVisitUpload
from app.models.user import User


class SiteVisitUploadCRUD(BaseCRUD):

    def __init__(self, db_session):
        super().__init__(model=SiteVisitUpload, db_session=db_session)

    def get_uploads(self, site_visit_id: int, section_name: str) -> List[Attachment]:
        query = self.db_session.query(
            self.model.id,
            self.model.filename,
            self.model.created_at,
            concat(coalesce(User.first_name, "Deleted"), " ", coalesce(User.last_name, "User")).label("author"),
        )
        query = query.filter_by(site_visit_id=site_visit_id, section_name=section_name)
        query = query.outerjoin(User)
        query = self._add_order_by(query, self.model.created_at, "desc")
        return query.all()
