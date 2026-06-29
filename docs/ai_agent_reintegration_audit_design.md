# AI Agent Reintegration — Product Intent, Legacy Audit, and Native Architecture Design

> **Sprint type: AUDIT / DESIGN ONLY. No production code was changed.** This document
> is the sole deliverable. It traces the legacy AI-agent code, evaluates it against the
> intended product role, and designs a native, well-governed Ilios AI assistant. Nothing
> here is wired into the running app; every "proposed" item is a design, not an
> implementation.

## Build-status legend

| Tag | Meaning |
|---|---|
| `[EXISTS-NATIVE]` | Already built the way we want to keep building (reference pattern). |
| `[LEGACY]` | Built by prior developers; depends on external GCP plumbing; candidate for replacement/retirement. |
| `[PROPOSED]` | Designed in this document; not built. |

## Scope guardrails (what this sprint deliberately does NOT touch)

- **No production code changes** — design only.
- **`InAppParsingService`** (document parsing) is a **separate concern** and is explicitly
  *not* the legacy agent. It is the **reference pattern** we want the new assistant to
  follow (Replit AI gateway, registry-driven prompts, idempotency, audit). It is left
  exactly as-is.
- **Weatherstack `ilios-services`** and the native weather/telemetry stacks are untouched
  and out of scope.
- The injected task list (T001–T012, "Entity Directory") and the `#84` inventory follow-up
  are unrelated to this sprint and are ignored.
- **The "Site" backend entity is never renamed** (per `replit.md`); "Project" stays a UI
  term only.

---

## 1. Legacy AI code inventory

The legacy conversational agent is a **per-site, document-scoped Retrieval-Augmented
Generation (RAG) Q&A chatbot**, surfaced inside the Data Room / Due Diligence module. It
is split across three deployable units: the React frontend, the `ilios-server` "glue"
layer, and a **separate Python service `ilios-DocAI`** that holds the actual LLM/RAG
"brain". It is wired to **external GCP Cloud Functions** via `*_function_url` settings.

### 1.1 Frontend entry points `[LEGACY]`

| File | Role |
|---|---|
| `frontend/rea-investment-fe/src/modules/due-diligence/DueDiligenceModuleContainer.tsx` | Injects `<AIAssistant />` into every Due Diligence page (module-scoped, not global). |
| `frontend/rea-investment-fe/src/modules/due-diligence/components/AIAssistant.tsx` | The chat widget: floating action button, message state, **WebSocket** to the AI server via `REACT_APP_CHATBOT_ENDPOINT`. |
| `frontend/rea-investment-fe/src/modules/due-diligence/components/AIAssistantTopBar.tsx` | Chat header (reset / collapse / close session). |
| `frontend/rea-investment-fe/src/modules/due-diligence/components/AIAssistantActionConfirmationDialog.tsx` | An **early action-confirmation dialog** — evidence a prior dev began an "AI takes an action, user confirms" pattern. Scope/wiring is shallow and document-centric; treat as a UX seed, not a governance framework. |
| `frontend/rea-investment-fe/src/api/due-diligence.ts` | Client interfaces for the chat session token (`*SessionQueryArgs/Response`). |

### 1.2 `ilios-server` glue layer `[LEGACY]`

| File | Role |
|---|---|
| `backend/ilios-server/app/routers/due_diligence/chatbot.py` | `chatbot_router`: issues a **session token** (`GET …/due-diligence/chatbot/{site_id}/session…`), records the conversation. |
| `backend/ilios-server/app/helpers/chatbot/session_maker.py` | Calls the external `chatbot_session_token_function_url` (a GCP Cloud Function) to mint a token. |
| `backend/ilios-server/app/helpers/chatbot/files_sync.py` | `…FilesSyncer`: background-task sync of Data Room files to the AI's storage (upload / mark-actual / delete) via GCP function URLs. Invoked from `due_diligence/files.py`. |
| `backend/ilios-server/app/crud/chatbot.py` | `…ConversationsCRUD`: persists conversation metadata. |
| `backend/ilios-server/app/schema/chatbot.py` | Session-token Pydantic schema. |
| `backend/ilios-server/app/models/chatbot.py` | `chatbot_conversations` table (user_id, site_id, company_id, conversation_id). |
| `backend/ilios-server/alembic/versions/18d250e4b4ca_define_chatbot_conversations.py` | Migration that created the table (applied). |
| `backend/ilios-server/app/settings.py` | `…_function_url` setting (the chatbot session-token Cloud Function). |
| `backend/ilios-server/app/main.py` / `…/routers/__init__.py` | Registers `chatbot_router`. |
| `backend/ilios-server/tests/unit/due_diligence/chatbot_test.py` | Tests for the session-token endpoint (success / 403 / 404 / AI-call-error). |

### 1.3 `ilios-DocAI` service — the agent "brain" `[LEGACY]`

Present at `docai/ilios-DocAI/` **and** `backend/ilios-DocAI/` (two copies; confirm which
deploys before any retirement).

| File / dir | Role |
|---|---|
| `…/src/deployment/fast_api/chatbot.py` | FastAPI service: `/get_token` (handshake) + `/chat` (**WebSocket**). Instantiates `ChatbotBase`. |
| `…/src/chatbot/main.py`, `…/src/chatbot/modules/base.py` | `ChatbotBase`: query classification → context retrieval (SQL over structured project data **or** RAG over vectorized docs) → answer. |
| `…/src/chatbot/modules/{classification,clarification,state,messages,memory_summarization}.py` | Intent classification, clarifying-question generation, conversation state, message history, long-context summarization. |
| `…/src/chatbot/prompt_templates/{base,classification,clarification}.py` | System prompt, RAG/format templates, intent-classification and clarification prompts. |
| `…/src/chatbot/validation/{pipeline,metrics,llm_validation}.py` | Answer-validation pipeline + quality metrics. |
| `…/src/vectordb/pg_vector/*`, `…/src/vectordb/chromadb/chatbot_db.py` | Vector stores (pgvector + ChromaDB) for document retrieval; `document_embeddings` table, separate `*-documents` DB. |
| `…/src/user_interface/pages/Chatbot.py` | **Standalone Streamlit demo UI** — `[LEGACY, ORPHANED]`, not used by the React app. |
| `…/notebooks/*chatbot*.ipynb` | Dev/eval notebooks — `[LEGACY, ORPHANED]`. |

### 1.4 Cross-cutting dependencies `[LEGACY]`

- **Auth/permissions**: the session-token endpoint enforces standard site authorization
  (a 403 test exists), but the **DocAI `/chat` service itself does no Ilios permission
  checks** — it trusts the minted token and answers from whatever context it retrieved.
- **Audit logs**: only the conversation row is recorded; **individual messages/answers
  are not written to the Ilios `audit_logs` trail.**
- **Task creation / mutations**: **none.** The legacy agent has **no write/action tools**.
  Its only "tools" are *read* context selectors (SQL vs RAG). It cannot create tasks,
  promote facts, or change anything.
- **Document interaction**: one-way — Data Room files are pushed into the AI's vector
  store via `files_sync.py`; the agent reads embeddings, it does not write back.
- **Help/FAQ access**: **none** — the agent has no connection to the in-app Help Center.
- **Background jobs**: file sync runs as FastAPI `background_tasks`.
- **Third-party**: GCP Cloud Functions (`*_function_url`), Google VertexAI/Gemini +
  LangChain, ChromaDB + pgvector, `ml_api_key`, WebSocket transport, GCP Secret Manager
  for the vector DB creds. Terraform under `infra/ilios-infra/**` provisions the vector
  store and `*-documents` DB.

### 1.5 What the legacy agent is — and is not

- **Is**: a single-site, Data-Room-only, **read-only document/project Q&A** RAG bot on a
  separate GCP-hosted service.
- **Is not**: a cross-module navigator, a help/education layer, or a **permission-aware
  action executor**. It satisfies **roughly one** of the four intended roles
  (education/Q&A) and only within the Data Room.

---

## 2. Recommendation: reuse, isolate, or replace

**Headline: REPLACE the conversational layer with a native Ilios assistant; ISOLATE then
retire the legacy GCP/DocAI plumbing behind a flag; SALVAGE (later, optional) only the
document-RAG *capability* as one native read tool. Keep `InAppParsingService` untouched.**

| Legacy component | Verdict | Rationale |
|---|---|---|
| DocAI `/chat` service, vector stores, GCP Cloud Functions, WebSocket handshake | **Replace** | External GCP dependency is the exact "legacy brittleness" pattern the platform is moving off (cf. `InAppParsingService` already replaced GCP parsing). No permission enforcement at the chat tier. Cannot host actions/wizards safely. |
| `chatbot.py` router, `helpers/chatbot/*`, `crud/chatbot.py`, `schema/chatbot.py` | **Isolate → retire** | Glue to the GCP service. Put behind an off-by-default flag, then remove once the native assistant ships. Keep `chatbot_conversations` until migration is decided. |
| `AIAssistant.tsx` / `AIAssistantTopBar.tsx` | **Replace** | New assistant is global and action-capable; WebSocket-to-GCP transport is dropped in favor of native HTTP/SSE. |
| `AIAssistantActionConfirmationDialog.tsx` | **Salvage as UX seed** | Good instinct; rebuild on the formal confirmation framework (§6). |
| Document-RAG capability (embeddings + retrieval) | **Salvage later (optional)** | Re-expose as a single native, permission-checked read tool (`search_documents`) — *not* by reusing the GCP service. Defer to a later phase. |
| `InAppParsingService` + Extraction Registry | **Keep / reference** | `[EXISTS-NATIVE]`. The template for the new assistant: Replit AI gateway, registry-driven prompts, tenacity retries, idempotency, audit. |

**Why replace rather than reuse:** the intended role (navigation + education +
**permission-aware actions** + **multi-step wizards**) requires (a) tight coupling to the
Ilios permission resolver and audit trail on **every action**, and (b) a tool layer that
calls **existing Ilios APIs**. The legacy agent has neither, lives off-platform on GCP,
and would have to be substantially rebuilt to add them — at which point we are building
native anyway, but on a worse foundation.

---

## 3. Proposed native architecture `[PROPOSED]`

A new first-party **Assistant** module inside `ilios-server`, mirroring the native parsing
stack, with the LLM reached through the **Replit AI Integrations gateway** (same gateway,
keys, and `gpt-5.2` model family already used by `InAppParsingService`).

```
Browser (global Assistant panel)
   │  HTTP + SSE (no WebSocket, no GCP)
   ▼
ilios-server  /api/assistant/*           ← standard JWT/session auth, same as every route
   ├── AssistantService        orchestration: turn loop, LLM calls, tool dispatch
   ├── Tool Registry           declarative tools; each binds to an EXISTING Ilios API + permission
   ├── Confirmation Engine     plan → confirm → execute (two-phase) for all writes
   ├── Wizard Engine           resumable multi-step state machines over the same tools
   ├── Knowledge Provider      retrieval over the in-app Help Center + nav map (grounding)
   └── Audit bridge            _create_audit_log(source="ai_assistant") on every action
        │
        ▼
   Replit AI gateway (OpenAI, gpt-5.2)  ← function/tool-calling
```

**Core principles**

1. **The assistant is a *client of the same APIs the UI uses.*** It never touches the DB
   directly and never gets a privileged service account — it acts strictly **as the
   logged-in user**, through the same guards.
2. **Plan, don't act.** The LLM proposes tool calls; the backend decides whether a call is
   read (auto-run) or write (requires explicit user confirmation, §6).
3. **Grounded, not free-form.** Navigation and help answers are grounded in real route
   config and curated Help Center content, with citations — minimizing hallucination.
4. **Native, no GCP.** No Cloud Functions, no external chat service, no new secret beyond
   the existing AI-gateway credentials.

---

## 4. Permission model `[PROPOSED]`

The assistant introduces **no new privilege**. It reuses the canonical resolver and the
existing guards verbatim.

- **Identity**: every `/api/assistant/*` request carries the user's normal JWT/session;
  the assistant has **no independent credentials**.
- **Per-tool enforcement (defense in depth)**: each tool declares the **same** dependency
  the underlying endpoint uses, and the backend re-checks it at execution time:
  - hierarchical project access via `get_authorized_site` / `resolve_effective_access`
    (Portfolio→Company→Project, restrict-only, intersection semantics);
  - module/action checks against `PermissionsModules` × `PermissionsActions`
    (`assets_management`, `diligence`, `finance`, `reporting`, `telemetry`, `settings`,
    `onm` × `view|edit|admin`); `edit` implies `view` via existing normalization;
  - specialized guards where applicable (`telemetry_admin_required`), and
    `_enforce_company_visibility` (404-on-mismatch, to avoid leaking entity existence).
- **Fail-closed**: unknown tool, missing permission, ambiguous scope, or unverifiable
  company visibility → **refuse** and explain; never "best-effort" execute.
- **Capability discovery, not bypass**: the assistant may *ask the resolver* what the user
  can do (to avoid offering impossible actions), but the **authoritative** check is the
  guard on the execute call. The UI hiding a button is never the security boundary.
- **No cross-tenant context**: retrieval and tool results are filtered to the user's
  visible companies/sites; conversation memory is scoped to the user.

---

## 5. Action / tool model `[PROPOSED]`

Tools are **declarative** and registry-driven (mirroring the Extraction Registry idea).
Every tool is one of two classes:

- **Read tools** (`READ`) — no side effects; auto-run after permission check.
- **Write tools** (`WRITE`) — propose a mutation; **never** auto-run; require the
  confirmation flow (§6) and audit (§9).

**Tool descriptor (every tool carries this):**

```
name                 e.g. "create_task"
class                READ | WRITE
description          natural-language, shown to the LLM
args_schema          JSON Schema (validated before execution)
required_permission  module:action (+ scope: site|company)  ← reused guard
backing_api          the existing endpoint it calls (no new mutation logic)
idempotency_key      for WRITE tools (dedupe double-confirm)
confirmation         none (READ) | standard (WRITE) | governed (hard-gated, §6/§10)
preview_builder      produces the human-readable diff/summary for confirmation
audit_action         the audit action string written on execute
```

**Initial tool catalog (all map to APIs surfaced in the audit):**

| Tool | Class | Backing API | Permission |
|---|---|---|---|
| `navigate_to` | READ | client route table (`App.tsx`/`NavMenu`) | n/a (UI nav) |
| `search_help` / `explain_concept` | READ | Help Center content (`src/content/help/*`) | n/a |
| `list_my_projects` / `get_project_overview` | READ | workspace / site read endpoints | `assets:view` |
| `get_reconciliation` / `get_inventory_reconciliation` | READ | `GET …/sites/{id}/inventory-reconciliation` | `assets:view` |
| `search_documents` *(later, salvaged RAG)* | READ | native doc search/embeddings | `diligence:view` |
| `create_task` | WRITE (standard) | `POST /api/task-tracker/boards/{board_id}/tasks` | `diligence:edit` or `onm:edit` |
| `create_company` | WRITE (standard) | `POST /api/companies/` | platform admin |
| `create_site` | WRITE (standard) | `POST /api/sites/` | `assets_management:edit` |
| `create_provider_account` / `map_site` | WRITE (standard) | `POST …/provider-accounts`, `PUT …/sites/{id}/mapping` | `settings:edit` / `telemetry_admin` |
| `upload_document` | WRITE (standard) | `POST …/documents/{id}/upload` | `diligence:edit` |
| `accept_extracted_facts` | WRITE (standard) | `POST …/files/{id}/bulk-accept/` | `diligence:edit` |
| `promote_facts` | WRITE (**governed**) | `POST /api/projects/{site_id}/assumptions/promote` | `diligence:edit` |
| `create_draft_baseline` | WRITE (standard) | `POST …/expected-baseline/create-draft-from-facts` | `telemetry_admin` |
| `activate_baseline` / `supersede_baseline` | WRITE (**governed**) | `POST …/expected-baselines/{id}/approve` → `…/activate` | `telemetry_admin` **+ baseline-lifecycle authority** (company-admin / platform bypass, via `enforce_baseline_lifecycle_authority`) |
| `map_device` | WRITE (**governed**) | `POST /api/telemetry/v2/sites/{site_id}/device-mappings` | `settings:edit` (+ company-admin on the site) |
| `declare_weather_semantics` | WRITE (**governed**) | weather declaration endpoint | `telemetry_admin` |
| `export_report` | WRITE (standard) | `POST …/reports/{id}/export-to-file` | `reporting:view` |

The LLM may **only** select tools in the registry. It cannot invent endpoints, run SQL, or
escalate a READ tool into a WRITE.

---

## 6. Confirmation rules `[PROPOSED]`

**Two-phase commit for every mutation.** The assistant may *draft, prefill, validate,
explain, and summarize*, but the actual write happens only after explicit user
confirmation, through the normal authorized endpoint, with an audit entry.

```
Phase 1 — PLAN
  LLM proposes WRITE tool + args
  → backend validates args (schema) + permission (fail-closed)
  → preview_builder renders a human-readable summary / diff (no write yet)
  → returns a Confirmation Card to the UI

Phase 2 — EXECUTE (only on explicit user click)
  user reviews card → clicks Confirm
  → backend re-checks permission + idempotency
  → calls the existing endpoint (same path the UI uses)
  → writes audit (source="ai_assistant", who confirmed, before/after)
  → returns result + a link to the changed entity
```

**Two confirmation tiers:**

1. **Standard WRITE** — one explicit confirm click on the card (e.g. create task, create
   site, upload document, create draft baseline, export report).
2. **Governed WRITE** — the **hard-governance list** (§10). These additionally:
   - show the **downstream impact** (e.g. "this changes expected output / operational
     truth"), require any **rationale** the underlying endpoint already enforces (e.g.
     baseline-driving override rationale), and respect existing **fail-closed server
     guards** (e.g. baseline-activation validation 409, promotion freshness 409). The
     assistant **surfaces** those guards; it never bypasses or pre-satisfies them.
   - are **never** batchable into an "accept all" — each governed action is confirmed on
     its own.

**Absolute rule:** there is **no configuration, prompt, or "auto mode" that lets a governed
action execute without an explicit human confirmation.** A governed tool with
`auto_execute=true` is a design error and must be rejected by the engine.

---

## 7. Wizard workflow model `[PROPOSED]`

Long multi-step processes run as **resumable state machines** over the same tools, with
the same permission + confirmation guarantees. The AI prefills and validates; the user
advances and confirms; only the terminal (or per-step) mutation calls a WRITE tool.

**Wizard descriptor:** `id`, ordered `steps[]`, each step = `{ prompt, inputs, validators,
prefill_source, tool? }`, plus `resume_token` (persisted progress) and
`final_confirmation`.

**Step lifecycle:** `collect → prefill (from context/facts) → validate → preview →
confirm → execute (WRITE tool) → next`. A wizard can be paused and resumed; nothing is
written until a step's confirm.

**The ten target wizards (each reuses existing APIs):**

| Wizard | Terminal/step tools | Governed step? |
|---|---|---|
| Add a company | `create_company` | no |
| Add a site/project | `create_site` | no |
| Onboard telemetry | `create_provider_account` → `map_site` | `map_device` (governed) if reached |
| Upload diligence documents | `upload_document` | no |
| Review extracted facts | `accept_extracted_facts` | no (acceptance ≠ promotion) |
| Create project facts | `accept_extracted_facts` → `promote_facts` | **promote_facts (governed)** |
| Create draft baselines | `create_draft_baseline` (+ later `activate_baseline`) | **activate (governed)** |
| Reconcile inventory | read recon → `create_task` for gaps | no (read + task only) |
| Assign tasks | `create_task` | no |
| Generate reports | `export_report` | no |

Wizards **never** silently chain governed actions; e.g. "create project facts" stops and
asks for explicit confirmation before `promote_facts`, and "create draft baseline" never
auto-activates.

---

## 8. Help / FAQ knowledge model `[PROPOSED]`

Ground education and navigation in **existing curated content**, not free generation.

- **Sources** (already in the repo):
  - Help articles: `frontend/rea-investment-fe/src/content/help/articles/*` (home,
    getting-started, project-hub, data-room, acquisitions, finance, o-and-m, tasks,
    reports, portfolio-admin, concepts, reference, troubleshooting).
  - FAQ: `…/content/help/faq.ts`; glossary: `…/content/help/glossary.ts`;
    index/types: `…/content/help/index.ts`, `types.ts`.
  - Navigation map: route hierarchy in `src/App.tsx` and the module menu in
    `components/layout/NavMenu/NavMenu.tsx` (Home, Acquisitions, Project Hub, Data Room,
    O&M, Finance, Tasks, Reports, Portfolio Admin), plus `Breadcrumbs` + navigation utils.
- **Retrieval**: index this curated corpus (server-side) and answer with **citations** to
  specific articles; reuse the `LearnMoreLink` component to deep-link the user to the
  source. If the answer isn't in the corpus, say so and offer to navigate — **do not
  invent**.
- **Navigation assistant**: `navigate_to` resolves a natural-language destination to a real
  route from the route table (scoped to what the user can access) and offers a one-click
  deep link; it never fabricates routes.
- **Single source of truth**: the assistant consumes the same help content users see, so
  docs and assistant answers can't drift.

---

## 9. Audit logging model `[PROPOSED]`

Reuse the existing best-effort, non-blocking audit system (`AuditLog` / `audit_logs`,
`_create_audit_log` / `create_audit_log`).

- **New `source` value**: `ai_assistant` (and `ai_assistant_governed` for the hard-gated
  list, for easy filtering), alongside existing sources like `telemetry_baseline`.
- **What is logged**:
  - **Proposal** (a WRITE was suggested) — optional/info level.
  - **Confirmation + execution** — `is_success`, `action` (the tool's `audit_action`),
    `user_id` (who confirmed), `details` (entity ids, summarized before/after, the
    conversation/turn id), and the backing endpoint.
  - **Refusals** — permission-denied / governed-block, for security review.
- **Linkage**: every audit row references the conversation + turn so an action is traceable
  to the exact dialog that produced it.
- **Non-blocking**: audit failures never block the user action (existing helper behavior),
  but a write tool that *cannot even attempt* an audit is flagged.
- The **underlying endpoints keep their own audit** (e.g. baseline lifecycle via
  `create_baseline_audit_log`); the assistant audit is **additive**, not a replacement.

---

## 10. Mutation boundaries `[PROPOSED]`

**The assistant may guide, draft, prefill, validate, explain, and summarize. It must never
silently mutate operational truth.**

- **Allowlist only**: the only writes possible are the registered WRITE tools, each behind
  the confirmation flow. No raw DB access, no arbitrary endpoint calls, no SQL.
- **Hard-governance list — NEVER silent, ALWAYS explicit confirm + normal authorization +
  audit:**
  - promote facts (`promote_facts`)
  - approve / activate / supersede baselines (`activate_baseline`, `supersede_baseline`)
  - map devices (`map_device`)
  - create weather declarations (`declare_weather_semantics`)
  - alter expected output / any operational-truth change
- **Read/write firewall**: READ tools physically cannot write; WRITE tools physically
  cannot execute without a confirmation token tied to a specific proposal.
- **Respect existing fail-closed guards**: the assistant cannot pre-satisfy or skip
  server-side governance (e.g. baseline activation validation `409`, promotion freshness
  `409`, baseline-driving override rationale). If a guard blocks, the assistant relays the
  reason; it does not retry around it.
- **No elevation**: the assistant cannot perform anything the logged-in user could not
  perform manually in the UI.

---

## 11. Frontend UX plan `[PROPOSED]`

- **Global surface** (replaces the Data-Room-only widget): an app-level Assistant panel
  available across modules, plus an optional command-palette entry point. Lives in the
  shared layout, not inside `due-diligence`.
- **Transport**: HTTP request + **SSE** streaming for tokens (drop the WebSocket-to-GCP
  transport).
- **Confirmation cards**: a first-class `ConfirmationCard` rendering the
  `preview_builder` summary/diff with explicit **Confirm / Cancel**; governed actions get a
  distinct, heavier treatment (impact banner, required rationale field). Rebuild
  `AIAssistantActionConfirmationDialog.tsx`'s intent on this component.
- **Wizard UI**: a stepper that renders each step's inputs (prefilled), inline validation,
  and a per-step or final confirm; resumable from a saved token.
- **Permission-aware affordances**: the assistant only *offers* actions the resolver says
  the user can take; disabled/denied actions explain why (and the server still re-checks).
- **Citations & deep links**: help answers cite Help Center articles (`LearnMoreLink`);
  navigation answers render a one-click route link.
- **Honest empty/again states**: "I can't do X with your current permissions",
  "Not found in Help", "This needs your explicit confirmation" — never silent success.

---

## 12. Backend / API plan `[PROPOSED]`

New router `app/routers/assistant/` under standard auth; new `app/services/assistant/`.

| Endpoint | Purpose |
|---|---|
| `POST /api/assistant/conversations` | Start a conversation (scoped to user; optional entity context). |
| `POST /api/assistant/conversations/{id}/turns` | Send a user message; returns assistant turn (SSE stream) incl. any proposed tool calls. |
| `GET /api/assistant/conversations/{id}` | Conversation history (user-scoped). |
| `POST /api/assistant/tools/{tool}/preview` | Build the confirmation preview for a proposed WRITE (no side effects). |
| `POST /api/assistant/tools/{tool}/execute` | Execute a confirmed WRITE: re-check permission, call backing API, audit. |
| `GET /api/assistant/tools` | Registry introspection (what the user can do here). |
| `POST /api/assistant/wizards/{id}/…` | Wizard start / advance / resume. |

- **LLM access** via the existing Replit AI gateway (OpenAI, `gpt-5.2`); reuse the
  `InAppParsingService` patterns: tenacity retries on `429`, structured/tool-call output,
  correlation IDs, idempotency keys for WRITE execution.
- **No new external service, no GCP Cloud Function, no new secret** beyond the AI gateway.
- The legacy `chatbot_router` is **flag-gated off** during transition, then removed.

---

## 13. Data model impact `[PROPOSED]`

**Additive only. No change to any operational-truth table** (facts, baselines, devices,
weather declarations, sites, etc.).

| Table | Purpose |
|---|---|
| `assistant_conversations` | One row per conversation (user_id, optional company/site context, timestamps). |
| `assistant_messages` | Per-turn messages (role, content, token usage, correlation id). |
| `assistant_tool_invocations` | Each proposed/confirmed/executed tool call: tool name, args, class, status (proposed/confirmed/executed/refused), result ref, **link to the `audit_logs` row**. |
| `assistant_workflow_runs` *(if wizards persisted server-side)* | Wizard id, current step, prefilled state, resume token, status. |

- **Legacy `chatbot_conversations`**: retain read-only during transition; decide migrate
  vs archive vs drop at retirement (separate, reviewed migration).
- All new tables are **append/operational metadata** — they record what the assistant did,
  never the source of truth for business data.

---

## 14. Implementation phases `[PROPOSED]`

Each phase is independently shippable and gated; governed writes come **last** and only on
top of a proven confirmation framework.

- **P0 — Foundations (read-only).** Assistant module skeleton, AI-gateway client, auth
  wiring, conversation/message tables, global UI panel with SSE. Tools: `navigate_to`,
  `search_help`, `explain_concept`. No writes.
- **P1 — Read tools.** `list_my_projects`, `get_project_overview`, `get_reconciliation`;
  permission-scoped retrieval; citations. Still no writes.
- **P2 — Confirmation framework + first low-risk write.** Build the two-phase engine,
  `ConfirmationCard`, audit bridge; ship **`create_task`** as the reference WRITE.
- **P3 — Standard wizards.** Add company, add site, upload documents, review/accept facts,
  create draft baseline (no activation), onboard telemetry (account + site map), export
  report — all standard-confirm.
- **P4 — Governed actions.** `promote_facts`, `activate/supersede_baseline`, `map_device`,
  `declare_weather_semantics` — each governed-confirm, honoring existing server guards.
- **P5 — Legacy retirement.** Flag-off and remove `chatbot.py`/`helpers/chatbot/*`/DocAI
  chat service/GCP function URL; optional native `search_documents` to recover RAG Q&A;
  resolve `chatbot_conversations` disposition.

---

## 15. Risks `[PROPOSED]`

| Risk | Mitigation |
|---|---|
| **Silent mutation of operational truth** | Read/write firewall + two-phase confirm + governed list can never auto-execute (§6/§10). |
| **Prompt injection** (malicious doc/help text drives a tool call) | LLM can only *propose* registry tools; backend re-checks permission and requires human confirm for writes; governed actions never batch. Treat retrieved content as data, not instructions. |
| **Permission escalation / cross-tenant leak** | No assistant service account; same guards + `_enforce_company_visibility`; retrieval filtered to visible scope; fail-closed. |
| **Hallucinated navigation/answers** | Grounded retrieval over real route table + curated Help Center, with citations; "not found" is honest. |
| **Bypassing server governance** (e.g. force baseline activate) | Assistant surfaces, never pre-satisfies, the `409`/rationale/freshness guards; relays the block. |
| **Cost / latency** | Reuse gateway + tenacity; cache help retrieval; stream via SSE; cap context. |
| **Legacy entanglement during cutover** | Flag-gate legacy off before removal; keep DocAI copies identified (`docai/` vs `backend/`) so retirement is unambiguous. |
| **Vector/RAG staleness** (if salvaged) | Defer to P5; native indexing tied to Data Room events; honest "may be incomplete" states. |
| **Audit gaps** | Every execute writes `source="ai_assistant"` linked to the turn; refusals logged. |

---

## 16. Test plan `[PROPOSED]`

- **Unit**: tool descriptors validate args (schema), enforce `required_permission`
  (fail-closed), and respect class (READ cannot write). Confirmation engine: a WRITE has no
  effect without a valid confirmation token; a governed tool rejects `auto_execute`.
- **Permission/governance**: for each WRITE, a user lacking the permission is refused
  (and the refusal is audited); governed actions cannot execute without explicit confirm;
  existing server guards (baseline activation `409`, promotion freshness `409`, override
  rationale) still block when the call comes via the assistant.
- **Integration**: each tool actually calls the **same** endpoint the UI uses and produces
  the **same** result + an `ai_assistant` audit row; idempotency key prevents
  double-execution on double-confirm.
- **Multi-tenant isolation**: retrieval/tool results never include other companies' data;
  `_enforce_company_visibility` returns 404 on mismatch.
- **Prompt-injection red-team**: documents/help text attempting to trigger
  promote/activate/map/declare must not produce an executed action without human confirm.
- **Knowledge grounding**: help answers cite real articles; out-of-corpus questions return
  an honest "not found", not a fabrication.
- **Backend harness note**: follow the existing `ilios-server` pytest harness conventions
  (dedicated test DB env, coverage-addopts override, `monkeypatch` not pytest-mock).

## 17. Browser-validation plan `[PROPOSED]`

Manual checks in the Replit preview (`Frontend` :5000 / `Backend` :8000), with screenshots
at each checkpoint:

1. **Navigation**: ask "take me to O&M for <project>" → assistant returns a working deep
   link; clicking lands on the right route (and is blocked if the user lacks access).
2. **Education**: ask a FAQ/glossary question → grounded answer **with a citation** that
   opens the right Help article via `LearnMoreLink`.
3. **Low-risk wizard (Add Task)**: run the create-task wizard → confirmation card shows the
   draft → Confirm → task appears in the Task board → an `ai_assistant` audit row exists.
4. **Permission-denied path**: as a `read_only` user, attempt a write → assistant refuses
   with an explanation; no mutation; refusal audited.
5. **Governed action gate**: attempt "promote these facts" / "activate this baseline" →
   governed confirmation with impact banner + required rationale; verify it **cannot**
   proceed without explicit confirm and that server guards still apply.
6. **Honest unavailable**: ask something out-of-scope → "I can't do that / not found",
   never a fabricated success.

(These run once the corresponding phase is built; this sprint changed no code, so there is
nothing to browser-validate yet.)

---

## 18. Confirmation: no production code changed

This sprint authored **only this document** (`docs/ai_agent_reintegration_audit_design.md`).
The only other working-tree entry is the user-provided sprint brief under `attached_assets/`
(task input, not an authored or production change).

- **No** application source files were modified (no `backend/ilios-server/**`,
  `frontend/rea-investment-fe/**`, `docai/**`, or `backend/ilios-DocAI/**` changes).
- **No** new endpoints, routers, services, tools, or UI components were created.
- **No** database schema, migration, model, table, enum, or seed change.
- **No** package, dependency, workflow, environment-variable, or secret change.
- **No** change to `InAppParsingService`, the permission resolver, audit system,
  telemetry/weather/baseline stacks, or the legacy chatbot.
- The legacy AI agent remains exactly as audited; nothing was enabled, disabled, or wired.

All items labeled `[PROPOSED]` are designs awaiting a separate, reviewed build sprint.
