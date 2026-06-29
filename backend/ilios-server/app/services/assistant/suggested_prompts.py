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
    ("What can you do?", "What can you do, and what can't you do?"),
    ("What is iliOS?", "Give me a quick overview of what iliOS does."),
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
]


def _normalize(route: str | None) -> str:
    return (route or "").strip().lower()


def get_suggested_prompts(route: str | None) -> tuple[str | None, list[dict]]:
    """Return ``(context_label, prompts)`` for a route. Falls back to general prompts.

    Deterministic and side-effect free. ``prompts`` are JSON-serializable dicts.
    """
    normalized = _normalize(route)
    for prefix, label, prompts in _ROUTE_BUCKETS:
        if normalized.startswith(prefix):
            return label, [{"label": p_label, "prompt": p_prompt} for p_label, p_prompt in prompts]
    return None, [{"label": label, "prompt": prompt} for label, prompt in _GENERAL]
