# Baseline Activation Effective-Date & Audit Events — Phase B3 Audit & Design

> **Sprint type:** Audit / design only. **No production code was changed.** This
> document traces the current implementation and proposes a Phase B3 plan; it does
> not modify behavior, math, lifecycle, authorization, weather semantics, device
> mappings, or any Site 4 data.

---

## 1. Executive Summary

The expected-baseline lifecycle (`create → approve → activate → supersede`) is
already well-separated and governance-aligned in two important respects:

- **Approval is not activation.** They are distinct endpoints, distinct CRUD
  methods, and distinct status transitions; the approve handler docstring and the
  activate handler docstring both state this explicitly.
- **Activation does not silently rewrite history.** A replacement baseline always
  takes `active_from = now`, the superseded baseline keeps its own
  `[active_from, active_to)` window, and the period-effective read path selects the
  baseline that *owned* each timestamp. Site 4 demonstrates a clean, gap-free,
  overlap-free boundary between baseline #3 and #4.

The **principal gap is auditability of the activation event itself**:

1. **No durable, queryable audit-log rows are written for any baseline lifecycle
   action.** `create`, `approve`, `activate`, and `supersede` only stamp columns
   and/or embed a JSON sub-object on the affected row. The shared `audit_logs`
   table — used for telemetry refresh, admin grants, site archive/restore, and
   auth — is *not* used for baseline lifecycle.
2. **Activator attribution is buried, not first-class.** `activated_by_user_id`
   and `activated_at` live only inside `validation_result_json["activation"]`. They
   are not columns, are not indexed/queryable, and are not serialized by
   `ExpectedBaselineResponse`, so the frontend history panel cannot show *who*
   activated *when* or *what was waived*.
3. **Blocked/failed activations leave no durable trail.** A `hard_invalid` or
   un-acknowledged-warning block emits only an ephemeral application `logger.info`
   line; there is no `audit_logs` record of the attempt, actor, or reason.

Phase B3’s recommended scope is therefore **additive observability**: write
best-effort `audit_logs` events for every lifecycle action (including blocked
attempts), and — as a separate, optional, migration-bearing decision — promote
activator attribution to first-class serialized fields. None of this requires any
change to baseline math, the expected model, effective-date selection, lifecycle
authorization, or weather/device logic.

---

## 2. Current Activation Lifecycle

All lifecycle writes live in
`backend/ilios-server/app/crud/telemetry_expected.py`
(`TelemetryExpectedBaselineCRUD`); endpoints live in
`backend/ilios-server/app/routers/telemetry/v2.py`.

### 2.1 Create (draft)
- **CRUD:** `create_draft` (`telemetry_expected.py:237`). Sets
  `status = draft`, `created_by_user_id`, and snapshots site-derived assumptions.
  Commits. **No audit-log row.**
- The supported V2 path is the project-facts bridge (`create-draft-from-facts`);
  the legacy SAFL-snapshot create endpoint remains deprecated.

### 2.2 Approve
- **Endpoint:** `POST /api/telemetry/v2/expected-baselines/{baseline_id}/approve`
  → `approve_expected_baseline` (`v2.py:3804`).
- **CRUD:** `approve` (`telemetry_expected.py:294`).
- **Guards:** site visibility (`get_authorized_site_with_company_admin`) →
  `enforce_baseline_lifecycle_authority(action_code="approve")` (telemetry-admin
  **AND** company-admin, or platform bypass), checked **before** any write.
- **Transition:** `draft | in_review | rejected → approved`.
- **Stamps:** `reviewed_by`/`reviewed_at` (only if `reviewed_at` is null),
  `approved_by`/`approved_at`. Commits.
- **Audit:** column stamps + one `logger.info`. **No audit-log row.** Docstring:
  “Activation is a separate, explicit step.”

### 2.3 Activate (with inline supersede)
- **Endpoint:** `POST /api/telemetry/v2/expected-baselines/{baseline_id}/activate`
  → `activate_expected_baseline` (`v2.py:3845`).
- **CRUD:** `activate` (`telemetry_expected.py:317`).
- **Request body:** `BaselineActivateRequest { acknowledge_warnings: bool,
  activation_source_note: str | None }` (optional; defaults applied).
- **Guards:** site visibility → `enforce_baseline_lifecycle_authority(
  action_code="activate")` before any write.
- **Ordering inside `activate` (all fail-closed, no commit on block):**
  1. **Approval gate** — only `approved` may activate, else `BaselineActivationError`
     → 409 (string).
  2. **Physics gate** — `validate_baseline(baseline,
     validation_source_mode="activation_gate")`
     (`services/telemetry/baseline_physics_validation.py`):
     - `report.is_blocking` → `BaselinePhysicsBlockedError(reason="hard_invalid")`.
     - `report.has_warnings and not acknowledge_warnings` →
       `reason="warnings_require_ack"`.
     - `report.has_warnings and acknowledge_warnings and not note` →
       `reason="source_note_required"`.
     - Each block is returned as a **structured 409** via `JSONResponse`
       (`_baseline_block_body`) so the global handler does not stringify it.
  3. **Supersede + activate (atomic)** — the prior `active` row for the same
     `(site_id, baseline_type)` is locked `with_for_update()`; if present and
     distinct: `prior.status = superseded`, `prior.active_to = now`,
     `baseline.supersedes_baseline_id = prior.id`.
  4. `baseline.status = active`, `active_to = None`, `active_from = now` for a
     replacement or `_first_active_from(baseline, now)` for the first baseline.
  5. Persist `validation_result_json = report.to_dict()` **plus** an `activation`
     sub-object (`acknowledged_warnings`, `source_note`, `activated_by_user_id`,
     `activated_at`) and `validation_policy_version = report.policy_version`, in the
     **same** transaction. Single commit.
- **Audit:** verdict + waiver JSON on the row; `logger.info` on success;
  `logger.info` (only) on block. **No audit-log row in any branch.**

### 2.4 Supersede
Supersession is **not** a separate endpoint or method; it is the inline step
inside `activate` (§2.3.3). The only durable evidence is: the prior row’s
`status = superseded` + `active_to`, and the new row’s `supersedes_baseline_id`.

---

## 3. Current Effective-Date Behavior

- **Columns:** `active_from` (timestamp, naive UTC), `active_to` (timestamp, naive
  UTC, `NULL` = open-ended/current).
- **Replacement activation:** `active_from = now`, `active_to = NULL`; the prior
  active row’s `active_to = now`. The new and prior windows therefore **abut
  exactly** (same `now` instant), producing no gap and no overlap.
- **First activation for a site:** `active_from = _first_active_from(baseline,
  now)` — a `weather_adjusted_model` carrying a `pto_date` is effective from PTO so
  the expected curve covers telemetry recorded before activation (onboarding);
  otherwise `now`.
- **Backdating:** the only implicit backdate is the PTO-anchored *first* baseline.
  There is **no user-supplied effective date**; replacement activations are always
  `now`. (Changing this is explicitly out of scope — see §16/§18.)
- **Timezone:** `active_from`/`active_to` are naive UTC; site-local concerns
  (day boundary) are handled elsewhere and are not part of activation timing.

---

## 4. Current Supersession Behavior

- Enforced atomically in `activate` with `with_for_update()` on the prior active
  row, so two concurrent activations cannot both win.
- A partial-unique index — `uq_telemetry_expected_baseline_active UNIQUE
  (site_id, baseline_type) WHERE status = 'active'` — guarantees at most one
  active baseline per `(site, type)` at the database level.
- The superseded baseline is **never deleted or edited beyond** `status` +
  `active_to`; its inputs and validation history are preserved (immutable
  ownership of its historical window).
- Supersession is fully reconstructable from `supersedes_baseline_id` +
  `active_from`/`active_to` chaining, but it is **not** independently event-logged.

---

## 5. Current Attribution Model

| Concern  | Where it lives | First-class column? | Serialized to FE? |
| --- | --- | --- | --- |
| Creator  | `created_by_user_id` | ✅ column | (per response schema) |
| Reviewer | `reviewed_by` / `reviewed_at` | ✅ columns | (per response schema) |
| Approver | `approved_by` / `approved_at` | ✅ columns | (per response schema) |
| **Activator** | `validation_result_json["activation"].activated_by_user_id` / `.activated_at` | ❌ JSON only | ❌ not serialized |
| **Waiver** | `validation_result_json["activation"].acknowledged_warnings` / `.source_note` | ❌ JSON only | ❌ not serialized |

**Key asymmetry:** create/review/approve attribution are first-class columns;
**activation** attribution and the **warning-waiver trail** are buried inside
`validation_result_json`, which `ExpectedBaselineResponse` does **not** serialize.
This is why the B2 `ValidationHistoryPanel` can show version/status/window but
cannot show who activated, when, or what was waived.

---

## 6. Current Audit / Event Model

### 6.1 The shared audit-log facility (exists, unused for baselines)
- **Model:** `AuditLog` (`app/models/audit_log.py`) → table `audit_logs`:
  `id`, `created_at` (server default utcnow), `source` (VARCHAR, nullable),
  `action` (VARCHAR, nullable), `is_success` (Boolean, **not null**), `details`
  (VARCHAR, nullable), `user_id` (FK → `users.id` `ON DELETE SET NULL`). Indexed on
  `created_at DESC` and `user_id`.
- **Writer:** `AuditLogCRUD.create_item` (`app/crud/audit_log.py`).
- **Best-effort helper:** `create_audit_log(request, db_session, action, details,
  is_success=True)` (`app/helpers/telemetry/audit.py`) — wraps the CRUD in a
  try/except that only logs a warning on failure (never raises), and stamps
  `source="telemetry"`, `user_id = request.state.current_user_id`.

### 6.2 Existing audit-log usage (pattern reference)
- **Telemetry V2 (`v2.py`):** `telemetry_v2_site_mapping_saved`,
  `telemetry_v2_device_mappings_saved`, `telemetry_v2_refresh_readings`,
  `telemetry_v2_scheduler_update`, `telemetry_v2_backfill_readings`.
- **Global admin (`admin/global_admin.py`):** `grant`/`revoke`, **including failed
  attempts** via `_record_audit` (a precedent for auditing failures).
- **Asset management (`assets_management/sites.py`):** `archive_site`,
  `restore_site` via `AuditLogCRUD`.
- **Auth:** `AuditingMiddleware` logs login/logout.

### 6.3 Baseline lifecycle event model (current)
The **only** structured event for baselines is the `activation` sub-object stamped
on the activated row’s `validation_result_json`. There is **no** event for create,
approve, or supersede, and **no** event for blocked attempts. Consequences:
- Activation attribution/waiver is not queryable across baselines.
- A blocked activation (e.g., someone repeatedly attempting to activate a
  `hard_invalid` baseline) is invisible to any durable audit query.
- Reconstructing “who activated what, when, and why” requires reading per-row JSON
  rather than a single chronological audit stream.

---

## 7. Existing Data-Model Inventory (`telemetry_expected_baselines`)

Lifecycle-relevant columns (from live schema):

- **Identity/scope:** `id`, `company_id`, `site_id`, `baseline_name`,
  `baseline_type` (`telemetry_baseline_type_enum`), `version`.
- **Status:** `status` (`telemetry_baseline_status_enum`: draft, in_review,
  approved, active, superseded, rejected, …).
- **Provenance:** `source_type` (`telemetry_baseline_source_enum`),
  `source_document_id`, `source_project_fact_id`.
- **Attribution:** `created_by_user_id`, `reviewed_by`/`reviewed_at`,
  `approved_by`/`approved_at` (FKs → `users` `ON DELETE SET NULL`).
- **Effective window:** `active_from`, `active_to`, `supersedes_baseline_id`.
- **Validation/waiver:** `validation_result_json` (jsonb, holds the `activation`
  sub-object), `validation_policy_version` (VARCHAR).
- **Timestamps:** `created_at`, `updated_at` (both not-null, default now()).
- **Constraints:** PK `id`; indexes on `company_id`, `site_id`, `status`; partial
  unique `uq_telemetry_expected_baseline_active (site_id, baseline_type) WHERE
  status='active'`; FKs to companies/sites/users.

**Observation:** there is **no** `activated_by` / `activated_at` column (unlike
`reviewed_*`/`approved_*`), confirming the attribution asymmetry in §5.

Related: `telemetry_expected_baseline_points` (design-estimate monthly/annual
points) — out of scope for B3 timing/audit, listed for completeness.

---

## 8. Existing API Inventory

| Action | Method + route | Handler (`v2.py`) | Notes |
| --- | --- | --- | --- |
| Approve | `POST /api/telemetry/v2/expected-baselines/{id}/approve` | `approve_expected_baseline` (3804) | telemetry-admin + company-admin; 409 on bad status |
| Activate | `POST /api/telemetry/v2/expected-baselines/{id}/activate` | `activate_expected_baseline` (3845) | structured 409 on physics block; inline supersede |
| List | `GET /api/telemetry/v2/sites/{id}/expected-baselines` | (list handler) | history rows; does **not** include `validation_result_json` |
| Active | `GET /api/telemetry/v2/sites/{id}/expected-baselines/active` | (active handler) | enveloped with flags |
| Diff | `GET /api/telemetry/v2/expected-baselines/{id}/diff` | (diff handler) | from/to validation verdicts (B1/B2) |
| Preview | `GET /api/telemetry/v2/sites/{id}/expected-preview` | `get_expected_preview` (3911) | read-only expected vs actual |

Response schema: `ExpectedBaselineResponse` (serializes status/window/attribution
columns) — **does not** serialize `validation_result_json`, so the activation
sub-object never reaches the client today.

Frontend client: `ApiClient.telemetryV2`
(`frontend/rea-investment-fe/src/api/telemetryV2.ts`) —
`approveExpectedBaseline`, `activateExpectedBaseline`, `listExpectedBaselines`,
`getActiveExpectedBaseline`, `getBaselineDiff`.

---

## 9. Existing Frontend UX Inventory

Primary surface:
`frontend/rea-investment-fe/src/modules/project-hub/pages/AssetManagementSiteDetails/tabs/Reconciliation/components/DraftBaselineReviewPanel.tsx`.

- **Lifecycle gating:** `viewer_can_manage_lifecycle` (telemetry-admin +
  company-admin); unauthorized → disabled buttons with lock icon + tooltip.
- **Approve dialog** (`ApproveConfirmationSummary`): read-only provenance summary;
  explicitly states approval ≠ activation. No user input.
- **Activate dialog** (`ActivateConfirmationSummary` + `ActivationReadinessSummary`
  from B2): shows readiness (blocking must be 0, warnings to ack, missing inputs,
  PTO presence, which baseline gets superseded). Captures the **activation source
  note** (required when the backend returns a warning verdict) and a per-warning
  acknowledgement checklist (**visual-only**; the real waiver is the single
  `acknowledge_warnings: true` flag). States that activation stamps `active_from`
  at the activation moment and that historical periods keep their prior baseline.
- **History** (`ValidationHistoryPanel` from B2): built from existing list rows
  (version/status/active window). **Cannot** show activator/waiver trail because
  the API does not serialize it (§5, §8).
- **Effective date:** surfaced descriptively (“stamps `active_from` now”), never
  user-editable.

---

## 10. Existing Test Inventory

**Backend (pytest, `backend/ilios-server/tests/`):**
- `integration/test_baseline_lifecycle_endpoints.py` —
  `test_approve_forbidden_for_non_admin_no_side_effect`,
  `test_approve_succeeds_for_platform_bypass`,
  `test_activate_succeeds_for_platform_bypass`,
  `test_active_endpoint_is_enveloped_with_flags`.
- `unit/telemetry/period_effective_baseline_test.py` — period-effective
  selection across active/superseded windows.
- `unit/telemetry/test_v2_expected_wiring.py` — expected plumbing across lifecycle
  states.
- `test_weather_declaration_guard.py` — activation safety gates.

**Frontend (jest):**
- `DraftBaselineReviewPanel.test.tsx` — approve calls only approve + refetch;
  activate calls only activate + refetch; activate dialog explains period-effective
  history, supersession, design-estimate separation.
- `ValidationHistoryPanel.test.tsx`, `ActivationReadinessSummary.test.tsx`,
  `ValidationSummaryPanel.test.tsx` (B2).

**Gap:** no test asserts that a lifecycle action **writes an audit-log row** (none
is written today), nor that a **blocked** activation is recorded.

---

## 11. Site 4 (110 Shawmut) Period-Effective Assessment

Read-only inspection (no mutation performed):

| id | status | type | active_from | active_to | supersedes | policy_ver | activation JSON |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | superseded | weather_adjusted_model | 2026-05-11 00:00:00 | 2026-06-20 16:33:48.801667 | — | (null) | — (none) |
| 4 | active | weather_adjusted_model | 2026-06-20 16:33:48.801667 | (null) | 3 | baseline-physics-v1 | present |

- **Clean boundary:** #3.`active_to` **exactly equals** #4.`active_from`
  (2026-06-20 16:33:48.801667). With `[active_from, active_to)` half-open
  semantics this yields **no gap and no overlap** — every timestamp is owned by
  exactly one baseline.
- **Historical ownership preserved:** #3 retains its
  `[2026-05-11, 2026-06-20 16:33:48.8)` window; #4 owns
  `[2026-06-20 16:33:48.8, ∞)`. #3.`active_from = 2026-05-11` is the PTO-anchored
  first-baseline window (onboarding coverage), consistent with `_first_active_from`.
- **Attribution:** both rows reviewed/approved by user 1. #4 carries an `activation`
  JSON sub-object (`activated_by_user_id=1`, `acknowledged_warnings=false`,
  `source_note` documenting that it supersedes physically-invalid #3 and that #3
  was left unedited). #3 has **no** activation JSON and **null**
  `validation_policy_version` — a **legacy/pre-physics-policy** baseline. Any B3
  audit backfill or event read path **must tolerate** missing policy version /
  missing activation JSON.
- **Verdict:** Site 4 is a faithful example of correct period-effective ownership.
  **B3 must not mutate, approve, activate, or re-activate anything on Site 4.** The
  before/after invariant is: #3 stays superseded (350.0 thermal, invalid), #4 stays
  active (−0.35 thermal), both windows unchanged.

---

## 12. Gaps and Risks

| # | Gap / Risk | Severity | Notes |
| --- | --- | --- | --- |
| G1 | No durable `audit_logs` events for create/approve/activate/supersede | High | Activation attribution lives only on the row JSON; no chronological stream |
| G2 | Blocked/failed activations not audited | High | Only ephemeral `logger.info`; precedent for auditing failures exists in global-admin |
| G3 | Activator attribution not first-class / not serialized | Medium | `activated_by`/`activated_at` are JSON-only; FE history cannot show them |
| G4 | Waiver trail (acknowledged_warnings/source_note) not serialized | Medium | B2 history panel cannot display what was waived |
| G5 | Supersession is inferred, not event-logged | Low | Reconstructable via `supersedes_baseline_id` + windows |
| G6 | Legacy rows have null `validation_policy_version` / no activation JSON (Site 4 #3) | Medium | Any event/read path must be null-tolerant |
| G7 | `details` is VARCHAR (string), not jsonb | Low | Structured event payloads would be stored as JSON strings unless a new column is added |
| G8 | No user-auditable effective date beyond `now`/PTO | Low / out-of-scope | Backdating is out of scope unless separately approved (§16/§18) |
| G9 | `activated_at` (naive UTC, in JSON) vs `audit_logs.created_at` could differ slightly | Low | Mitigate by passing the same `now` instant into the event detail |

---

## 13. Recommended Phase B3 Implementation Plan

**Guiding principle:** additive observability only. Do not touch math, the expected
model, effective-date selection, lifecycle authorization, weather/device logic, or
Site 4. Make audit writes **best-effort** so they can never break activation.

### Tier 1 — Durable lifecycle audit events (no migration) — *recommended core*
Reuse the existing best-effort helper pattern (`create_audit_log` /
`AuditLogCRUD`). Emit one `audit_logs` row per lifecycle action, with `source`
(either reuse `"telemetry"` or introduce `"telemetry_baseline"` — see §16/Open
Decisions) and an `action` verb, `is_success`, and a compact `details` string that
encodes the key facts (JSON-encoded into the existing VARCHAR `details`):

- `baseline_created` — `{baseline_id, site_id, company_id, version, source_type}`.
- `baseline_approved` — `{baseline_id, site_id, prior_status}`.
- `baseline_activated` — `{baseline_id, site_id, supersedes_baseline_id,
  active_from, acknowledged_warnings, source_note, policy_version}` (the same `now`
  instant used for `active_from`, to avoid G9 drift).
- `baseline_activation_blocked` — `is_success=false`,
  `{baseline_id, site_id, reason}` where reason ∈
  `hard_invalid | warnings_require_ack | source_note_required | invalid_status`.
- *(Optional)* `baseline_superseded` — emitted alongside `baseline_activated`, or
  folded into it (open decision G5/§16).

**Write placement:** in the **router handlers** (`approve_expected_baseline`,
`activate_expected_baseline`), *after* the CRUD returns (success) or in the
`except` branches (blocked/failed), so the audit write has access to the `Request`
(for `current_user_id`) and never participates in the lifecycle transaction. This
keeps audit failures fully isolated from baseline state (best-effort, never
raises). Create-draft auditing can be added at its endpoint similarly.

**Migration impact:** **none.** `audit_logs` already exists and `details` is a
nullable VARCHAR; storing a JSON-encoded string requires no schema change.

### Tier 2 — First-class activator attribution (migration-bearing) — *optional*
Promote `activated_by` (FK → users, `ON DELETE SET NULL`) and `activated_at`
(timestamp) to **nullable, additive** columns on `telemetry_expected_baselines`,
mirroring `approved_by`/`approved_at`. Populate them in `activate` alongside the
existing JSON (keep the JSON for the full waiver trail). Then serialize
`activated_by`/`activated_at` (and optionally `acknowledged_warnings`/
`source_note`) as **additive optional** fields on `ExpectedBaselineResponse`.

- **Why optional/separate:** this is the only part needing a migration; it directly
  unblocks the B2 `ValidationHistoryPanel` waiver/activator display (G3/G4).
- **Migration impact:** one Alembic migration adding two nullable columns + FK.
  Backfill is **not** required (legacy rows like Site 4 #3 simply read null);
  optionally a one-time, read-then-write backfill from existing
  `validation_result_json["activation"]` could populate historical rows **without
  touching Site 4’s window/status** (attribution-only, no lifecycle change) — gated
  as a separate, explicitly-approved step.

### Tier 3 — Frontend surfacing (additive) — *follows Tier 1/2*
- If Tier 2 ships: extend `ValidationHistoryPanel` to show activator + activated_at
  + waiver note from the new serialized fields.
- Optionally add a read-only “Activation events” list fed by a new read-only
  audit-query endpoint (open decision — adds an endpoint; can be deferred).

### Sequencing
1. Tier 1 (events) — highest value, zero migration, lowest risk.
2. Tier 2 (columns + serialization) — if/when product approves the migration.
3. Tier 3 (FE) — after Tier 2.

---

## 14. Mutation Boundaries

**This sprint:** documentation only — **no production code changed** (confirmed in
§“Confirmation” below).

**For the Phase B3 implementation that this plan describes:**
- **Allowed (additive):** writing `audit_logs` rows (best-effort); *optionally*
  adding two nullable attribution columns + a forward-only Alembic migration;
  serializing additive optional response fields; additive FE display.
- **Forbidden:** any change to baseline math / expected model / loss assumptions;
  any change to effective-date selection (`get_baselines_effective_in_window`,
  `_effective_baseline_at`, `compute_site_expected_period_effective`); any change to
  `active_from`/`active_to` assignment semantics; any change to lifecycle
  authorization (`enforce_baseline_lifecycle_authority`) or visibility resolvers;
  any historical-expected rewrite; WS.5; weather semantics; device mappings;
  backdating/user-chosen effective dates (out of scope unless separately approved).
- **Site 4:** strictly read-only. No approve/activate/supersede/edit. Invariant:
  #3 superseded (thermal 350.0) and #4 active (thermal −0.35) with identical
  windows before and after.
- **Audit-write isolation:** lifecycle audit writes must never run inside the
  baseline transaction and must never raise — a failed audit write must not block or
  roll back an approve/activate.

---

## 15. Browser-Validation Strategy

Use a **non-Site-4** demo/test site with telemetry-admin + company-admin.

1. **Happy path:** create draft → approve → activate. After each, query
   `audit_logs` (newest first) and confirm one row per action with correct
   `action`, `user_id`, `is_success=true`, and `details` payload (incl.
   `supersedes_baseline_id`, `active_from`, `acknowledged_warnings`, `source_note`).
2. **Supersede:** activate a second baseline; confirm the prior goes `superseded`
   with `active_to == new.active_from`, and the activation event records the
   supersession.
3. **Blocked — hard invalid:** attempt to activate a `hard_invalid` baseline;
   confirm structured 409 (unchanged), baseline untouched, **and** a
   `baseline_activation_blocked` row with `is_success=false, reason=hard_invalid`.
4. **Blocked — warnings:** attempt with warnings but no ack / no note; confirm
   `warnings_require_ack` / `source_note_required` 409 and matching blocked event;
   then ack + note and confirm success event includes the note.
5. **Attribution surfacing (if Tier 2):** confirm `ExpectedBaselineResponse`
   returns `activated_by`/`activated_at` and the history panel renders them.
6. **Period-effective regression:** confirm the expected vs actual preview and the
   period-effective read path are byte-identical before/after B3 (no math/selection
   change).
7. **Site 4 read-only check:** re-run the §11 query and confirm #3/#4 rows
   (status, windows, thermal coefficients) are unchanged.

---

## 16. Open Product Decisions

1. **Audit source value:** reuse `source="telemetry"` (consistent with existing
   telemetry events) vs introduce `source="telemetry_baseline"` for cleaner
   filtering. *Recommendation: `telemetry_baseline`.*
2. **`details` shape:** keep JSON-encoded string in the existing VARCHAR `details`
   (no migration) vs add a structured `jsonb` details column (migration) for
   queryable event payloads. *Recommendation: start with the string; revisit if
   structured querying is needed.*
3. **Supersession event:** dedicated `baseline_superseded` event vs folding the
   supersedes info into `baseline_activated`. *Recommendation: fold in, to avoid
   double-counting one user action.*
4. **Tier 2 columns:** promote `activated_by`/`activated_at` now (migration) vs
   defer and serialize from existing JSON. *Recommendation: promote — it removes
   the JSON-parsing dependency and matches the `approved_*` pattern.*
5. **Historical backfill:** populate new attribution columns from existing
   `validation_result_json["activation"]`? Must be **attribution-only**, never
   touching windows/status, and **must skip Site 4 mutations** (read-only). Requires
   explicit approval.
6. **Audit-read endpoint:** add a read-only endpoint to list baseline lifecycle
   events for the FE, or defer. *Recommendation: defer to Tier 3.*
7. **User-chosen effective date / backdating:** explicitly **out of scope** here;
   raise separately if the business needs auditable backdated activations.
8. **Create-draft auditing:** audit `baseline_created` too, or only
   approve/activate? *Recommendation: include create for a complete trail; it is
   cheap and best-effort.*

---

## Required Deliverable Summary (return items)

### Audit findings
- Approve ≠ activate is correctly enforced (separate endpoints/methods/transitions).
- Activation does not rewrite history; replacement `active_from = now`, prior
  `active_to = now`, half-open windows abut cleanly (validated on Site 4).
- **No `audit_logs` events exist for any baseline lifecycle action; blocked
  activations are not durably recorded; activator/waiver attribution is JSON-only
  and unserialized.**

### Recommended implementation plan
Tier 1 best-effort `audit_logs` events for create/approve/activate/blocked (no
migration) → Tier 2 optional first-class `activated_by`/`activated_at` columns +
additive response serialization (one migration) → Tier 3 additive FE surfacing.
All additive, fail-closed-preserving, Site-4-read-only.

### Affected files (for the *future* B3 implementation — none changed now)
- `backend/ilios-server/app/routers/telemetry/v2.py` (emit events in
  approve/activate handlers + blocked branches).
- `backend/ilios-server/app/helpers/telemetry/audit.py` (reuse; optional
  `source`/structured-detail extension).
- *(Tier 2)* `backend/ilios-server/app/crud/telemetry_expected.py` (populate new
  columns in `activate`), `app/models/telemetry_expected.py` (two nullable
  columns), `app/schemas/...ExpectedBaselineResponse` (additive optional fields),
  new Alembic migration.
- *(Tier 3)* `.../Reconciliation/components/ValidationHistoryPanel.tsx`,
  `frontend/.../api/telemetryV2.ts`, related types.

### Affected routes
- `POST /api/telemetry/v2/expected-baselines/{id}/approve`
- `POST /api/telemetry/v2/expected-baselines/{id}/activate`
- *(optional)* create-draft endpoint; *(optional, Tier 3)* a read-only
  baseline-events endpoint.

### Affected data models
- Tier 1: `audit_logs` (writes only; no schema change).
- Tier 2: `telemetry_expected_baselines` (+ `activated_by` FK, `activated_at`
  timestamp — nullable, additive).

### Migration impact
- Tier 1: **none.**
- Tier 2: **one** forward-only Alembic migration adding two nullable columns + FK;
  no backfill required (legacy/Site-4 rows read null); any optional backfill is
  attribution-only and must not mutate Site 4.

### Test plan
- Backend: extend `test_baseline_lifecycle_endpoints.py` to assert an `audit_logs`
  row is written on approve/activate (correct action/user/payload) and on blocked
  activation (`is_success=false`, reason); assert audit-write failure does **not**
  break activation (monkeypatch helper to raise). Tier 2: assert response includes
  `activated_by`/`activated_at`. Re-run `period_effective_baseline_test.py` to prove
  selection is unchanged.
- Frontend: extend `ValidationHistoryPanel.test.tsx` to render activator/waiver
  (Tier 2); confirm existing `DraftBaselineReviewPanel.test.tsx` stays green.

### Browser-validation plan
Per §15 (happy path, supersede, hard-invalid block, warning block + ack,
attribution surfacing, period-effective regression, Site-4 read-only check).

### Confirmation — no production code changed
This sprint produced **only** this document
(`docs/baseline_activation_effective_date_audit_events_audit.md`). No backend or
frontend source, schema, migration, route, authorization, math, weather, or device
code was modified, and **no Site 4 data was approved, activated, superseded, or
otherwise mutated** (Site 4 was inspected read-only only).
