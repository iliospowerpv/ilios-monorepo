# Native Workflow Engine & Wizard Framework — Audit & Design

> **Sprint type: AUDIT / DESIGN ONLY. No production code was changed.** This document is
> the sole deliverable. It traces the existing multi-step flows, then designs a single
> native, declarative workflow/wizard framework that can power **both** guided UI
> walkthroughs **and** future AI-agent actions — under strict governance.

## Build-status legend

| Tag | Meaning |
|---|---|
| `[EXISTS]` | Already built (audited reference). |
| `[GAP]` | Missing today; the design fills it. |
| `[PROPOSED]` | Designed here; not built. |
| `[BUILT]` | Designed here **and** since implemented in a later sprint (see §15 build log). |

> **Update (build log).** Sections 1–14 are the original AUDIT/DESIGN sprint record and remain
> accurate for that sprint. The framework has since been built **incrementally via small
> pilots**; each pilot is documented in **§15**. Pilot 1 (Add Company) and Pilot 2
> (Add Site / Project) are now `[BUILT]`. The §14 "no production code changed" statement
> applies to the original design sprint only — not to the pilots in §15.

## Relationship to the prior sprint

This extends `docs/ai_agent_reintegration_audit_design.md` (the AI-agent reintegration
audit). That doc defined the assistant's tool/confirmation model at a high level; **this
doc designs the underlying workflow engine** those wizards run on. The two are consistent:
the engine is the single execution substrate; the UI wizard shell and the AI assistant are
two **clients** of it.

## Governance contract (binding on every design decision)

- AI (and any automation) may **guide, prefill, validate, and propose** — never silently
  mutate operational truth.
- **Every** mutation goes through an **existing API**, the **existing permission** guard,
  an **explicit human confirmation**, and an **audit log**.
- **Hard-prohibited as autonomous/auto-executed steps** (always require explicit human
  confirmation; never engine-automated): fact promotion, baseline approval/activation,
  device mapping, weather-declaration creation, and any change to operational truth.
- No legacy chatbot reuse. No bypass of backend authorization. No new operational-truth
  tables or state.

---

## 1. Current workflow inventory `[EXISTS]`

### 1.1 The four existing multi-step UIs (all ad-hoc, no shared engine)

| Wizard | File(s) | Step model | Draft / resume | Per-step validation | Persistence of results |
|---|---|---|---|---|---|
| **Onboarding** | `src/modules/onboarding/` (`hooks/useOnboardingState.ts`, `components/{CompanyStep,ProjectStep,InviteStep,CompletionScreen}`, `OnboardingProgress`) | string `currentStep` (`company→project→invite→complete`); MUI Stepper is **display-only** | **`localStorage`** keyed `ilios_onboarding_draft_{userId}`; **no backend draft** | local `isCreateFormValid()` + `useState` errors | each step calls real create APIs (`companies.create`, `assetManagement.createSite`, …) |
| **Project Import** | `src/components/common/ProjectImport/ProjectImportWizard.tsx` | numeric `activeStep` (`Upload→Map→Validate→Import`) | **memory-only**; resets on close | client `canValidate` + **server** `validateImport` returns row-level errors | parse → validate → execute (bulk) |
| **Telemetry onboarding** | `.../AssetManagementSiteDetails/tabs/Telemetry/TelemetryWizard.tsx` | numeric `activeStep` (`Connection→Site Mapping→Device Mapping→Confirm`); MUI Stepper | **backend-driven** — each step saves via React-Query mutations | local guards (`connectionTested`, `selectedDasSite`) + mutation errors | site/device mappings persisted per step |
| **Weather declare** | `.../Telemetry/WeatherDeclareDialog.tsx` | 2-step (`Declare semantics→Review & activate`) | backend draft (`activate:false`) | local `useState` | declaration draft vs activate (**governed** — out of scope to automate) |

**Shared primitives that exist:** `SearchableSelect` / `SearchableMultiSelect`
(`src/components/common/SearchableSelect/`), `ConfirmationModal` (exit guards),
`FormattedNumericInput`. **`[GAP]` There is no unified `<Wizard>` wrapper** — every flow
re-implements `switch(activeStep)` rendering, navigation, and progress.

### 1.2 Forms & validation patterns `[EXISTS]`

- **`react-hook-form` (^7.50.0)** is the standard (Controller for selects, `register` for
  text). Field errors via MUI `helperText`/`error`.
- **Server errors**: two patterns — mapped to a `root` error key and shown at form bottom
  (`CompanyForm`, `SiteForm`, `ConnectionForm`), or surfaced via `notify` toast
  (`AddTaskForm`). `ConnectionForm` has provider-conditional validation and special
  "invalid credentials" 422 handling.
- **Document upload** (`UploadButton.tsx`) is plain MUI (no RHF): MIME/extension check +
  100 MB cap; uses `DataTransfer` to synthesize clean multipart events.
- **`PromoteVersionDialog.tsx`** — the **gold-standard confirmation pattern**: a
  "blast-radius" re-confirm that snapshots the promotion diff (`reviewedKeyRef`) and
  **re-fetches at the moment of confirm**; if the server-side diff changed, it forces
  re-review. This is the existing precedent for the framework's confirmation model (§7).

### 1.3 Backend lifecycle / draft states `[EXISTS]`

| Domain | Table(s) | Status enum | Transition service | Audit |
|---|---|---|---|---|
| Project facts | `project_facts`, `assumptions_promotions` | `FactStatus` (`candidate→active→retired`) | `PromotionService.promote_version` | `assumptions_promotions` row + `is_actual` on `File` |
| Expected baselines | `telemetry_expected_baselines`, `…_points` | `TelemetryBaselineStatus` (`draft→in_review→approved→active→superseded/rejected`) | `expected_service` (partial unique index enforces single active) | baseline lifecycle audit (`telemetry_baseline` source) |
| DD parse runs | `ai_parsing_results` | `FileParsingStatuses` (`not_started`→`queued`→`processing`→`completed`, plus failure states `processing_failed`/`processing_timeout`/`processing_start_failed`/`unprocessable_file` — no single `failed`) | `parse_state_service` | completion creates candidate facts |
| Deal pipeline | `deals`, `sales_state_transitions` | `SalesStage` (14 values, `prospect`…`dead`; conversion is tracked by the `is_converted` flag, not a stage) | `crud/sales.py: transition_deal_stage` | **`sales_state_transitions`** (`from_state`,`to_state`,`transition_type`,`notes`,`changed_by_id`) |

**The deal pipeline is the closest existing "workflow engine":** a declared stage set
(`app/static/sales.py`), guarded transitions (`transition_deal_stage`), a per-transition
audit table, **gating** (`CONVERSION_ELIGIBLE_STAGES`, required `name`/`company_id`/`state`
on `convert_to_project`), and a **readiness computation** (`HANDOFF_CHECKLIST_ITEMS` /
`get_handoff_checklist` → `DealReadinessWidget` %). The framework generalizes these proven
ideas rather than inventing new ones.

### 1.4 The nine focus workflows, mapped to today

| # | Workflow | Existing entry / form | Backing API (verified) | Permission | Draft/lifecycle state | Governed terminal? |
|---|---|---|---|---|---|---|
| 1 | Add a company | Onboarding `CompanyStep`, `CompanyForm`, AddCompany page | `POST /api/companies/` | platform admin | none (localStorage in onboarding) | no |
| 2 | Add a site | Onboarding `ProjectStep`, `SiteForm`, `CreateProjectDialog`/`AddProjectDialog` | `POST /api/sites/` | `assets_management:edit` | none | no |
| 3 | Telemetry onboarding | `TelemetryWizard`, `ConnectionForm` | connection: `POST /api/telemetry/companies/{id}/connections` (legacy, used by the wizard) **or** V2 `…/v2/companies/{id}/provider-accounts`; site map: `PUT …/v2/sites/{id}/mapping`; device map: `POST …/v2/sites/{id}/device-mappings` | `settings:edit` (legacy conn) / `telemetry_admin` (V2 provider-account); `settings:edit` + company-admin (site map & device map) | per-step backend save | **device mapping = governed** |
| 4 | Document upload/review | `UploadButton`/`DocumentModal`, Data Room verify | `POST …/documents/{id}/upload`; `POST …/files/{id}/bulk-accept/` | `diligence:edit` | parse-run states; doc versions | no (accept ≠ promote) |
| 5 | Project fact creation | bulk-accept → candidate facts; `PromoteVersionDialog` | `…/files/{id}/bulk-accept/`; `POST /api/projects/{site_id}/assumptions/promote` | `diligence:edit` | `FactStatus` candidate→active→retired | **promotion = governed** |
| 6 | Draft baseline creation | Reconciliation tab | `POST …/expected-baseline/create-draft-from-facts` (draft only) | `telemetry_admin` | baseline `draft` | **approve/activate = governed (out of scope)** |
| 7 | Inventory reconciliation | Reconciliation tab (read-only) | `GET …/sites/{id}/inventory-reconciliation` | `assets:view` | none (read) | no — remediation = create task |
| 8 | Task assignment | `AddTaskForm`, TaskBoard | `POST /api/task-tracker/boards/{board_id}/tasks` | `diligence:edit` or `onm:edit` | none | no |
| 9 | Reporting | `AllReports` | `POST …/reports/{id}/export-to-file` | `reporting:view` | none | no |

**`[GAP]` summary:** no declarative workflow definitions; no shared wizard shell; no
server-side resumable draft for the *wizard itself* (only fragile per-flow localStorage or
in-memory state); confirmation + audit are bespoke per flow; nothing is reusable by the AI.

---

## 2. Reusable wizard architecture `[PROPOSED]`

A single declarative engine with one definition format consumed by two clients (UI shell +
AI assistant) and one execution path.

```
        Workflow Definition (declarative; per-workflow)
                      │
        ┌─────────────┴──────────────┐
   UI Wizard Shell            AI Assistant (proposes/prefills)
        └─────────────┬──────────────┘
                      ▼
        Workflow Engine (FE orchestration + BE run/state)
         steps · validation · progress · resume · confirm
                      ▼
        Existing APIs  (the SAME endpoints the UI uses today)
                      ▼
        Existing permission guards + audit_logs
```

**Core tenets**

1. **Declarative, not bespoke.** A workflow is data: an ordered list of steps, each with
   inputs, validators, a required permission, a confirmation policy, and the **existing**
   API it calls. No new mutation logic is created — steps *invoke existing endpoints*.
2. **One shell, many workflows.** A single reusable `<Wizard>` shell renders any
   definition (replacing the four `switch(activeStep)` re-implementations).
3. **Engine never owns truth.** It orchestrates collection/validation/confirmation; the
   *result* of a step is whatever the existing endpoint persists. Wizard "draft" state
   (collected inputs) is **separate** from domain draft state (candidate facts, draft
   baselines) and never substitutes for a real mutation.
4. **Governed steps are first-class and structurally gated** (§7/§9): a step flagged
   `governed` can never be auto-advanced or auto-executed.

### Step descriptor `[PROPOSED]`

```
id                  unique step key
title / help        UI copy (link Help Center articles, §reuse)
inputs[]            field schema (type, label, options-source, default/prefill-source)
validators[]        client rules (react-hook-form) + optional server-validate endpoint
required_permission module:action (+scope) — reused guard
gating              precondition expr over prior step outputs (e.g. CONVERSION_ELIGIBLE)
action              { kind: 'read'|'write', api: existing endpoint, idempotency_key }
confirmation        'none' | 'standard' | 'governed'  (write steps only)
preview_builder     produces human-readable summary/diff for confirmation
audit_action        audit action string written on execute
on_success          next-step routing / outputs to carry forward
```

### Workflow descriptor `[PROPOSED]`

```
id, version          (versioned so resumed drafts bind to a known shape)
entry_permission     coarse gate to even start
steps[]              ordered step descriptors
resume_policy        server-draft | client-only | none
final_confirmation   optional terminal recap
```

---

## 3. Workflow state / data model `[PROPOSED]`

**Additive metadata only. No change to any operational-truth table.** The engine persists
*the progress of the wizard*, never business truth (which keeps flowing through existing
domain tables/states from §1.3).

| Table | Purpose |
|---|---|
| `workflow_runs` | one per in-progress/completed run: `workflow_id`, `version`, `user_id`, scope (`company_id`/`site_id`), `status` (`active`/`paused`/`completed`/`abandoned`), `current_step`, timestamps, `resume_token`. |
| `workflow_step_states` | per-step record: collected inputs (JSONB), validation status, `executed` flag, link to the resulting domain entity id and to the `audit_logs` row. |

- **Resume** replaces the fragile `localStorage` onboarding draft with a **server-side,
  user-scoped** draft so a run survives device/browser changes; client-only mode remains
  available for trivial flows. A run binds to `workflow.version`; if the definition changed,
  the engine re-validates rather than blindly replaying.
- **Progress tracking**: derived from `current_step` + per-step `executed` flags; the UI
  shell renders the MUI Stepper from this (single source, vs today's display-only steppers).
- **Idempotency**: write steps carry an `idempotency_key` (mirroring `InAppParsingService`
  / `AIParsingResultCRUD.create_or_get_active`) so a resumed/double-confirmed step cannot
  double-execute.
- **Separation guarantee**: `workflow_step_states` references domain entities by id; it
  never stores or becomes the authoritative copy of a fact/baseline/mapping.

---

## 4. API impact `[PROPOSED]`

**No existing endpoint changes; no new mutation endpoints for business truth.** Steps call
the **same** create/update endpoints audited in §1.4. New endpoints only manage *runs*:

| Endpoint | Purpose |
|---|---|
| `GET /api/workflows` | list workflow definitions the user may start (entry-permission filtered). |
| `POST /api/workflows/{id}/runs` | start a run (server draft); returns `run_id` + first step. |
| `GET /api/workflows/runs/{run_id}` | fetch run + step states (resume). |
| `PATCH /api/workflows/runs/{run_id}/steps/{step_id}` | save collected inputs / mark validated (no side effect). |
| `POST /api/workflows/runs/{run_id}/steps/{step_id}/preview` | build confirmation preview for a write step (no side effect). |
| `POST /api/workflows/runs/{run_id}/steps/{step_id}/execute` | execute a **confirmed** write step → calls the existing endpoint → audits. |
| `POST /api/workflows/runs/{run_id}/abandon` | abandon/cleanup. |

- The execute handler is a thin dispatcher: re-check permission (fail-closed) → call the
  real endpoint/service → write the engine audit row → record entity id. It contains **no**
  bespoke business logic.
- Optional **server-validate** endpoints already exist for some flows (e.g.
  `validateImport`); the engine reuses them as a step's `server validator`.

---

## 5. Frontend UX plan `[PROPOSED]`

- **Reusable `<Wizard>` shell** (`src/components/common/Wizard/`): consumes a definition,
  renders the MUI Stepper, the active step's inputs (react-hook-form), inline + server
  validation, Back/Next/Confirm, progress, and a `ConfirmationModal`-based exit guard.
  Reuses `SearchableSelect`, `FormattedNumericInput`, the `root`-error and `notify`
  conventions already standardized.
- **Migration path (non-breaking):** the four existing wizards (onboarding, project import,
  telemetry, and the generic forms) can be re-expressed as definitions over the shell in
  later phases; nothing is forced to migrate at once.
- **Confirmation cards / governed treatment:** write steps show a preview; governed steps
  get a heavier treatment (impact banner, required rationale, the **blast-radius
  re-confirm** generalized from `PromoteVersionDialog`).
- **Resume UX:** "Continue where you left off" surfaced from `workflow_runs`; replaces the
  invisible localStorage draft.
- **Permission-aware affordances:** steps the user cannot perform are hidden/disabled with
  an explanation; the server still re-checks (UI is never the boundary).
- **Honest states:** "needs your confirmation", "you don't have permission", "validation
  failed on rows X/Y" — never silent success.

---

## 6. Permission model `[PROPOSED]`

Reuse the canonical stack verbatim — the engine introduces **no new privilege**.

- Each step declares the **same** guard as its backing endpoint: hierarchical project
  access (`get_authorized_site` / `resolve_effective_access`, Portfolio→Company→Project,
  restrict-only, intersection), module/action checks (`PermissionsModules` ×
  `PermissionsActions`), specialized guards (`telemetry_admin_required`,
  `get_authorized_site_with_company_admin`), and `_enforce_company_visibility`
  (404-on-mismatch).
- **Two-layer enforcement:** entry-permission to *start* a run; per-step permission at
  *execute* time (authoritative). The run executes strictly **as the logged-in user**.
- **Fail-closed:** missing/ambiguous permission, scope mismatch, or unknown step → refuse
  and explain; never best-effort.

---

## 7. Confirmation model `[PROPOSED]`

Two-phase commit for every write step; generalizes the existing `PromoteVersionDialog`
"blast-radius" precedent.

```
PLAN     save inputs → validate (client + server) → build preview (NO write)
CONFIRM  user reviews preview → explicit Confirm
EXECUTE  re-check permission + idempotency → re-fetch & diff (blast-radius):
           if the underlying data changed since preview → force re-confirm
         → call existing endpoint → write audit → record entity id
```

**Tiers:**

1. **Standard write** — one explicit confirm (create company/site, upload doc, accept
   facts, create draft baseline, create task, export report).
2. **Governed write** (the hard-prohibited-as-autonomous set) — **always** explicit, never
   engine-advanced, never batched into "accept all", and they additionally **surface (never
   pre-satisfy) existing server guards** (baseline activation `409`, promotion freshness
   `409`, baseline-driving override rationale). Covers: **fact promotion, baseline
   approve/activate/supersede, device mapping, weather-declaration creation, any
   operational-truth change.** Baseline approval/activation, device mapping, and weather
   declaration are **out of scope for any automated step in this framework** — the engine
   may, at most, navigate the user to the existing manual UI and stop.

**Absolute rule:** a governed step with `auto_execute=true` (or any "skip confirmation"
config) is a definition error the engine must reject at load time.

---

## 8. Audit model `[PROPOSED]`

Reuse the existing best-effort, non-blocking audit (`AuditLog` / `audit_logs`,
`_create_audit_log`), aligned with the prior sprint.

- **Source values:** `workflow_engine` (and `workflow_engine_governed` for the hard set)
  for easy filtering, alongside existing `telemetry_baseline` / sales transitions.
- **What is logged:** run start/abandon (info); per write step the **confirmation +
  execution** with `is_success`, `action` (`audit_action`), `user_id` (who confirmed),
  `details` (entity ids, summarized before/after, `run_id`/`step_id`), and the backing
  endpoint; **refusals** (permission/governed blocks) for security review.
- **Additive, not a replacement:** underlying endpoints keep their own audit
  (`assumptions_promotions`, `sales_state_transitions`, baseline lifecycle). The engine
  audit links the run to those domain records for end-to-end traceability.

---

## 9. AI integration boundary `[PROPOSED]`

The **same** workflow definitions power the AI assistant (from the prior sprint). The AI is
just another client of the engine — it gets **no** special path.

- **AI may:** suggest which workflow to start, **prefill** step inputs from context/facts,
  run client/server **validation**, explain steps (cite Help Center), and **propose** the
  next action.
- **AI may not:** advance a step without the user, execute any write without explicit
  human confirmation, or touch governed terminals autonomously. The engine's
  `confirmation='governed'` + "no auto_execute" rule is what makes "AI must not silently
  mutate operational truth" structurally true.
- **Mechanism:** the AI calls the *same* `…/steps/{id}/preview` (read-only) to draft a
  confirmation; only a human click hits `…/execute`. The AI cannot synthesize the
  confirmation token.
- **Boundary table:**

| Capability | Guided UI user | AI assistant |
|---|---|---|
| Start a run, fill inputs | yes | yes (prefill) |
| Validate / preview | yes | yes (read-only) |
| Confirm a standard write | yes (explicit) | **no — requires human confirm** |
| Execute governed terminal | yes (explicit, manual) | **never** |

---

## 10. Implementation phases `[PROPOSED]`

Each phase ships independently; governed terminals come last and only navigate to manual UI.

- **P0 — Engine + read-only shell.** `workflow_runs`/`workflow_step_states`, run endpoints,
  `<Wizard>` shell rendering definitions with read/validate steps only. No writes.
- **P1 — Standard writes + confirmation framework.** Two-phase preview/execute + audit
  bridge; ship the lowest-risk write workflow end-to-end (**task assignment**) as the
  reference.
- **P2 — Re-express existing wizards as definitions.** Add company, add site, document
  upload/accept, draft-baseline *creation* (draft only), reporting — migrate the onboarding
  and project-import flows onto the shell (replace localStorage/in-memory drafts with
  server resume). Telemetry onboarding's account+site-mapping steps; device-mapping step
  navigates to existing manual UI (governed).
- **P3 — Governed surfacing (no automation).** Fact promotion and inventory-reconciliation
  remediation: the engine builds previews and routes to the existing manual confirm dialogs
  (`PromoteVersionDialog`, baseline UI); it never executes promotion/approval/activation/
  device-mapping/weather-declaration itself.
- **P4 — AI client.** Wire the assistant to the same definitions (prefill/validate/propose
  only), reusing P1's confirmation gate.

---

## 11. Risks `[PROPOSED]`

| Risk | Mitigation |
|---|---|
| **Silent mutation of operational truth** | Engine never owns truth; write = existing endpoint behind two-phase confirm; governed terminals can't auto-execute (§7/§9). |
| **Stale draft replays a changed action** | Blast-radius re-confirm (re-fetch + diff at execute) generalized from `PromoteVersionDialog`; runs bind to `workflow.version`. |
| **Permission drift between step and endpoint** | Steps declare the *same* guard; execute re-checks server-side; fail-closed. |
| **Double execution on resume/retry** | Per-step `idempotency_key` + `executed` flag. |
| **Scope creep into a parallel mutation layer** | Hard rule: execute handlers are thin dispatchers to existing endpoints; no bespoke business logic, no new operational-truth tables. |
| **Cross-tenant leakage in saved drafts** | `workflow_runs` user/company-scoped; `_enforce_company_visibility`. |
| **Migration regressions** | Existing wizards keep working; re-expression is phased and optional, not a big-bang rewrite. |
| **AI over-reach** | AI limited to read/preview/prefill; cannot mint confirmation tokens; governed terminals never reachable by AI. |

---

## 12. Test plan `[PROPOSED]`

- **Engine unit:** definition loader rejects `governed`+`auto_execute`; step gating/validation
  evaluated correctly; resume binds to version and re-validates on mismatch; idempotency
  prevents double execute.
- **Permission/governance:** each write step refuses a user lacking the permission (and the
  refusal is audited); governed steps cannot execute without explicit confirm; existing
  server guards (promotion freshness `409`, baseline activation `409`, override rationale)
  still block when invoked via the engine.
- **Integration:** each step calls the **same** endpoint the UI uses and yields the **same**
  result + a `workflow_engine` audit row linked to the domain audit record.
- **Confirmation:** no write occurs without a valid confirm token; blast-radius re-confirm
  fires when underlying data changed between preview and execute.
- **Multi-tenant isolation:** runs/drafts never expose another company's data.
- **AI boundary:** AI preview path is read-only; AI cannot execute a write or reach a
  governed terminal.
- **Backend harness:** follow the existing `ilios-server` pytest conventions (dedicated
  test DB env, coverage-addopts override, `monkeypatch`, `PermissionType` as plain str).

## 13. Browser-validation plan `[PROPOSED]`

Manual checks in the Replit preview (`Frontend` :5000 / `Backend` :8000), with screenshots:

1. **Standard wizard (Add Task):** run end-to-end on the shell → preview → confirm → task
   appears on the board → `workflow_engine` audit row exists.
2. **Resume:** start "Add site", close mid-way, reopen → run resumes from the saved step
   (server draft, not localStorage).
3. **Validation:** project-import-style step shows server row-level errors and blocks Next.
4. **Permission-denied:** as `read_only`, attempt a write step → refused with explanation;
   no mutation; refusal audited.
5. **Governed surfacing:** start a fact-promotion flow → engine builds the preview and
   routes to the existing `PromoteVersionDialog`; verify it **cannot** auto-execute and that
   the blast-radius re-confirm + server guards still apply.
6. **Honest unavailable:** governed terminals (baseline activate / device map / weather
   declare) only navigate to manual UI; the engine never executes them.

(These run once the corresponding phase is built; this sprint changed no code, so there is
nothing to browser-validate yet.)

---

## 14. Confirmation: no production code changed

This sprint authored **only this document**
(`docs/native_workflow_engine_wizard_framework_audit.md`). The only other working-tree
entries are user-provided sprint briefs under `attached_assets/` (task input, not authored
or production changes).

- **No** application source files were modified (no `backend/ilios-server/**`,
  `frontend/rea-investment-fe/**`, `docai/**`, or `backend/ilios-DocAI/**` changes).
- **No** new endpoints, routers, services, engine, tables, enums, migrations, or UI
  components were created.
- **No** package, dependency, workflow, environment-variable, or secret change.
- **No** change to existing wizards, forms, the permission resolver, audit system, or any
  domain lifecycle (facts, baselines, deals, telemetry, weather).
- **No** operational-truth change and **no** governed action (fact promotion, baseline
  approval/activation, device mapping, weather declaration) was performed or automated.

All items labeled `[PROPOSED]` are designs awaiting a separate, reviewed build sprint.

---

## 15. Build log — pilots `[BUILT]`

The engine is being built **incrementally**, one real flow at a time, so each pilot proves a
specific framework capability against a live endpoint before the next is attempted.

- **Pilot 1 — Add Company** (`add_company`): first vertical slice; entry permission
  `platform_admin`; static selects (`company_types`, `us_states`); reuses the existing
  company-create endpoint + `CreateCompanySchema`; companies have DB uniqueness, so its
  preview warning is a hard "creation will fail" and a unique-violation at execute is mapped
  to a `409 conflict` with a `conflict_unique` audit outcome.
- **Pilot 2 — Add Site / Project** (`add_site`): documented in full below.

### 15.1 Pilot 2 goal & what it proves

Pilot 2 proves the same engine generalizes to a **second** flow with two capabilities Pilot 1
did not exercise:

1. a **company-scoped** permission model (not the platform-wide `platform_admin`), and
2. a **dynamic** select whose options are resolved per-user at serialize time (the company
   picker), alongside a curated timezone picker and a new `number` field type.

Per `replit.md`, the backend entity remains **Site**; the UI label is **Project**. The engine
**never owns truth** — it wraps the existing site-create endpoint behind
preview → confirm → execute and adds nothing to site-creation behavior.

### 15.2 Files changed

**Backend** (`backend/ilios-server`):

- `app/services/workflows/engine.py` — added the `assets_management:create_site` permission
  token (`PERMISSION_ASSETS_CREATE_SITE`) and `_has_company_scoped_edit`; threaded
  `db_session` (+ `current_user`) through `list_workflow_definitions`, `serialize_definition`,
  `_can_start`, and `_ensure_permission` so per-user dynamic options and company-scoped checks
  can resolve; extended `_build_warnings` with the read-only `add_site` duplicate-name advisory.
- `app/services/workflows/definitions.py` — the `ADD_SITE` `WorkflowDef` (collect step
  `project_details`, execute step `review_and_create`); `_editable_company_options` +
  `resolve_options` cases for `companies` and `us_timezones`; the `number` field type; and the
  `add_site → CreateSiteSchema` entries in `STEP_INPUT_SCHEMAS` and `WORKFLOW_PAYLOAD_SCHEMAS`
  (validated at import).
- `app/services/workflows/executors.py` — `_execute_add_site` (lazy-imports the existing
  site-create endpoint + `CreateSiteSchema`, returns `("site", id)`) and its `EXECUTORS` entry.
- `tests/test_workflow_engine.py` — extended with the Pilot-2 suites (see §15.7).

**Frontend** (`frontend/rea-investment-fe`):

- `src/modules/workflows/AddSiteWorkflowPage.tsx` (new) + `src/modules/workflows/index.ts`
  export — mirrors the merged Add Company page on the shared `Wizard` shell.
- `src/App.tsx` — route `/workflows/add-site`.
- Shared `Wizard` field renderer — `number` field type.
- Navigation entry for "Add Project", permission-gated.

The existing manual Site/Project creation form was **not** touched.

### 15.3 Routes used

All engine routes already existed (Pilot 1); Pilot 2 added **no** new routes. Mounted at
`/api/workflows`:

| Method & path | Purpose |
|---|---|
| `GET /api/workflows` | List startable workflows for the user. |
| `POST /api/workflows/{workflow_id}/runs` | Start a run (`201`; entry permission enforced). |
| `GET /api/workflows/runs/{run_id}` | Fetch a run + serialized definition (save/resume). |
| `PATCH /api/workflows/runs/{run_id}/steps/{step_id}` | Persist + server-validate a step (no write). |
| `POST /api/workflows/runs/{run_id}/steps/{step_id}/preview` | Read-only preview + confirm token. |
| `POST /api/workflows/runs/{run_id}/steps/{step_id}/execute` | Execute the confirmed write. |
| `POST /api/workflows/runs/{run_id}/abandon` | Cancel a run. |

At execute, `_execute_add_site` invokes the **existing** domain endpoint **verbatim**:
`POST /api/sites/` (`create` in `app/routers/assets_management/sites.py`, `CreateSiteSchema`) —
the same call, guard, scaffolding (default sections/boards/documents), and commit as the manual
"Add Project" path. No parallel mutation logic.

### 15.4 Permission model

- **Entry token:** `assets_management:create_site`. Resolved fail-closed as
  **platform-bypass OR `_has_company_scoped_edit`**, where the latter calls
  `require_module_permission_any_company(module=assets_management, action="edit")` over the
  user's accessible company ids. It is deliberately **company-scope only**: a project/site-only
  grant must not let a user start the wizard or enumerate companies.
- **Coarse vs authoritative:** the engine gate is an **any-company** coarse check. The
  **authoritative per-company** guard remains the existing site-create endpoint at execute time.
  If the coarse gate passes but the user lacks edit on the *selected* company, the endpoint
  raises `403`; the engine rolls back and records a distinct `endpoint_refused_permission`
  audit outcome before re-raising.
- **Fail-closed:** an unknown/mis-typed permission token is always refused (`403`), so a bad
  definition can never silently grant access.
- **Drift from the session plan:** the plan named the token `assets_management:edit`. The
  implementation uses a dedicated, self-describing token `assets_management:create_site` whose
  underlying *check* is exactly the company-scoped `assets_management` **edit** permission —
  same semantics, clearer intent, and it leaves room for a future finer-grained create grant.
  Pilot 1's `platform_admin` path is unchanged.

### 15.5 Dynamic options

`serialize_definition` resolves each select's `options_source` per request via `resolve_options`:

- `companies` → `_editable_company_options`: active companies where the user holds
  `assets_management` edit (resolved through `resolve_effective_access`); platform-bypass users
  see all active companies. Best-effort and read-only; the endpoint stays authoritative.
- `us_timezones` → curated IANA list **plus `UTC`** (feeds the per-site timezone column).
- `company_types`, `us_states` → unchanged static enum sources.
- New `number` field type for `system_size_ac` / `system_size_dc`.

### 15.6 Audit, idempotency & uniqueness

- **Audit:** every execute writes a `create_workflow_audit_log` row with action
  `workflow.add_site.execute`. Outcomes: `executed` (success — records `entity_type=site`,
  `entity_id`, and an input `summary`), `endpoint_refused_permission` (`403` from the endpoint),
  and `endpoint_error` (other `HTTPException`). The success row's id is stored on the step state
  (`audit_log_id`) alongside `result_entity_type`/`result_entity_id` for end-to-end traceability.
- **Idempotency:** `execute_step` short-circuits when the step state is already `executed`
  (returns the prior result — no second write), and also on a matching `idempotency_key`. After
  a successful execute the run transitions to `completed`, so a **live replay** is additionally
  caught by the non-active-run guard and returns `409` (defense-in-depth, still no double write).
  The executed-flag / idempotency-key short-circuit itself is covered by unit tests.
- **Uniqueness:** sites have **no** DB uniqueness constraint, so the duplicate check is a
  read-only, **non-blocking preview advisory** only — *"A project named 'X' already exists in
  this company."* — and creation still proceeds. (Contrast Pilot 1: companies are unique, so its
  warning is hard and a collision becomes a `409 conflict_unique`.)

### 15.7 Tests

`tests/test_workflow_engine.py` was extended with `TestAddSiteDefinition`,
`TestAddSitePermission`, `TestAddSiteExecutor`, `TestAddSiteOptionResolution`, and
`TestAddSitePreviewWarning`, covering: definition loads/validates; `assets_management:create_site`
fail-closed (no company context → `403`, edit-context → pass, platform-bypass → pass) and unknown
token → `403`; executor calls the real `sites.create` and writes the success audit; idempotency
(executed flag + idempotency key); confirm-token blast-radius; and dynamic company-option
resolution. Full file: **43 passed** via
`test_db_name=test_heliumdb python -m pytest tests/test_workflow_engine.py -o addopts="" -p no:cacheprovider -q`.

### 15.8 Browser / API validation

A throwaway live E2E (against the running `Backend` on :8000, then deleted) drove the real HTTP
API end to end and asserted **21/21** checks:

- list shows `add_site` and `can_start` is true for an authorized user;
- start → `201`; the serialized definition resolves the **company picker** options, the
  **timezone** options (UTC + IANA), and the **number** field type;
- preview fires the **duplicate-name warning** and performs **no write** (row count unchanged),
  and issues a **confirm token**; a unique name yields no warning;
- execute → `200`, creating a **real site via the existing endpoint** with the chosen IANA
  **timezone persisted**, and writing the **success audit** row;
- **idempotency** replay creates no duplicate (`409`, count unchanged);
- **blast-radius**: a tampered confirm token is rejected `409 reconfirm_required` and **no site
  is created**;
- teardown leaves **zero residue** (test sites, boards, runs, and audit rows all removed —
  including an orphan from an earlier aborted run; the protected site 4 / 110 Shawmut was never
  touched, and the warning probe used a non-protected company).

The FE compiles clean (`No issues found.`) and the `/workflows/add-site` route is auth-gated.

### 15.9 Remaining gaps & next pilot

- **Live permission-denied not exercised:** the dev DB has no zero-access user, so the live
  `403` path was skipped; it is covered by unit tests and by the endpoint's authoritative guard.
- **Authenticated FE render not screenshot-verified:** the preview requires login; the page
  mirrors the merged Add Company wizard and the backend serialization it consumes is proven live.
- **Idempotent replay returns `409`, not a cached `200` echo:** on a completed run the
  non-active-run guard fires first; the cached-result short-circuit is unit-tested rather than
  observed live.
- **Coarse gate is any-company by design:** per-company authority intentionally stays with the
  existing endpoint.
- **Next pilots:** a flow with **server row-level validation** (project-import-style errors that
  block Next), then a **governed-surface** flow that builds a preview and routes to the existing
  manual confirmation UI — proving the engine **never auto-executes** a governed terminal (fact
  promotion, baseline activation, device mapping, weather declaration).

## 16. Build log — Native Onboarding Experience, Phase 1 `[BUILT]`

Pilots 1–2 proved the engine on **single** flows. Phase 1 of the Native Onboarding Experience
adds a **discovery + orchestration** layer **on top of** the same engine without touching its
write semantics: richer registry metadata, a **Workflow Dashboard**, and an **Onboarding
Orchestrator** that chains Add Company → Add Project (= Site). The workflows stay **independent
but chainable** — each still runs the unchanged preview → confirm → execute handshake, each is
individually permission-gated, and the orchestrator itself **writes nothing** (it only starts
runs and reads their results).

### 16.1 Goal & what it proves

1. **Registry as a catalog, not just a launcher:** definitions carry presentational discovery
   metadata (`category`, `icon`, `suggested_next`, `landing_route_template`, `sequence_eligible`)
   so a dashboard can group/route them without hard-coding workflow knowledge in the FE.
2. **Owner-scoped run history:** a user can see their own in-progress and completed runs and
   **resume** or **cancel** them — proving the engine's persisted run state is a first-class,
   listable resource, not just a per-page ephemeral handle.
3. **Declarative sequences:** a `SequenceDef` describes an ordered chain of existing workflows
   with **no executor of its own**; chaining is expressed as additive, nullable **lineage** on
   `workflow_runs` (`parent_run_id`, `sequence_id`, `sequence_step_index`) so the chain is
   auditable while each step remains a standalone, independently-runnable workflow.

### 16.2 Files changed

**Backend** (`backend/ilios-server`):

- `app/models/...workflow run model` — additive nullable lineage columns `parent_run_id`
  (self-FK, `ON DELETE SET NULL`), `sequence_id` (VARCHAR), `sequence_step_index` (Integer);
  indexes on `parent_run_id` and `(user_id, sequence_id, status)`.
- `alembic` migration `ff40` — additive, nullable; verified `upgrade`+`downgrade` clean on the
  dev DB (dev DB left at head).
- `app/services/workflows/definitions.py` — extended `WorkflowDef` with the discovery metadata;
  added `SequenceDef` + the `SEQUENCES` registry (`onboarding = (add_company, add_site)`),
  validated at import (every referenced workflow id must exist; no sequence executor).
- `app/services/workflows/engine.py` — `list_user_runs` (owner-scoped summaries),
  `list_sequences` (per-step `can_start` resolved for the user), `start_run` now accepts +
  **validates** lineage (rejects a `parent_run_id` the caller does not own) and persists it; and
  orchestrator audit helpers emitting `workflow.sequence.{id}.started` / `.advanced` on start and
  `.completed` / `.step_completed` on execute.
- `app/schemas/...workflow schemas` — `WorkflowDefinitionSchema` gained the metadata fields;
  added `WorkflowRunSummary` + `WorkflowRunListResponse`, `SequenceStep`/`SequenceSchema` +
  `SequenceListResponse`; `StartRunRequest` gained optional `parent_run_id` / `sequence_id` /
  `sequence_step_index`.
- `app/crud/...workflow run CRUD` — `list_for_user(user_id, statuses?, workflow_id?,
  sequence_id?, limit?)`.
- `app/routers/...workflows router` — `GET /api/workflows/runs` (owner-scoped, capped pagination)
  registered **before** `GET /api/workflows/runs/{run_id}`; `GET /api/workflows/sequences`;
  `start_run` threads the new optional lineage fields.
- `tests/test_workflow_engine.py` — +~21 tests (see §16.7).

**Frontend** (`frontend/rea-investment-fe`):

- `src/api/workflows.ts` + `src/api/index.ts` — new types (`WorkflowRunSummarySchema`,
  `WorkflowRunListResponse`, `SequenceStepSchema`, `SequenceSchema`, `SequenceListResponse`,
  `ListRunsParams`); `WorkflowDefinitionSchema`/`StartRunRequest` extended; `listRuns`
  (repeated `?status=` via `URLSearchParams`) + `listSequences` methods.
- `src/modules/workflows/WorkflowDashboardPage.tsx` (new) — the dashboard.
- `src/modules/workflows/OnboardingOrchestratorPage.tsx` (new) — the orchestrator.
- `src/modules/workflows/WorkflowRunPage.tsx` (new) — generic resume page (`/workflows/run/:runId`).
- `src/modules/workflows/landing.ts` (new) — landing-route resolution + naive-UTC timestamp
  formatting + the FE-owned start-route maps.
- `src/modules/workflows/index.ts`, `src/App.tsx` — exports + routes `/workflows`,
  `/workflows/onboarding`, `/workflows/run/:runId`.
- `src/components/layout/NavMenu/NavMenu.tsx` — a permission-gated **Workflows** nav entry.

No existing manual form, executor, or write path was modified.

### 16.3 Routes

| Method & path | Purpose | Added? |
|---|---|---|
| `GET /api/workflows/runs` | Owner-scoped run summaries (`?status=` repeatable, capped `limit`). | **new** |
| `GET /api/workflows/sequences` | Declarative sequence catalog with per-step `can_start`. | **new** |
| `POST /api/workflows/{workflow_id}/runs` | Start a run; now also accepts optional lineage. | extended |
| `GET /api/workflows` · `GET /runs/{run_id}` · `PATCH …/steps/{id}` · `POST …/preview` · `…/execute` · `…/abandon` | Unchanged engine handshake. | — |

FE routes: `/workflows` (dashboard), `/workflows/onboarding` (orchestrator),
`/workflows/run/:runId` (generic resume), plus the existing `/workflows/add-company` and
`/workflows/add-site`.

### 16.4 Permission model

- **No new permission tokens.** Discovery endpoints are owner-scoped; every *start* still
  resolves the underlying workflow's existing entry permission (`add_company` → `platform_admin`;
  `add_site` → `assets_management:create_site`), and every *execute* is still authorized by the
  underlying domain endpoint. The dashboard/orchestrator add **zero** authority.
- `GET /runs` returns **only the caller's** runs; `start_run` **rejects a `parent_run_id` the
  caller does not own** (fail-closed) so lineage can never be forged to read or chain another
  user's run.
- `list_sequences` reports per-step `can_start` for the user but never bypasses the start gate;
  the FE merely disables Start when `can_start` is false (server stays authoritative).
- **Nav gating is convenience only:** the Workflows entry shows for platform-bypass **or**
  any-company `Asset Management:edit`; the server gates each action regardless.

### 16.5 Dashboard UX

`/workflows` reads three sources (`list`, `listRuns`, `listSequences`) and groups them:

- **Suggested** — declarative sequences (Onboarding) as cards with per-step chips; Start is
  disabled when the first step is not startable.
- **In Progress** — `active`/`paused` owner runs with **Resume** (→ `/workflows/run/:runId`,
  which loads the run and resumes the shared `Wizard` from its saved `current_step` + inputs) and
  **Cancel** (the existing `abandon` call — the *only* mutation the dashboard performs).
- **Available** — startable single definitions routed via an FE-owned id→route map.
- **Completed** — finished runs with a **View result** deep link built from
  `landing_route_template` + `result_entity_id` (hidden when either is absent — no dead links).

Honest empty/loading/error states throughout; timestamps are parsed naive-UTC (append `Z`).

### 16.6 Orchestrator behavior

`/workflows/onboarding` hosts a 2-step progress (`Add Company` → `Add Project`) over the shared
`Wizard`:

1. Starts an `add_company` run tagged `sequence_id=onboarding, sequence_step_index=0`.
2. On the company execute response it captures `entity_id` (the new company id) and the
   company run id, then starts an `add_site` run tagged `…step_index=1, parent_run_id=<company
   run>` and **prefills** the company picker by seeding the collect step's inputs **client-side**
   — **no orchestrator server write**.
3. On the project execute it navigates to the project landing route.

The orchestrator never mutates operational truth; both writes happen inside the two underlying
workflows' own execute calls. Exiting abandons the active underlying run (best-effort).

### 16.7 Audit events

On top of each step's existing `workflow.<id>.execute` audit row, `start_run` and `execute_step`
emit additive **orchestrator** audit events when a run carries sequence lineage:
`workflow.sequence.{sequence_id}.started` and `.advanced` at start, and `.completed` /
`.step_completed` at execute. Both success and failure of the underlying executes remain audited
by the unchanged per-workflow audit path; the sequence events are purely additive provenance for
the chain and never gate or replace the per-step audit.

### 16.8 Tests

`tests/test_workflow_engine.py` gained `TestSequenceDefinitions`,
`TestRegistryDiscoveryMetadata`, `TestListUserRuns`, `TestListSequences`,
`TestStartRunLineage`, and `TestExecuteStepSequenceAudit` (~21 cases): sequence registry
validates + serializes with per-step status; definitions expose the new metadata; `list_user_runs`
is owner-scoped and filterable by status; `start_run` persists lineage and **rejects an
unowned `parent_run_id`**; and the orchestrator audit events fire on start/advance/execute.
Full file: **64 passed** via
`test_db_name=test_heliumdb python -m pytest tests/test_workflow_engine.py -o addopts="" -p no:cacheprovider -q`.

### 16.9 Validation

- **FE compiles clean:** webpack `No issues found.` (fork-ts-checker — the TS-clean signal).
- **Routes registered + auth-gated:** hitting the backend directly (`:8000`) returns the
  structured `{"message":"Unauthorized","code":401}` for `GET /runs`, `GET /sequences`, and
  `GET /runs/{id}`, confirming registration and that `GET /runs` resolves to the list route
  (not shadowed by `/runs/{run_id}`).
- **Engine logic:** the 64 unit tests cover the new discovery/lineage/audit surface.

### 16.10 Remaining gaps & next

- **Authenticated live E2E + browser render not captured here:** the screenshot tool's browser
  context is unauthenticated (shows Sign In) and a curl chain would create real Company + Site
  rows in the dev DB without a clean teardown path in this session. The dashboard/orchestrator
  reuse the already-live-proven engine (§15.8) and are covered by unit tests + the route/auth
  probe above; the user's own authenticated session can verify the UI visually.
- **Sequence catalog is single-entry:** only `onboarding` exists; both the FE start-route maps
  (`WORKFLOW_START_ROUTES` / `SEQUENCE_START_ROUTES`) and the registry are additive and ready for
  more.
- **Resume is engine-state-driven:** the generic run page trusts the persisted `current_step` +
  step inputs; it does not re-validate completed steps client-side (the server re-validates on
  save/execute regardless).
- **Next:** richer suggested-next surfacing (driven by `suggested_next`) and the deferred
  governed-surface pilot (preview → existing manual confirmation UI; engine never auto-executes a
  governed terminal).

## 17. Build log — Native Onboarding Experience, Phase 2 `[BUILT]`

Phase 1 added discovery/orchestration over the engine. Phase 2 adds **three new workflows** plus
**two cross-cutting systems** (declarative prerequisites + read-only completion metrics), all by
**reusing existing domain endpoints, permissions, and audit** — no new infrastructure, no AI
execution, no manual-form replacement, no governed-flow change, and no authorization bypass. Every
new workflow is **independently executable** and runs the unchanged preview → confirm → execute
handshake. (Project == Site; "Project" is a UI label only — the backend `Site` entity is untouched.)

### 17.1 Goal & what it proves

1. **The engine generalizes beyond single-entity create:** the new workflows cover a **two-call
   composite** (Invite User = create-or-get user + add company membership), a **multipart file
   write** (Document Upload), and a **long-running async trigger** (Parse Document → an
   `ai_parsing_run` the user tracks in the Data Room). Each delegates to the **same** domain
   endpoint the manual UI already uses — zero endpoint logic is duplicated.
2. **File uploads fit the JSON engine without storing bytes:** a step declares
   `multipart_file_field` and runs via a sibling **`execute-file`** route that shares the engine's
   perm / idempotency / reconfirm / audit pipeline. Targets (`site_id`, `document_id`) are still
   collected as ordinary JSON; the file part is **never persisted in run JSONB**.
3. **Dependencies become declarative, not authority:** a `PrerequisiteDef` advertises what a
   workflow needs (e.g. "an accessible project", "an uploaded file") via **read-only, user-scoped**
   evaluators. Prerequisites power a dashboard "blocked" affordance but **never replace
   authorization** (`can_start` stays a separate permission decision).
4. **Cascading options are context-aware:** collect-step options resolve against the run's
   already-collected inputs (project → its documents → that document's files), all **authz-scoped
   read-only** reads; the FE refreshes the run after each save to pull the next level.
5. **Completion is measurable read-only:** a metrics endpoint aggregates the caller's own runs
   (completion %, abandonment %, avg/median duration, per-workflow rollups) with an optional
   platform-bypass org-wide scope — **no schema change, zero writes**.

### 17.2 Files changed

**Backend** (`backend/ilios-server`):

- `app/services/workflows/definitions.py` — added `PrerequisiteDef` (+ `prerequisites` on
  `WorkflowDef`) and `StepDef.multipart_file_field`; the three new `WorkflowDef`s (`invite_user`,
  `document_upload`, `parse_document`) with their `STEP_INPUT_SCHEMAS` bindings; and the
  **context-aware** `resolve_options(...)` dynamic resolvers (`accessible_projects`,
  `project_documents` [reads `context.site_id`], `document_files` [reads `context.document_id`],
  `membership_companies`, `membership_roles`) — all authz-scoped read-only. `validate_definition`
  extended to cover the new fields and that every `evaluator_key` exists.
- `app/services/workflows/executors.py` — split the executor maps into `EXECUTORS` (JSON) and
  `FILE_EXECUTORS` (multipart, signature includes the `UploadFile` + `BackgroundTasks`). Added
  `_execute_invite_user` (create-or-get user + add membership, **idempotent** — existing
  email/membership read back rather than erroring → `("user", id)`), `_execute_parse_document`
  (→ existing `trigger_file_parsing` → `("ai_parsing_run", run_id)`, honest 202/async), and
  `_execute_document_upload` (→ existing `upload_file` endpoint under the **same** auth dependency
  the manual UI uses → `("file", id)`). No domain endpoint logic is reimplemented.
- `app/services/workflows/engine.py` — `execute_file_step` (mirrors `execute_step`'s
  perm/idempotency/reconfirm/audit, then dispatches to the `FILE_EXECUTORS`); a read-only,
  user-scoped `PREREQUISITE_EVALUATORS` registry (`has_accessible_project`, `has_uploaded_file`)
  with prerequisites evaluated during serialization (populating `blocked_reason` = first unmet
  message); run collected-inputs threaded as `context` into `serialize_definition` →
  `resolve_options`; and `compute_metrics(scope="me"|"all")` (owner default; `"all"` gated to
  platform-bypass, else 403; unknown scope → 400) computing totals, rates over **closed** runs,
  and avg/median durations with a per-workflow rollup. **`execute_step` behavior is unchanged.**
- `app/schema/workflow.py` — `multipart_file_field` on `WorkflowStepSchema`; `WorkflowPrerequisiteSchema`
  + `prerequisites[]` / `blocked_reason` on `WorkflowDefinitionSchema`; `WorkflowMetricsItemSchema`
  + `WorkflowMetricsResponse`.
- `app/routers/workflows.py` — `POST /api/workflows/runs/{run_id}/steps/{step_id}/execute-file`
  (multipart: `confirm_token` + optional `idempotency_key` as form fields + the `file` part) and
  `GET /api/workflows/metrics?scope=me` (default; `scope=all` for platform-bypass). Engine errors
  surface as the structured `JSONResponse` payload (consistent with the existing handler).
- `tests/test_workflow_engine.py` — Phase-2 suites (see §17.7).

**Frontend** (`frontend/rea-investment-fe`):

- `src/api/workflows.ts` — `multipart_file_field` on `WorkflowStepSchema`;
  `WorkflowPrerequisiteSchema` + `prerequisites[]` / `blocked_reason` on `WorkflowDefinitionSchema`;
  `WorkflowMetricsItemSchema` / `WorkflowMetricsResponse` (+ `WorkflowMetricsScope`); `executeFile`
  (FormData multipart) and `getMetrics(scope)` methods.
- `src/components/common/Wizard/{types.ts,Wizard.tsx,WizardReviewStep.tsx}` — additive, **optional**
  `onExecuteFile` + `onReloadRun` props. The wizard holds a **live copy** of the definition so
  cascading options refresh after each save (via `onReloadRun`), renders a **file input on the
  review step** when the active execute step declares `multipart_file_field` (confirm disabled until
  a file is chosen), and dispatches that step through `onExecuteFile`. **Static flows
  (add_company / add_site) pass neither prop and are completely unaffected.**
- `src/modules/workflows/GenericWorkflowStartPage.tsx` (new) — generic start page
  (`/workflows/start/:workflowId`) that starts a run for any registered workflow and wires
  `onExecuteFile` + `onReloadRun` + landing redirect.
- `src/modules/workflows/{index.ts,landing.ts}`, `src/App.tsx` — export + route the new page;
  `WORKFLOW_START_ROUTES` gains the three Phase-2 ids → `/workflows/start/<id>`.
- `src/modules/workflows/WorkflowDashboardPage.tsx` — a read-only **"Your activity"** metrics panel
  (`getMetrics('me')`) and **prerequisite-blocked** Available cards (Start disabled + the
  `blocked_reason` caption).

No existing manual form, executor, or write path was modified.

### 17.3 Routes

| Method & path | Purpose | Added? |
|---|---|---|
| `POST /api/workflows/runs/{run_id}/steps/{step_id}/execute-file` | Multipart execute for steps declaring `multipart_file_field` (document upload). Shares the full engine pipeline; bytes never enter run state. | **new** |
| `GET /api/workflows/metrics?scope=me` | Read-only completion metrics; `scope=all` (platform-bypass only) for org-wide. | **new** |
| `POST …/steps/{id}/execute` · `…/preview` · `PATCH …/steps/{id}` · `GET /runs` · `…/sequences` | Unchanged engine handshake + discovery. | — |

FE routes: adds `/workflows/start/:workflowId` (generic start) alongside the existing dashboard,
orchestrator, resume, and bespoke add-company / add-site routes.

### 17.4 Permission model

- **Reuses existing entry permissions; adds none for execution.** `invite_user` →
  `platform_admin` (creating a user needs global admin); `document_upload` / `parse_document` →
  Diligence-edit, resolved by the engine's existing token map and ultimately by the **same domain
  endpoint** the manual UI calls. The new surfaces add **zero** authority.
- **Prerequisites are NOT authorization.** `PREREQUISITE_EVALUATORS` are pure reads scoped to the
  caller's accessible entities; unknown evaluator keys fail closed. A met prerequisite never grants
  start rights, and an unmet one is advisory (the server still gates the actual start/execute).
- **Dynamic options are permission-scoped reads, not visibility-scoped.** The data-room resolvers
  (`accessible_projects`, `project_documents`, `document_files`) and the upload/parse prerequisites
  scope to the caller's **Diligence `edit`** set per site — NOT mere site visibility — via
  `_diligence_editable_site_ids`, which calls the canonical per-context `require_module_permission`
  for each candidate site (company- or project-level grant). This mirrors the per-document guard
  the Data Room list/upload/parse endpoints already enforce, so a user who can *see* a project but
  cannot manage its Data Room never has its project/document/file labels disclosed in a dropdown or
  is falsely told a prerequisite is "met". The membership resolvers stay company-admin scoped; the
  engine never widens visibility to populate a dropdown, and the underlying endpoints remain the
  authoritative guard at execute time.
- **Metrics are owner-scoped by default.** `scope=me` returns only the caller's runs; `scope=all`
  is refused (403) for non-platform-bypass callers; an unknown scope is a 400.

### 17.5 Multipart upload (no bytes in JSONB)

The upload workflow collects its **targets** (`site_id`, `document_id`) as ordinary JSON save
steps, then its terminal execute step declares `multipart_file_field="file"`. The FE renders a file
picker on the review step and posts to `execute-file` with the confirm token + idempotency key as
**form fields** and the file as the multipart part. The engine reconstructs the normal
`ExecuteRequest`, runs the identical perm / idempotency / reconfirm / audit path, and hands the
`UploadFile` (+ `BackgroundTasks`) to the existing `upload_file` endpoint. The file's bytes are
**never** written to run state — only the resulting `("file", id)` entity ref is recorded.

### 17.6 Prerequisites, cascading options & metrics

- **Prerequisites:** serialized per-caller as `prerequisites[]` with `met` + `unmet_message`;
  `blocked_reason` is the first unmet message (null when all met). The dashboard disables Start and
  shows the message; the server remains authoritative.
- **Cascading options:** `resolve_options` reads the run's collected inputs as `context`, so the
  document picker lists only the chosen project's documents and the file picker only that
  document's files. The FE calls `onReloadRun` after each save and re-binds the live definition so
  the next step's options reflect the new context.
- **Metrics:** rates are fractions in `[0, 1]` over **closed** runs (completed + abandoned);
  durations are avg + median seconds; `by_workflow[]` carries the same shape per workflow id. All
  derived read-only from `workflow_runs` — no schema change, no writes.

### 17.7 Tests

`tests/test_workflow_engine.py` gained Phase-2 suites covering: the three new definitions validate
and serialize (including `multipart_file_field` and `prerequisites[]`); `invite_user` **idempotency**
(existing email/membership read back, not re-created); the parse executor returns the
`("ai_parsing_run", id)` entity ref; the multipart `execute-file` happy path plus token/permission
guards; prerequisite-blocked serialization (`blocked_reason` populated); metrics aggregation
(owner scope, rates, avg/median, per-workflow rollup, `scope=all` gating); and dynamic-option
authz scoping (context-filtered, caller-visible only). Full file: **110 passed** (64 prior + 46
new) via
`test_db_name=test_heliumdb python -m pytest tests/test_workflow_engine.py -o addopts="" -p no:cacheprovider -q`.

### 17.8 Validation

- **Backend:** the full `test_workflow_engine.py` is green at **110 passed** (the 64 Phase-0/1
  tests stay green).
- **FE compiles clean:** webpack `No issues found.` (fork-ts-checker — the TS-clean signal); the
  changed files also pass ESLint with no errors (only pre-existing `no-non-null-assertion` warnings
  that match the add_company / add_site pages).
- **Reuse-only confirmed:** the new executors call the existing `users` / `workspace members` /
  `due-diligence upload` / `due-diligence parsing` endpoints; no endpoint logic is duplicated and
  no governed-confirmation flow is touched.

### 17.9 Remaining gaps & next

- **Authenticated live E2E not captured here:** as in §16.10, real runs would create User /
  membership / file / parse-run rows in the dev DB without a clean teardown path this session;
  coverage is the 110 unit tests + the reuse of the already-live-proven engine and domain
  endpoints. The user's own authenticated session can verify the UI visually.
- **Parse completion is async/honest:** the parse executor returns the `ai_parsing_run` id at 202;
  the workflow does **not** poll to "done" — the user tracks completion + candidate review in the
  existing Data Room (no synthetic completion state is fabricated).
- **Metrics are aggregate-only:** no time-series/trend or funnel breakdown yet; `by_workflow`
  rollups are the finest grain. `scope=all` exists but has no dedicated admin UI panel.
- **First AI read-only "workflow advisor" sprint (proposed, not built):** a strictly read-only
  advisor that, given the caller's runs + prerequisites + metrics, **suggests** the next workflow
  or surfaces the most common abandonment point — **advice only**, never auto-starting or
  auto-executing anything, preserving the standing AI boundary (§9): the engine never
  auto-executes, and a human still drives every preview → confirm → execute.
