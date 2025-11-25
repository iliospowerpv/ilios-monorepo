import enum

from sqlalchemy import JSON, Column, DateTime, Enum, Identity, Integer

from app.db.base_class import Base
from app.models.helpers import utcnow


class InternalConfigurationNameEnum(enum.Enum):
    """Define configs supported to the API management.
    If you want to introduce new config, ensure to add it to the `ConfigHandlerFactory` as well"""

    ai_parsing = "ai_parsing"
    agreement_names = "agreement_names"
    co_terminus = "co_terminus"

    @classmethod
    def string_values(cls):
        return ", ".join([f"'{config_type.value}'" for config_type in cls])


class InternalConfiguration(Base):
    __tablename__ = "internal_configurations"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = Column(Enum(InternalConfigurationNameEnum), unique=True)
    payload = Column(JSON, nullable=False)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())
