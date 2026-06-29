"""Curated, in-repo product FAQ / knowledge source for the AI Assistant.

This is the ONLY product-knowledge source the assistant grounds help/FAQ answers on — a static,
versioned, human-curated list living in the repository (no external calls, no scraping, no live DB
read). The ``answer_help_faq`` tool returns the most relevant entries; the model phrases the final
answer from them. Keep entries factual and short; expand as the product evolves.
"""
from __future__ import annotations

# Each entry: stable id, a category (for grouping/disclosure), the question/topic, a concise answer,
# and match keywords. Keep answers factual, short, and product-accurate. Expand as the product grows.
FAQ_ENTRIES: list[dict] = [
    # --- Basics -------------------------------------------------------------------------------
    {
        "id": "what-is-ilios",
        "category": "Basics",
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
        "category": "Basics",
        "question": "What is the difference between a Project and a Site?",
        "answer": (
            "They are the same thing. 'Project' is the UI term for what the system stores as a "
            "'Site'. Anywhere you see Project in the interface, it maps to a Site record."
        ),
        "keywords": ["project", "site", "difference", "terminology"],
    },
    {
        "id": "companies-and-projects",
        "category": "Basics",
        "question": "How are companies and projects organized?",
        "answer": (
            "A company groups its projects (sites). The company landing page has Overview, "
            "Projects, Tasks, and Performance tabs. Most data is scoped by company and project, "
            "and what you can see depends on your access to each company."
        ),
        "keywords": ["company", "companies", "organize", "structure", "hub", "landing"],
    },
    # --- Workflows ----------------------------------------------------------------------------
    {
        "id": "guided-onboarding",
        "category": "Workflows",
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
        "category": "Workflows",
        "question": "What are workflows and sequences?",
        "answer": (
            "Workflows are guided wizards for a single task (e.g. add a company, add a project, "
            "upload a document, invite a user). Sequences chain several workflows into a longer "
            "guided flow. Every workflow asks you to review and confirm before it makes any change."
        ),
        "keywords": ["workflow", "workflows", "sequence", "sequences", "wizard"],
    },
    {
        "id": "onboarding-readiness",
        "category": "Workflows",
        "question": "What does onboarding readiness mean?",
        "answer": (
            "Readiness summarizes, per project, how complete the setup is across telemetry health, "
            "due-diligence reconciliation, device eligibility, and the expected baseline. Each "
            "dimension is read-only and shows an honest 'unavailable' when it can't be evaluated. "
            "Ask me to 'explain my readiness' for a live breakdown."
        ),
        "keywords": ["readiness", "ready", "health", "complete", "status", "progress"],
    },
    # --- Due diligence / Data Room ------------------------------------------------------------
    {
        "id": "diligence-onboarding",
        "category": "Diligence",
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
        "id": "data-room",
        "category": "Diligence",
        "question": "What is the Data Room?",
        "answer": (
            "The Data Room is a hybrid document viewer that links AI-extracted fields back to the "
            "source PDF, with search, highlighting, an audit trail, and a sequential verification "
            "workflow where you accept or override extracted values. Accepting a value records it; "
            "it does not by itself change a baseline."
        ),
        "keywords": ["data", "room", "viewer", "extract", "extraction", "ai", "verify", "accept"],
    },
    {
        "id": "promote-and-baseline",
        "category": "Diligence",
        "question": "What does promoting a term or activating a baseline do?",
        "answer": (
            "Promoting moves an accepted term into your project's current assumptions (an active "
            "fact). Activating a baseline turns promoted facts into the expected-performance "
            "reference used by charts and reconciliation. Both are deliberate, human-confirmed "
            "actions you take in the app — the assistant can only point you to them."
        ),
        "keywords": ["promote", "baseline", "activate", "assumptions", "fact", "facts", "current"],
    },
    {
        "id": "reconciliation",
        "category": "Diligence",
        "question": "What is the reconciliation screen?",
        "answer": (
            "Reconciliation is a strictly read-only audit view showing, per field, how far it has "
            "advanced from an uploaded document through AI extraction, acceptance, promotion, and "
            "into the active baseline. It flags only genuine conflicts that need a human decision "
            "and never changes data itself."
        ),
        "keywords": ["reconciliation", "reconcile", "status", "audit", "conflict", "review"],
    },
    {
        "id": "poison-pill",
        "category": "Diligence",
        "question": "What is a poison pill term?",
        "answer": (
            "A poison pill is a contract term flagged as a serious risk. You can manually mark or "
            "unmark a term as a poison pill on a due-diligence document key; a user-set flag takes "
            "precedence over an AI-detected one."
        ),
        "keywords": ["poison", "pill", "risk", "flag", "term", "contract"],
    },
    # --- Telemetry ----------------------------------------------------------------------------
    {
        "id": "telemetry-overview",
        "category": "Telemetry",
        "question": "What does telemetry show?",
        "answer": (
            "Telemetry shows device and site readings (e.g. production) and interval rollups stored "
            "natively in the platform. Charts compare actual production against the expected "
            "baseline when one is defined, and show an honest 'unavailable' rather than a fake zero "
            "when expected can't be computed."
        ),
        "keywords": ["telemetry", "readings", "production", "chart", "actual", "expected", "data"],
    },
    {
        "id": "refresh-telemetry",
        "category": "Telemetry",
        "question": "How do I refresh telemetry for a project?",
        "answer": (
            "On a mapped project's Telemetry tab, use the 'Refresh Telemetry' button. It pulls the "
            "most recent window (defaults to the last 24h) and updates the readings and rollups, "
            "then refreshes the readiness and health panels. Scheduled background refresh is a "
            "separate, opt-in setting."
        ),
        "keywords": ["refresh", "telemetry", "pull", "ingest", "update", "sync"],
    },
    {
        "id": "expected-baseline",
        "category": "Telemetry",
        "question": "What is the expected baseline?",
        "answer": (
            "The expected baseline is the reference for how much a site should produce, derived "
            "from promoted due-diligence facts. Charts use it to show expected vs actual. If the "
            "baseline isn't active or required inputs are missing, expected is reported as "
            "unavailable — never fabricated as zero."
        ),
        "keywords": ["expected", "baseline", "projected", "reference", "performance", "design"],
    },
    # --- Devices ------------------------------------------------------------------------------
    {
        "id": "device-eligibility",
        "category": "Devices",
        "question": "Which devices can be mapped, and which drive expected math?",
        "answer": (
            "Many device types — inverters, modules, meters, loggers, gateways, and weather "
            "sensors — can be mapped and inspected. Only inverters, modules, and weather stations "
            "actually drive the expected-performance math and the health/readiness counts; "
            "expanding what's mappable never changes which devices drive those numbers."
        ),
        "keywords": ["device", "devices", "map", "mappable", "eligible", "inverter", "meter", "gateway"],
    },
    {
        "id": "weather-provenance",
        "category": "Weather",
        "question": "How does the platform handle weather data?",
        "answer": (
            "Weather inputs are tracked with explicit source identity, measurement semantics, and "
            "approval so they're auditable. The platform never guesses what a weather reading means "
            "— unknown semantics stay 'unknown' until a reviewer declares them, and only properly "
            "declared plane-of-array irradiance can drive expected math."
        ),
        "keywords": ["weather", "irradiance", "temperature", "provenance", "semantics", "source"],
    },
    # --- Finance & data -----------------------------------------------------------------------
    {
        "id": "finance-integration",
        "category": "Finance",
        "question": "How does the finance integration work?",
        "answer": (
            "Finance integration is a company-level, read-only connection to external accounting "
            "providers. Credentials are stored encrypted, access is role-based, and incoming data "
            "is normalized and stored with upsert semantics. It reads data in; it does not push "
            "changes back out."
        ),
        "keywords": ["finance", "financial", "integration", "accounting", "provider", "budget", "vendor"],
    },
    {
        "id": "contacts",
        "category": "Data",
        "question": "What is the Contacts system?",
        "answer": (
            "Contacts is a CRM-style directory for external people related to a portfolio, company, "
            "or project. Use it to track who is associated with each entity."
        ),
        "keywords": ["contact", "contacts", "crm", "people", "directory"],
    },
    {
        "id": "project-import",
        "category": "Data",
        "question": "Can I bulk import projects?",
        "answer": (
            "Yes. The Project Import tool is a multi-step wizard (Upload → Map Fields → Validate → "
            "Import) for CSV/XLSX files, with auto-mapping, validation, and duplicate detection."
        ),
        "keywords": ["import", "bulk", "csv", "xlsx", "upload", "projects", "spreadsheet"],
    },
    {
        "id": "archive-restore",
        "category": "Data",
        "question": "How do I archive or restore a company or project?",
        "answer": (
            "Companies and projects support archive/restore via a soft-delete flag, with cascade "
            "archiving. Archiving hides items without permanently deleting them, so they can be "
            "restored."
        ),
        "keywords": ["archive", "restore", "delete", "soft", "hide", "remove"],
    },
    # --- Reporting ----------------------------------------------------------------------------
    {
        "id": "reporting",
        "category": "Reporting",
        "question": "How does reporting work?",
        "answer": (
            "Reporting is powered by PowerBI for sites with data there, with an in-app performance "
            "report as a fallback (for example, demo sites) that generates daily/monthly figures "
            "from the telemetry pipeline."
        ),
        "keywords": ["report", "reporting", "powerbi", "performance", "analytics", "dashboard"],
    },
    # --- Access -------------------------------------------------------------------------------
    {
        "id": "permissions",
        "category": "Admin",
        "question": "How do permissions and access work?",
        "answer": (
            "Access is governed by a multi-company system with granular, module-level permissions "
            "and role profiles. You only see the companies and projects you've been granted access "
            "to, and actions are gated by the permissions for that module."
        ),
        "keywords": ["permission", "permissions", "access", "role", "roles", "authorization", "rights"],
    },
    # --- Assistant ----------------------------------------------------------------------------
    {
        "id": "assistant-limits",
        "category": "Assistant",
        "question": "What can the assistant do (and not do)?",
        "answer": (
            "I can explain available workflows, recommend the next best action, explain onboarding "
            "readiness, and answer product questions — all read-only. I cannot start, advance, or "
            "execute workflows, promote facts, activate baselines, map devices, or change weather "
            "declarations. Those stay with you, confirmed inside the relevant wizard."
        ),
        "keywords": ["assistant", "can", "you", "do", "help", "limits", "able"],
    },
    {
        "id": "assistant-action-cards",
        "category": "Assistant",
        "question": "What are the action cards the assistant shows?",
        "answer": (
            "When I recommend a concrete next step, I may show an action card — an inert shortcut "
            "link into the relevant wizard or run. Clicking it navigates you there so YOU can take "
            "the action; the card never starts or executes anything on its own."
        ),
        "keywords": ["action", "card", "cards", "link", "shortcut", "button"],
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
    return {
        "id": entry["id"],
        "category": entry.get("category"),
        "question": entry["question"],
        "answer": entry["answer"],
    }
