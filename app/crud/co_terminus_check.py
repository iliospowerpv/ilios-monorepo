from app.crud.base_crud import BaseCRUD
from app.models.site import CoTerminusCheck


class CoTerminusCheckCRUD(BaseCRUD):
    """CRUD operations on CoTerminusCheck model."""

    def __init__(self, db_session):
        super().__init__(model=CoTerminusCheck, db_session=db_session)
