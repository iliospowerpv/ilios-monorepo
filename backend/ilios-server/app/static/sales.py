"""Sales module static definitions."""

import enum


class SalesStage(enum.Enum):
    """Sales pipeline stages for deal acquisition."""
    prospect = "prospect"
    nda_signed = "nda_signed"
    inputs_received = "inputs_received"
    modeling = "modeling"
    model_review = "model_review"
    model_approved = "model_approved"
    quoted = "quoted"
    term_sheet_neg = "term_sheet_neg"
    term_sheet_signed = "term_sheet_signed"
    phase_1_diligence = "phase_1_diligence"
    mipa_negotiating = "mipa_negotiating"
    mipa_signed = "mipa_signed"
    passed = "passed"
    dead = "dead"


class LifecycleState(enum.Enum):
    """Project lifecycle states controlling module activation."""
    sales_pre_diligence = "Sales / Pre-Diligence"
    due_diligence = "Due Diligence"
    implementation = "Implementation"
    placed_in_service = "Placed in Service"
    operations = "Operations"


class SalesSource(enum.Enum):
    """Source of the sales opportunity."""
    broker = "Broker"
    inbound = "Inbound"
    developer = "Developer"
    outreach = "Outreach"
    referral = "Referral"
    other = "Other"


class NextActionStatus(enum.Enum):
    """Status of the next action."""
    none = "none"
    pending = "pending"
    in_progress = "in_progress"
    blocked = "blocked"
    overdue = "overdue"


HANDOFF_CHECKLIST_ITEMS = [
    "address",
    "system_size_ac",
    "system_size_dc",
    "utility_rate",
    "ownership_structure",
    "offtaker_name",
]

LIFECYCLE_MODULE_ACTIVATION = {
    LifecycleState.sales_pre_diligence: {
        "sales": True,
        "due_diligence": False,
        "implementation": False,
        "operations": False,
        "finance": True,
    },
    LifecycleState.due_diligence: {
        "sales": True,
        "due_diligence": True,
        "implementation": False,
        "operations": False,
        "finance": True,
    },
    LifecycleState.implementation: {
        "sales": True,
        "due_diligence": True,
        "implementation": True,
        "operations": False,
        "finance": True,
    },
    LifecycleState.placed_in_service: {
        "sales": True,
        "due_diligence": True,
        "implementation": True,
        "operations": True,
        "finance": True,
    },
    LifecycleState.operations: {
        "sales": True,
        "due_diligence": True,
        "implementation": True,
        "operations": True,
        "finance": True,
    },
}
