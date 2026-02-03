"""Finance module static enums and constants."""

from app.static.messages import BaseMessageEnum


class FinanceVendorType(BaseMessageEnum):
    epc = "EPC"
    om = "O&M"
    insurance = "Insurance"
    utility = "Utility"
    engineering = "Engineering"
    legal = "Legal"
    accounting = "Accounting"
    other = "Other"


class FinanceObligationType(BaseMessageEnum):
    milestone = "Milestone"
    invoice = "Invoice"
    retainer = "Retainer"
    change_order = "Change Order"
    service_call = "Service Call"
    other = "Other"


class FinanceObligationStatus(BaseMessageEnum):
    draft = "Draft"
    submitted = "Submitted"
    approved = "Approved"
    rejected = "Rejected"
    paid_external = "Paid (External)"
    canceled = "Canceled"


class FinanceBudgetStatus(BaseMessageEnum):
    draft = "Draft"
    submitted = "Submitted"
    approved = "Approved"
    rejected = "Rejected"
    active = "Active"
    closed = "Closed"


class FinanceBudgetCategory(BaseMessageEnum):
    development = "Development"
    construction = "Construction"
    interconnection = "Interconnection"
    permitting = "Permitting"
    equipment = "Equipment"
    labor = "Labor"
    engineering = "Engineering"
    legal = "Legal"
    insurance = "Insurance"
    om = "O&M"
    administrative = "Administrative"
    contingency = "Contingency"
    other = "Other"


class FinanceApprovalDecision(BaseMessageEnum):
    approved = "Approved"
    rejected = "Rejected"
    override = "Override"


class FinanceActualSource(BaseMessageEnum):
    manual = "Manual"
    quickbooks = "QuickBooks"
    gravity = "Gravity"
    other = "Other"
