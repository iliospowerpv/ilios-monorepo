"""Role Profile DB models for deep stakeholder role definitions."""

from sqlalchemy import Boolean, Column, ForeignKey, Identity, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class RoleProfile(Base):
    """Model for role profiles that provide granular module permissions.
    
    Role profiles work alongside the simplified 3-role system (company_admin,
    contributor, read_only) to provide deeper stakeholder role definitions
    without resurrecting the legacy 45-role system.
    """

    __tablename__ = "role_profiles"

    key = Column(String(50), primary_key=True)
    label = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    applicable_company_types = Column(ARRAY(String), nullable=True)
    default_module_permissions = Column(JSONB, nullable=False, default={})
    default_dashboard_key = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
