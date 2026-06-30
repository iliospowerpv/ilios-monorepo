"""Static, page-aware suggested prompts for the AI Assistant (Slice 3).

These are pure UI affordances: a deterministic mapping from a coarse route "bucket" to a few example
questions a user might ask there. They carry NO live/business state, perform NO data fetch, and make
NO assertions about the account — they only help a user discover what they can ask. The assistant
still resolves every real answer through its authz-scoped read-only tools.
"""
from __future__ import annotations

# Each bucket: an ordered list of (label, prompt) example questions. ``label`` is the short chip
# text; ``prompt`` is the full question sent to the assistant when the chip is clicked.
_GENERAL: list[tuple[str, str]] = [
    ("What should I do next?", "What should I do next?"),
    ("Explain my readiness", "Explain my onboarding readiness."),
    ("Summarize a project", "Summarize a project's status across telemetry, diligence, weather, and devices."),
    ("What can you do?", "What can you do, and what can't you do?"),
    ("What is iliOS?", "Give me a quick overview of what iliOS does."),
]

# Workflow Companion bucket — surfaced ONLY when the user is inside a guided workflow run (the FE
# context carries an active run_id). These are step-aware example questions the assistant answers by
# grounding in the run via the read-only get_workflow_run tool. Like every other bucket they are pure
# UI affordances: no data fetch, no account assertions, and the assistant never executes anything.
_COMPANION: list[tuple[str, str]] = [
    ("Explain this step", "Explain the step I'm on in this workflow — what it's for and what each field means."),
    ("What does each field mean?", "What does each field on this step mean, and which ones are required?"),
    ("Why did my entry fail?", "Why did my last entry fail validation, and how do I fix it?"),
    ("What happens when I confirm?", "What will the final confirm step of this workflow do when I run it?"),
    ("How do I resume later?", "If I stop now, how do I resume this workflow later?"),
    ("Is anything blocking me?", "Is anything blocking me from completing this workflow?"),
]

# Ordered route-prefix → prompts. First matching prefix wins, so list more specific prefixes first.
_ROUTE_BUCKETS: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "/workflows",
        "Workflows",
        [
            ("Which workflows can I run?", "Which workflows are available to me right now?"),
            ("What are sequences?", "What are sequences and which should I use to onboard?"),
            ("Resume a run", "Do I have any in-progress runs I should resume?"),
            ("What should I do next?", "What should I do next?"),
        ],
    ),
    (
        "/data-room",
        "Data Room",
        [
            ("What is the Data Room?", "What is the Data Room and how does it work?"),
            ("How do I add terms?", "How do I add due-diligence terms to this project?"),
            ("Promote vs activate", "What's the difference between promoting a term and activating a baseline?"),
            ("What needs review?", "What due-diligence items still need my review?"),
            ("Summarize diligence", "Summarize this project's due-diligence reconciliation and active facts."),
        ],
    ),
    (
        "/telemetry",
        "Telemetry",
        [
            ("What does telemetry show?", "What does the telemetry data show for this project?"),
            ("How do I refresh telemetry?", "How do I refresh telemetry for this project?"),
            ("What is the expected baseline?", "What is the expected baseline and is one active here?"),
            ("Why is expected unavailable?", "Why might expected production show as unavailable?"),
            ("Summarize telemetry", "Summarize this project's telemetry health, weather readiness, and expected vs actual energy."),
        ],
    ),
    (
        "/acquisitions",
        "Acquisitions",
        [
            ("Explain the deal pipeline", "How does the acquisitions deal pipeline work?"),
            ("What should I do next?", "What should I do next on my deals?"),
            ("What is due diligence?", "How does due diligence fit into acquisitions?"),
        ],
    ),
    (
        "/project-hub",
        "Project Hub",
        [
            ("Explain this project's readiness", "Explain this project's onboarding readiness."),
            ("What should I do next?", "What should I do next on this project?"),
            ("How do devices map?", "Which devices can be mapped and which drive expected math?"),
            ("How do I refresh telemetry?", "How do I refresh telemetry for this project?"),
            ("Summarize this project", "Give me a full summary of this project across telemetry, diligence, weather, and devices."),
        ],
    ),
    (
        "/companies",
        "Companies",
        [
            ("Onboard a new project", "How do I add a new project to this company?"),
            ("What should I do next?", "What should I do next for this company?"),
            ("Invite a teammate", "How do I invite a teammate to this company?"),
        ],
    ),
    (
        "/due-diligence",
        "Due Diligence",
        [
            ("What is due diligence?", "What is the due-diligence process and how does it work here?"),
            ("What needs review?", "What due-diligence items still need my review?"),
            ("Promote vs activate", "What's the difference between promoting a term and activating a baseline?"),
            ("Summarize diligence", "Summarize this project's due-diligence reconciliation and active facts."),
        ],
    ),
    # `/operations-and-maintenance` must precede no other prefix here, but keep it ahead of any future
    # shorter `/operations` token; it is its own coarse module.
    (
        "/operations-and-maintenance",
        "Operations & Maintenance",
        [
            ("What is O&M?", "What does the Operations & Maintenance module cover?"),
            ("Explain device health", "How do I read device health and alerts for this project?"),
            ("Summarize this project", "Summarize this project's telemetry health, weather readiness, and devices."),
            ("What should I do next?", "What should I do next in Operations & Maintenance?"),
        ],
    ),
    (
        "/finance",
        "Finance",
        [
            ("What does Finance cover?", "What can I do in the Finance module?"),
            ("Explain budgeting", "How does budgeting and capital governance work here?"),
            ("How do vendors work?", "How does vendor management work in Finance?"),
            ("What should I do next?", "What should I do next in Finance?"),
        ],
    ),
    (
        "/reports",
        "Reporting",
        [
            ("What reports are available?", "Which reports can I view here?"),
            ("Explain performance reporting", "What does the performance report show and where does its data come from?"),
            ("What should I do next?", "What should I do next with reporting?"),
        ],
    ),
    # `/portfolio-admin` is a settings surface; list it BEFORE `/portfolio` so the broader portfolio
    # prefix never swallows the admin route.
    (
        "/portfolio-admin",
        "Settings & Admin",
        [
            ("What can admins do here?", "What can I manage from the admin and settings area?"),
            ("Explain access & roles", "How do roles and access control work in iliOS?"),
            ("What should I do next?", "What should I do next as an administrator?"),
        ],
    ),
    (
        "/portfolio",
        "Portfolio",
        [
            ("Summarize my portfolio", "Summarize my portfolio's status across telemetry, diligence, weather, and devices."),
            ("Which projects need attention?", "Which of my projects need attention right now?"),
            ("What should I do next?", "What should I do next across my portfolio?"),
        ],
    ),
    (
        "/settings",
        "Settings & Admin",
        [
            ("What can I change here?", "What can I manage from settings?"),
            ("Explain access & roles", "How do roles and access control work in iliOS?"),
            ("What should I do next?", "What should I do next in settings?"),
        ],
    ),
    (
        "/home",
        "Workspace",
        [
            ("What should I do next?", "What should I do next across my projects?"),
            ("Explain my readiness", "Explain my onboarding readiness."),
            ("Summarize my work", "Summarize the status of my projects across telemetry, diligence, weather, and devices."),
            ("What can you do?", "What can you do, and what can't you do?"),
        ],
    ),
]


def _normalize(route: str | None) -> str:
    return (route or "").strip().lower()


def get_suggested_prompts(
    route: str | None, *, in_workflow: bool = False
) -> tuple[str | None, list[dict]]:
    """Return ``(context_label, prompts)`` for a route. Falls back to general prompts.

    When ``in_workflow`` is true (the FE context carries an active workflow run_id), returns the
    step-aware Workflow Companion prompts regardless of route. Deterministic and side-effect free;
    ``prompts`` are JSON-serializable dicts.
    """
    if in_workflow:
        return "Workflow Companion", [
            {"label": p_label, "prompt": p_prompt} for p_label, p_prompt in _COMPANION
        ]
    normalized = _normalize(route)
    for prefix, label, prompts in _ROUTE_BUCKETS:
        if normalized.startswith(prefix):
            return label, [{"label": p_label, "prompt": p_prompt} for p_label, p_prompt in prompts]
    return None, [{"label": label, "prompt": prompt} for label, prompt in _GENERAL]
