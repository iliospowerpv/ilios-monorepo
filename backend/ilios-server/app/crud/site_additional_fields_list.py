from app.crud.base_crud import BaseCRUD
from app.models.site import SiteAdditionalFieldList


class SiteAdditionalFieldListCRUD(BaseCRUD):
    """CRUD operations on SiteAdditionalFieldList model."""

    def __init__(self, db_session):
        super().__init__(model=SiteAdditionalFieldList, db_session=db_session)
