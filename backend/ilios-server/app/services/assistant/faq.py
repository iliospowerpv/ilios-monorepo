"""Curated, in-repo product FAQ / knowledge source for the AI Assistant.

This is the ONLY product-knowledge source the assistant grounds help/FAQ answers on — a static,
versioned, human-curated list living in the repository (no external calls, no scraping, no live DB
read). The ``answer_help_faq`` tool returns the most relevant entries; the model phrases the final
answer from them. Keep entries factual and short; expand as the product evolves.
"""
from __future__ import annotations

# Each entry: stable id, the question/topic, a concise answer, and match keywords.
FAQ_ENTRIES: list[dict] = [
    {
        "id": "what-is-ilios",
        "question": "What is iliOS?",
        "answer": (
            "iliOS is a real estate asset investment management platform covering the full "
            "lifecycle of an investment: acquisition and due diligence, asset management, "
            "financial tracking, telemetry, and reporting."
        ),
        "keywords": ["what", "ilios", "platform", "about", "overview"],
    },
    {
        "id": "project-vs-site",
        "question": "What is the difference between a Project and a Site?",
        "answer": (
            "They are the same thing. 'Project' is the UI term for what the system stores as a "
            "'Site'. Anywhere you see Project in the interface, it maps to a Site record."
        ),
        "keywords": ["project", "site", "difference", "terminology"],
    },
    {
        "id": "guided-onboarding",
        "question": "How do I get started / onboard a new portfolio?",
        "answer": (
            "Use a guided sequence from the Workflow area. The 'onboarding' and 'portfolio_setup' "
            "sequences walk you through adding a company, adding its first project (site), and "
            "inviting teammates. Ask me 'what should I do next?' for live, account-specific steps."
        ),
        "keywords": ["start", "onboard", "onboarding", "begin", "setup", "new", "portfolio"],
    },
    {
        "id": "workflows-overview",
        "question": "What are workflows and sequences?",
        "answer": (
            "Workflows are guided wizards for a single task (e.g. add a company, add a project, "
            "upload a document, invite a user). Sequences chain several workflows into a longer "
            "guided flow. Every workflow asks you to review and confirm before it makes any change."
        ),
        "keywords": ["workflow", "workflows", "sequence", "sequences", "wizard"],
    },
    {
        "id": "diligence-onboarding",
        "question": "How do I add due-diligence terms to a project?",
        "answer": (
            "Open the project and use the document_upload workflow to add a source document, then "
            "review the extracted terms in the Data Room. Promoting terms and activating baselines "
            "are deliberate, human-confirmed steps — the assistant can point you to them but cannot "
            "perform them."
        ),
        "keywords": ["diligence", "due", "document", "upload", "terms", "facts", "data room"],
    },
    {
        "id": "onboarding-readiness",
        "question": "What does onboarding readiness mean?",
        "answer": (
            "Readiness summarizes, per project, how complete the setup is across telemetry health, "
            "due-diligence reconciliation, device eligibility, and the expected baseline. Each "
            "dimension is read-only and shows an honest 'unavailable' when it can't be evaluated. "
            "Ask me to 'explain my readiness' for a live breakdown."
        ),
        "keywords": ["readiness", "ready", "health", "complete", "status", "progress"],
    },
    {
        "id": "assistant-limits",
        "question": "What can the assistant do (and not do)?",
        "answer": (
            "I can explain available workflows, recommend the next best action, explain onboarding "
            "readiness, and answer product questions — all read-only. I cannot start, advance, or "
            "execute workflows, promote facts, activate baselines, map devices, or change weather "
            "declarations. Those stay with you, confirmed inside the relevant wizard."
        ),
        "keywords": ["assistant", "can", "you", "do", "help", "limits", "able"],
    },
]


def search_faq(query: str, *, limit: int = 4) -> list[dict]:
    """Return up to ``limit`` FAQ entries most relevant to ``query`` (simple keyword overlap).

    Read-only and deterministic. On an empty/over-generic query, returns the leading entries so the
    assistant always has grounding material rather than nothing.
    """
    cap = max(1, min(int(limit or 4), len(FAQ_ENTRIES)))
    tokens = {t for t in "".join(c.lower() if c.isalnum() else " " for c in (query or "")).split() if t}
    if not tokens:
        return [_public(e) for e in FAQ_ENTRIES[:cap]]

    scored: list[tuple[int, int, dict]] = []
    for idx, entry in enumerate(FAQ_ENTRIES):
        hay = set(entry["keywords"]) | set(entry["question"].lower().split())
        score = sum(1 for t in tokens if any(t in h or h in t for h in hay))
        if score:
            scored.append((score, -idx, entry))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    if not scored:
        return [_public(e) for e in FAQ_ENTRIES[:cap]]
    return [_public(e) for _, _, e in scored[:cap]]


def _public(entry: dict) -> dict:
    return {"id": entry["id"], "question": entry["question"], "answer": entry["answer"]}
