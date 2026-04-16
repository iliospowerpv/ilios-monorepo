"""Acquisitions module static definitions (formerly Sales)."""

import enum


class SalesStage(enum.Enum):
    """Acquisitions pipeline stages for deal acquisition."""
    prospect = "prospect"
    nda_signed = "nda_signed"
    inputs_received = "inputs_received"
    modeling = "modeling"
    model_review = "model_review"
    model_approved = "model_approved"
    quoted = "quoted"
    term_sheet_neg = "term_sheet_neg"
    term_sheet_signed = "term_sheet_signed"
    mipa_negotiating = "mipa_negotiating"
    mipa_signed = "mipa_signed"
    closed_won = "closed_won"
    passed = "passed"
    dead = "dead"


class LifecycleState(enum.Enum):
    """Project lifecycle states controlling module activation."""
    sales_pre_diligence = "sales_pre_diligence"
    due_diligence = "due_diligence"
    implementation = "implementation"
    placed_in_service = "placed_in_service"
    operations = "operations"


class SignedAgreementStatus(enum.Enum):
    """Signed agreement status for project gating."""
    missing = "missing"
    uploaded = "uploaded"
    waived = "waived"


class DocumentKeySource(enum.Enum):
    """Source of extracted document key."""
    ai_extraction = "ai_extraction"
    manual_entry = "manual_entry"


class DocumentKeyStatus(enum.Enum):
    """Status of extracted document key."""
    proposed = "proposed"
    accepted = "accepted"
    overridden = "overridden"
    rejected = "rejected"


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
        "acquisitions": True,
        "data_room": False,
        "implementation": False,
        "operations": False,
        "finance": True,
    },
    LifecycleState.due_diligence: {
        "acquisitions": True,
        "data_room": True,
        "implementation": False,
        "operations": False,
        "finance": True,
    },
    LifecycleState.implementation: {
        "acquisitions": True,
        "data_room": True,
        "implementation": True,
        "operations": False,
        "finance": True,
    },
    LifecycleState.placed_in_service: {
        "acquisitions": True,
        "data_room": True,
        "implementation": True,
        "operations": True,
        "finance": True,
    },
    LifecycleState.operations: {
        "acquisitions": True,
        "data_room": True,
        "implementation": True,
        "operations": True,
        "finance": True,
    },
}

CONVERSION_ELIGIBLE_STAGES = [
    SalesStage.term_sheet_signed,
    SalesStage.mipa_signed,
]
