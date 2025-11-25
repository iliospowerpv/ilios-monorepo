from app.crud.base_crud import BaseCRUD
from app.models.site_visit import SiteVisit


class SiteVisitCRUD(BaseCRUD):

    def __init__(self, db_session):
        super().__init__(model=SiteVisit, db_session=db_session)
