from app.crud.base_crud import BaseCRUD
from app.models.internal_configuration import InternalConfiguration, InternalConfigurationNameEnum


class InternalConfigurationCRUD(BaseCRUD):
    """CRUD operations on InternalConfiguration model."""

    def __init__(self, db_session):
        super().__init__(model=InternalConfiguration, db_session=db_session)

    def get_by_name(self, config_name: InternalConfigurationNameEnum):
        return self.db_session.query(self.model).filter_by(name=config_name).first()
