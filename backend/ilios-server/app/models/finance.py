"""Finance module database models."""

from sqlalchemy import (
    TIMESTAMP,
    VARCHAR,
    Boolean,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Identity,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow
from app.static.finance import (
    FinanceActualSource,
    FinanceApprovalDecision,
    FinanceBudgetCategory,
    FinanceBudgetStatus,
    FinanceObligationStatus,
    FinanceObligationType,
    FinanceVendorType,
)


class FinanceVendor(Base):
    """Vendor/service provider for finance tracking."""

    __tablename__ = "finance_vendors"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    name = Column(VARCHAR(255), nullable=False)
    vendor_type = Column(Enum(FinanceVendorType), nullable=False)
    contact_name = Column(VARCHAR(255), nullable=True)
    contact_email = Column(VARCHAR(255), nullable=True)
    contact_phone = Column(VARCHAR(50), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(TIMESTAMP, server_default=utcnow())
    updated_at = Column(TIMESTAMP, server_default=utcnow(), onupdate=utcnow())

    company = relationship("Company", backref="finance_vendors")
    budget_line_items = relationship("FinanceBudgetLineItem", back_populates="vendor")
    obligations = relationship("FinanceObligation", back_populates="vendor")
    actuals = relationship("FinanceActual", back_populates="vendor")


class FinanceBudget(Base):
    """Budget container for a site or deal."""

    __tablename__ = "finance_budgets"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=True)
    deal_id = Column(Integer, nullable=True)

    name = Column(VARCHAR(255), nullable=False)
    description = Column(Text, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    status = Column(Enum(FinanceBudgetStatus), default=FinanceBudgetStatus.draft, nullable=False)

    created_at = Column(TIMESTAMP, server_default=utcnow())
    updated_at = Column(TIMESTAMP, server_default=utcnow(), onupdate=utcnow())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    company = relationship("Company", backref="finance_budgets")
    site = relationship("Site", backref="finance_budgets")
    created_by = relationship("User", foreign_keys=[created_by_id])
    line_items = relationship("FinanceBudgetLineItem", back_populates="budget", cascade="all, delete-orphan")
    approvals = relationship("FinanceApproval", back_populates="budget", cascade="all, delete-orphan")


class FinanceBudgetLineItem(Base):
    """Individual line item within a budget."""

    __tablename__ = "finance_budget_line_items"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    budget_id = Column(Integer, ForeignKey("finance_budgets.id", ondelete="CASCADE"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("finance_vendors.id", ondelete="SET NULL"), nullable=True)

    category = Column(Enum(FinanceBudgetCategory), nullable=False)
    description = Column(VARCHAR(500), nullable=True)
    amount_planned = Column(Float, default=0.0, nullable=False)
    amount_authorized = Column(Float, default=0.0, nullable=False)
    amount_actual = Column(Float, default=0.0, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    created_at = Column(TIMESTAMP, server_default=utcnow())
    updated_at = Column(TIMESTAMP, server_default=utcnow(), onupdate=utcnow())

    budget = relationship("FinanceBudget", back_populates="line_items")
    vendor = relationship("FinanceVendor", back_populates="budget_line_items")


class FinanceObligation(Base):
    """Authorization request for payment or commitment."""

    __tablename__ = "finance_obligations"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("finance_vendors.id", ondelete="SET NULL"), nullable=True)
    budget_line_item_id = Column(Integer, ForeignKey("finance_budget_line_items.id", ondelete="SET NULL"), nullable=True)

    obligation_type = Column(Enum(FinanceObligationType), nullable=False)
    description = Column(Text, nullable=True)
    amount_requested = Column(Float, nullable=False)
    requested_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(Enum(FinanceObligationStatus), default=FinanceObligationStatus.draft, nullable=False)
    prerequisite_snapshot = Column(JSON, nullable=True)
    reference_number = Column(VARCHAR(100), nullable=True)

    created_at = Column(TIMESTAMP, server_default=utcnow())
    updated_at = Column(TIMESTAMP, server_default=utcnow(), onupdate=utcnow())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    company = relationship("Company", backref="finance_obligations")
    site = relationship("Site", backref="finance_obligations")
    vendor = relationship("FinanceVendor", back_populates="obligations")
    budget_line_item = relationship("FinanceBudgetLineItem", backref="obligations")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approvals = relationship("FinanceApproval", back_populates="obligation", cascade="all, delete-orphan")


class FinanceApproval(Base):
    """Approval record for an obligation or budget."""

    __tablename__ = "finance_approvals"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    obligation_id = Column(Integer, ForeignKey("finance_obligations.id", ondelete="CASCADE"), nullable=True)
    budget_id = Column(Integer, ForeignKey("finance_budgets.id", ondelete="CASCADE"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    decision = Column(Enum(FinanceApprovalDecision), nullable=False)
    notes = Column(Text, nullable=True)
    override_reason = Column(Text, nullable=True)

    approved_at = Column(TIMESTAMP, server_default=utcnow())

    obligation = relationship("FinanceObligation", back_populates="approvals")
    budget = relationship("FinanceBudget", back_populates="approvals")
    approved_by = relationship("User", foreign_keys=[approved_by_id])


class FinanceActual(Base):
    """Actual financial data imported or entered for variance tracking."""

    __tablename__ = "finance_actuals"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("finance_vendors.id", ondelete="SET NULL"), nullable=True)

    category = Column(Enum(FinanceBudgetCategory), nullable=False)
    description = Column(VARCHAR(500), nullable=True)
    amount = Column(Float, nullable=False)
    transaction_date = Column(Date, nullable=False)
    reference_id = Column(VARCHAR(100), nullable=True)
    source_system = Column(Enum(FinanceActualSource), default=FinanceActualSource.manual, nullable=False)

    created_at = Column(TIMESTAMP, server_default=utcnow())
    updated_at = Column(TIMESTAMP, server_default=utcnow(), onupdate=utcnow())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    company = relationship("Company", backref="finance_actuals")
    site = relationship("Site", backref="finance_actuals")
    vendor = relationship("FinanceVendor", back_populates="actuals")
    created_by = relationship("User", foreign_keys=[created_by_id])
