"""Company DB models."""

from sqlalchemy import TIMESTAMP, VARCHAR, Column, Enum, Identity, Integer
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.board import RelatedBoards
from app.models.helpers import utcnow
from app.static.companies import CompanyTypes


class Company(RelatedBoards, Base):
    """Model of the company entity."""

    __tablename__ = "companies"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)

    name = Column(VARCHAR, nullable=False, unique=True)
    email = Column(VARCHAR, nullable=True)
    phone = Column(VARCHAR, nullable=True)
    address = Column(VARCHAR, nullable=True)
    company_type = Column(Enum(CompanyTypes), nullable=False)

    sites = relationship("Site", back_populates="company")
    users = relationship("User", back_populates="parent_company")
    das_connections = relationship("DASConnection", back_populates="company", order_by="DASConnection.name")

    created_at = Column(TIMESTAMP, server_default=utcnow())
    updated_at = Column(TIMESTAMP, server_default=utcnow())

    _allowed_users = relationship("User", secondary="user_projects", back_populates="companies")

    def get_active_users_ids(self, permissions_module_name):
        """Filter full list of allowed users to return only users who complete registration"""
        return [
            user.id
            for user in self._allowed_users
            if user.is_registered and user.role and user.role.permissions.get(permissions_module_name, {}).get("view")
        ]
