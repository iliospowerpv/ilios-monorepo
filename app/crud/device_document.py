from typing import List

from sqlalchemy.sql.functions import coalesce, concat

from app.crud.base_crud import BaseCRUD
from app.models.device_document import DeviceDocument
from app.models.user import User


class DeviceDocumentCRUD(BaseCRUD):
    """CRUD operations on DeviceDocument model."""

    def __init__(self, db_session):
        super().__init__(model=DeviceDocument, db_session=db_session)

    def get_device_documents(self, device_id: int) -> List[DeviceDocument]:
        """Get device documents. Always orders by created_at DESC."""
        query = self.db_session.query(
            self.model.id,
            self.model.filename,
            self.model.category,
            self.model.created_at,
            concat(coalesce(User.first_name, "Deleted"), " ", coalesce(User.last_name, "User")).label("author"),
        )
        query = query.filter_by(device_id=device_id)
        query = query.outerjoin(User)
        query = self._add_order_by(query, self.model.created_at, "desc")
        return query.all()
