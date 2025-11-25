from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.helpers.permissions import get_default_permissions
from app.models.helpers import utcnow
from app.static.companies import CompanyTypes


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    permissions = Column(JSON, nullable=False, default=get_default_permissions())

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    users = relationship("User", back_populates="role")
    related_company_type = relationship("CompanyTypeRoleMapping", uselist=False)


class CompanyTypeRoleMapping(Base):
    __tablename__ = "company_type_role_mapping"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"))
    company_type = Column(Enum(CompanyTypes), nullable=False)

    role = relationship("Role", back_populates="related_company_type")
