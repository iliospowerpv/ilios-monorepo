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
