"""Company DB models."""

from sqlalchemy import TIMESTAMP, VARCHAR, Column, Enum, ForeignKey, Identity, Index, Integer
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.board import RelatedBoards
from app.models.helpers import utcnow
from app.static.companies import CompanyTypes


class Company(RelatedBoards, Base):
    """Model of the company entity."""

    __tablename__ = "companies"
    
    __table_args__ = (
        Index('ix_companies_portfolio_hub_id', 'portfolio_hub_id'),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)

    name = Column(VARCHAR, nullable=False, unique=True)
    email = Column(VARCHAR, nullable=True)
    phone = Column(VARCHAR, nullable=True)
    address = Column(VARCHAR, nullable=True)
    company_type = Column(Enum(CompanyTypes), nullable=False)
    
    portfolio_hub_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True
    )

    sites = relationship("Site", back_populates="company")
    users = relationship("User", back_populates="parent_company")
    das_connections = relationship(
        "DASConnection",
        back_populates="company",
        order_by="DASConnection.name",
        foreign_keys="DASConnection.company_id"
    )
    
    portfolio_hub = relationship(
        "Company",
        remote_side="Company.id",
        foreign_keys=[portfolio_hub_id],
        backref="portfolio_members"
    )
    
    member_users = relationship("UserCompanyAccess", back_populates="company")

    created_at = Column(TIMESTAMP, server_default=utcnow())
    updated_at = Column(TIMESTAMP, server_default=utcnow())

    _allowed_users = relationship(
        "User",
        secondary="user_projects",
        primaryjoin="Company.id == foreign(UserProject.company_id)",
        secondaryjoin="foreign(UserProject.user_id) == User.id",
        overlaps="sites,project_memberships,member_users,companies",
        viewonly=True
    )

    def get_active_users_ids(self, permissions_module_name):
        """Filter full list of allowed users to return only users who complete registration"""
        return [
            user.id
            for user in self._allowed_users
            if user.is_registered and user.role and user.role.permissions.get(permissions_module_name, {}).get("view")
        ]
