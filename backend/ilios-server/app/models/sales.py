"""Sales module database models."""

from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    VARCHAR,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Identity,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class Deal(Base):
    """Sales deal entity - pre-project acquisition tracking."""

    __tablename__ = "deals"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = Column(VARCHAR(255), nullable=False)
    developer_name = Column(VARCHAR(255), nullable=True)
    sales_stage = Column(VARCHAR(50), nullable=True)
    lifecycle_state = Column(VARCHAR(50), nullable=True)
    quoted_by = Column(VARCHAR(255), nullable=True)
    last_action = Column(Text, nullable=True)
    next_action = Column(Text, nullable=True)
    next_action_status = Column(VARCHAR(50), nullable=True)
    next_action_date = Column(Date, nullable=True)
    ownership_structure = Column(VARCHAR(255), nullable=True)
    sales_notes = Column(Text, nullable=True)
    
    address = Column(VARCHAR(500), nullable=True)
    city = Column(VARCHAR(255), nullable=True)
    state = Column(VARCHAR(50), nullable=True)
    zip_code = Column(VARCHAR(20), nullable=True)
    county = Column(VARCHAR(255), nullable=True)
    latitude = Column(DECIMAL(10, 7), nullable=True)
    longitude = Column(DECIMAL(10, 7), nullable=True)
    
    notice_to_proceed_date = Column(Date, nullable=True)
    mechanical_completion_date = Column(Date, nullable=True)
    permission_to_operate_date = Column(Date, nullable=True)
    substantial_completion_date = Column(Date, nullable=True)
    
    project_company = Column(VARCHAR(255), nullable=True)
    mipa_per_watt = Column(DECIMAL(10, 4), nullable=True)
    offtaker_name = Column(VARCHAR(255), nullable=True)
    offtaker_legal_name = Column(VARCHAR(255), nullable=True)
    utility_rate = Column(VARCHAR(255), nullable=True)
    utility_zone = Column(VARCHAR(255), nullable=True)
    system_size_ac = Column(DECIMAL(12, 2), nullable=True)
    system_size_dc = Column(DECIMAL(12, 2), nullable=True)
    
    itc_percent = Column(DECIMAL(5, 2), nullable=True)
    itc_amount = Column(DECIMAL(15, 2), nullable=True)
    fmv = Column(DECIMAL(15, 2), nullable=True)
    grant_amount = Column(DECIMAL(15, 2), nullable=True)
    tax_equity = Column(DECIMAL(15, 2), nullable=True)
    
    pipeline_value = Column(DECIMAL(15, 2), nullable=True)
    probability = Column(Integer, nullable=True)
    target_close_date = Column(Date, nullable=True)
    
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    assigned_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    converted_to_project_id = Column(Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, unique=True)
    is_converted = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(TIMESTAMP, server_default=utcnow())
    updated_at = Column(TIMESTAMP, server_default=utcnow(), onupdate=utcnow())

    company = relationship("Company", foreign_keys=[company_id])
    assigned_owner = relationship("User", foreign_keys=[assigned_owner_id])
    converted_project = relationship("Site", foreign_keys=[converted_to_project_id])


class SalesStateTransition(Base):
    """Audit log for sales stage and lifecycle state transitions."""

    __tablename__ = "sales_state_transitions"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True)
    
    transition_type = Column(VARCHAR(50), nullable=False)
    from_state = Column(VARCHAR(100), nullable=True)
    to_state = Column(VARCHAR(100), nullable=False)
    notes = Column(Text, nullable=True)
    
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=utcnow())

    site = relationship("Site", backref="sales_transitions", foreign_keys=[site_id])
    deal = relationship("Deal", backref="state_transitions", foreign_keys=[deal_id])
    changed_by = relationship("User", foreign_keys=[changed_by_id])
