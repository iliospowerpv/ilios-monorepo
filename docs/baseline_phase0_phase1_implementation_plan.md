# Baseline Lifecycle Authorization Hardening (Phase 0) + Draft Preview (Phase 1) — Implementation Plan

**Status:** PLAN ONLY — no production code written. Return for review before implementation.
**Date:** 2026-06-25
**Supersedes a claim in:** `docs/baseline_review_approval_activation_and_staleness_ux_audit.md` (§0.3 / §D — see Correction below).
**Scope guardrails:** Do not change baseline math, period-effective selection, expected output, or any existing approved/active baseline state. Do not change the backend `Site` entity. Separation-of-duties (approver ≠ activator) is explicitly **deferred** to a separate product-policy decision; this work is **role-based authorization only**.

---

## 0. Audit correction (why Phase 0 is reframed)

The accepted audit reported a "live permission defect": that the backend required **company-admin** for `approve`/`activate` while the frontend only checked telemetry-admin, so a telemetry-admin-without-company-admin user would pass the FE gate and then hit a 403.

**That was inferred from a function _name_, not its body.** Verified facts:

- `get_authorized_site_with_company_admin` (`app/helpers/authorization/project_access.py:216`) is a **misnamed alias** — its body is identical to `get_authorized_site` (resolver-based **site visibility** only). Its own docstring states the legacy company-admin fallback was **deprecated**.
- The real backend gate today for create/draft/approve/activate/diff is `telemetry_admin_required` (`app/helpers/authorization/module_based/telemetry.py:57`) = platform-bypass **OR** `Telemetry.admin` **OR** `Settings Page.edit`.
- The FE `useTelemetryAdminPermission` already mirrors that gate exactly.

**Conclusion:** there is **no** company-admin enforcement today, hence **no 403 defect** to "align." Per the approved direction (Option B), Phase 0 is therefore reframed from a *defect fix* into a deliberate **governance control**: make telemetry-admin **AND** company-admin a *real* requirement for lifecycle mutations, enforced backend-first and mirrored on the FE. This is a backend **strengthening**, not a weakening.

---

## 1. Target permission model (the spec)

Three authority tiers. The actor for every tier already needs **normal site access** (resolver visibility) as a baseline.

| Tier | Actions | Required authority |
|---|---|---|
| **Read-only** | list baseline history; view active baseline; view validation; view source-basis lineage; compare/diff; **read-only draft preview** | telemetry-admin **+** site access |
| **Draft-authoring** | create draft from facts; edit draft inputs (where supported); generate draft design points | telemetry-admin **+** site access |
| **Governance / lifecycle** | approve; activate; supersede-via-replacement-activation; acknowledge activation warnings; *(future)* reject; *(future)* retire / deactivate-with-reason | telemetry-admin **AND** company-admin (for the baseline's company) **+** site access |

Platform-bypass (system user / global admin) satisfies all tiers.
"company-admin" = backend truth `crud.is_company_admin(user_id, company_id)` (`app/crud/user_company_access.py:101`) = an **active** `user_company_access` membership with `role == company_admin` for the baseline's `company_id`.

---

## 2. Phase 0 — exact affected routes (current → target)

All routes in `app/routers/telemetry/v2.py`. "alias" = `get_authorized_site_with_company_admin` (site-visibility only, despite the name).

### 2a. Governance / lifecycle mutations — **CHANGE: add company-admin gate**

| Route | Line | Current authority | Target authority |
|---|---|---|---|
| `POST /v2/expected-baselines/{baseline_id}/approve` | 3763 | `telemetry_admin_required` + inline alias + `_enforce_company_visibility` | `telemetry_admin_required` + **`enforce_baseline_lifecycle_authority(action="approve")`** (company-admin OR bypass) |
| `POST /v2/expected-baselines/{baseline_id}/activate` | 3797 | same (covers supersede + `acknowledge_warnings` payload) | same gate, `action="activate"` |

There are **no** reject/retire/deactivate endpoints today (verified: next route after `activate` at line 3858 is the GET preview). When added later they **must** use the same gate (`action="reject"` / `"retire"`).

> The acknowledge-warnings path is the `acknowledge_warnings=true` + non-empty `activation_source_note` branch *inside* `activate` — it is gated by the same endpoint, so it inherits the lifecycle gate automatically. No separate endpoint.

### 2b. Draft-authoring — **NO CHANGE** (already telemetry-admin + site access)

| Route | Line |
|---|---|
| `POST /v2/sites/{site_id}/expected-baseline/create-draft-from-facts` | 3240 |
| `POST /v2/sites/{site_id}/expected-baseline/{baseline_id}/generate-design-points` | 3645 |
| `GET  /v2/sites/{site_id}/expected-baseline/readiness-from-facts` | 3205 |
| `GET  /v2/sites/{site_id}/expected-baseline/{baseline_id}/points-readiness` | 3618 |
| `POST /v2/sites/{site_id}/expected-baselines` (DEPRECATED snapshot create) | 3094 |

These keep `telemetry_admin_required`. No company-admin. (They currently resolve the site via the misnamed alias; functionally that is just site visibility, which is correct for this tier. No behavior change needed; optional cosmetic swap to `get_authorized_site` for clarity — **not required**.)

### 2c. Reads — mostly unchanged; one decision point

| Route | Line | Current authority | Notes |
|---|---|---|---|
| `GET /v2/expected-baselines/{baseline_id}/diff` | 3502 | `telemetry_admin_required` + alias | ✅ already matches read tier |
| `GET /v2/sites/{site_id}/expected-baselines` (list/history) | 3062 | **`get_authorized_site` only** (no telemetry-admin) | ⚠️ looser than the model — **Decision D1** |
| `GET /v2/sites/{site_id}/expected-baselines/active` | 3079 | **`get_authorized_site` only** | ⚠️ looser than the model — **Decision D1** |
| `GET /v2/sites/{site_id}/expected-preview` (O&M chart feed) | 3858 | `get_authorized_site` only (intentional) | **Keep open.** This is the public expected-vs-actual feed for non-admin O&M viewers; tightening it would break their charts and contradicts the "honest expected for all viewers" design. NOT in the governance surface. |

**Decision D1 (list & active reads):** The model says reads require telemetry-admin. Today `list` and `active` are site-access-only. Recommended: tighten **`list`** (clearly a governance/history view) to `telemetry_admin_required`, and **leave `active` at site-access** unless a consumer audit shows it is only consumed by admin surfaces (it may feed read-only "current baseline" panels for non-admins). **Pre-step:** grep all callers of `getActiveExpectedBaseline` / the `/active` route before tightening. I will not tighten anything that a non-admin surface depends on. *Flagging for your call; default = tighten `list` only, keep `active` and `expected-preview` open.*

---

## 3. Phase 0 — backend authorization helper changes

**New, baseline-only helpers** (proposed home: `app/helpers/authorization/module_based/telemetry.py`, beside `telemetry_admin_required`). We deliberately **do not** modify the shared `get_authorized_site_with_company_admin` alias because it is also used by 10 endpoints in `app/routers/weather.py`; changing its body would silently re-gate weather governance (out of scope — see §9).

1. `class BaselineLifecycleForbiddenError(Exception)` — carries `action_code`, `reason_code` (`"company_admin_required"` | `"telemetry_admin_required"`), `company_id`, and a human message.
2. `enforce_baseline_lifecycle_authority(db, current_user, *, company_id, site_id, action_code) -> None` (throwing):
   - resolve site access (resolver) for `site_id` — fail-closed on no visibility;
   - require telemetry-admin via `user_has_telemetry_admin(current_user)` (non-throwing variant already exists at `telemetry.py:60`);
   - require `current_user.has_platform_bypass OR crud.is_company_admin(current_user.id, company_id)`;
   - on failure raise `BaselineLifecycleForbiddenError(action_code, reason, ...)`.
3. `can_manage_baseline_lifecycle(db, current_user, company_id) -> bool` (non-throwing) — used to compute FE capability flags (§5) without duplicating logic.

**Structured 403 rendering.** The global `http_exception_handler` flattens `HTTPException.detail` to a string, so a raw `HTTPException(403, {...})` would lose structure. Two consistent options:
- **Recommended:** register one handler in `app/main.py` — `app.add_exception_handler(BaselineLifecycleForbiddenError, baseline_lifecycle_forbidden_handler)` returning `JSONResponse(status_code=403, content=<body>)`. Future reject/retire get structured 403s for free.
- **Alternative (matches the existing physics-block pattern):** inline `try/except` in each handler returning `JSONResponse(403, body)` — this is exactly how `activate` already returns the 409 physics block (`_baseline_block_body`, line 3745+). Either is acceptable; the registered handler is DRY-er given multiple endpoints.

**Structured 403 body contract:**
```json
{
  "error": "baseline_<action>_forbidden",
  "action": "approve | activate | reject | retire",
  "reason": "company_admin_required | telemetry_admin_required",
  "message": "Approving an expected baseline requires Telemetry admin AND Company admin for this company.",
  "required_roles": ["telemetry_admin", "company_admin"]
}
```

**Edit in the two handlers:** replace the current `get_authorized_site_with_company_admin(baseline.site_id, ...) + _enforce_company_visibility(...)` lines with a single `enforce_baseline_lifecycle_authority(db, current_user, company_id=baseline.company_id, site_id=baseline.site_id, action_code=...)`. No other handler logic changes; the physics gate, supersede, and acknowledge flow are untouched.

---

## 4. Phase 0 — migration impact

**None.** Pure role-based authorization. No new tables, columns, enums, or Alembic revision. `is_company_admin` and the `user_company_access` rows it reads already exist. (Explicitly confirms the user's "expected none.")

---

## 5. Phase 0 — frontend gates + permission matrix + affected components

**Core constraint:** the FE `user` object carries `is_system_user`, `is_global_admin`, `parent_company_id`, and a single global `role.permissions` map — it does **NOT** carry per-company `company_admin` membership. So the FE cannot reliably re-derive `is_company_admin(company_id)`. (`useAccess.isCompanyAdminFull` is `Settings Page.view`, which is **not** the backend company-admin role — using it would drift.)

**Recommended design — server-computed capability flags (single source of truth):**
Backend adds two additive, nullable-safe booleans to the baseline read responses, computed with the non-throwing helpers:
- `viewer_can_author_draft` (telemetry-admin + site access)
- `viewer_can_manage_lifecycle` (telemetry-admin AND company-admin)

Placed on `ExpectedBaselineListResponse` and the `/active` response (the data the review panel already loads). The FE gates UI off these flags — guaranteed to match the backend, zero drift. *(Alternative if we prefer not to touch read schemas: a dedicated `GET /v2/sites/{site_id}/expected-baselines/permissions` probe returning the same two flags.)*

### FE permission matrix

| UI action | Component | Gating signal (target) |
|---|---|---|
| Create draft from facts | `BaselineFromFactsPanel.tsx` | `useTelemetryAdminPermission()` (**unchanged** — draft-authoring tier) |
| Generate design points | review panel | `useTelemetryAdminPermission()` (unchanged) |
| Compare / diff | `DraftBaselineReviewPanel.tsx` | `useTelemetryAdminPermission()` (unchanged — read tier) |
| **Approve** | `DraftBaselineReviewPanel.tsx` | **`viewer_can_manage_lifecycle`** (server flag) |
| **Activate** | `DraftBaselineReviewPanel.tsx` | **`viewer_can_manage_lifecycle`** (server flag) |
| **Acknowledge warnings** (activate sub-flow) | `DraftBaselineReviewPanel.tsx` | **`viewer_can_manage_lifecycle`** |
| Promote / task (DD) | `Reconciliation.tsx` | `Diligence.edit` (unchanged — separate concern) |

### Affected FE components

- `src/api/telemetryV2.ts` — add capability fields to `ExpectedBaselineListResponse`/`ExpectedBaselineResponse`; add `getDraftBaselinePreview` (Phase 1).
- `src/types/telemetryV2.ts` — add `viewer_can_author_draft` / `viewer_can_manage_lifecycle`; add draft-preview response type.
- `DraftBaselineReviewPanel.tsx` — bind approve/activate/ack to `viewer_can_manage_lifecycle`; when false, show a **read-only explanation** instead of a disabled-then-403 button: *"You can review this baseline. Approving or activating requires Telemetry admin **and** Company admin for {company}."*
- `BaselineFromFactsPanel.tsx` — unchanged (canDraft = telemetry-admin).
- `Reconciliation.tsx` — thread `canManageLifecycle` (from the loaded baseline data) into the review panel alongside the existing `canDraftBaseline`.
- *(Optional)* `src/hooks/useBaselineLifecycleAuthority.ts` — thin helper that reads the server flag from loaded baseline data (keeps components clean). Not strictly required.

**UX principle (per spec):** users lacking lifecycle authority still see baseline, validation, preview, diff, and history — never an action that fails later.

---

## 6. Phase 1 — draft-preview API / data-contract design

**New endpoint:** `GET /v2/sites/{site_id}/expected-baseline/{baseline_id}/draft-preview`
- **Auth:** `Depends(telemetry_admin_required)` + `get_authorized_site` (site access). **Read tier → no company-admin.**
- **Params:** optional `start`, `end`, `bucket_size` (same clamping as `expected-preview`: default last 24h, 24h max, `_PREVIEW_BUCKET_SIZES`).
- **Behavior:** load baseline (must belong to `site_id`, else 404). Allow `status ∈ {draft, approved}` (the statuses the public preview refuses). Call `expected_service.compute_site_expected(db, site=site, baseline=<that baseline>, start, end, bucket_size, weather_resolver=default)` — uses the **specific** baseline, no active-resolution, no stitching. Run `validate_baseline` on read so an invalid/blocked draft suppresses expected honestly (NULL, never fabricated zeros). **Zero DB writes.**
- **Response:** reuse `ExpectedPreviewResponse` as a base, add additive fields → `DraftExpectedPreviewResponse`:
  - `is_draft_preview: bool = True`
  - `baseline_status: str`
  - `validation_summary` (the validate-on-read verdict, so the panel can show "draft invalid: …")
  - `disclaimer: str = "Draft preview — not approved or active. Not used for operations."`

**FE additions:**
- `getDraftBaselinePreview(siteId, baselineId, { start, end, bucket_size })` in `telemetryV2.ts`.
- Reuse existing `getBaselineDiff(draftId, activeId)` for the field-level diff (already implemented; `/v2/expected-baselines/{id}/diff`).
- Fetch the **active** series via the existing `expected-preview` (no `baseline_id`) over the same window for overlay.
- New overlay UI in the review panel: active = solid "Current active"; draft = dashed "Draft (not active)"; disclaimer banner; honest gaps where the draft is invalid/missing-inputs; an effective-date note that the draft would take over **at activation** (Phase 3 effective-date policy is preserve-only here).

---

## 7. Phase 1 — draft-preview isolation guarantees

1. **Separate, telemetry-admin-gated endpoint** → drafts are unreachable by O&M / public viewers.
2. **Public `expected-preview` still refuses non-`{approved,active,superseded}`** (409 via `_PREVIEWABLE_BASELINE_STATUSES`) → a draft can **never** appear in O&M charts, health, readiness, or company/portfolio aggregation.
3. **Zero writes** → preview never changes status, never activates, never affects period-effective selection or any active/approved state.
4. **Specific-baseline compute** (no active-resolution, no stitching) → the draft curve cannot leak into the period-effective active series.
5. **Explicitly flagged** (`is_draft_preview`, `disclaimer`, `baseline_status`) so the UI cannot accidentally present a draft as operational truth.

---

## 8. Validation plans

### 8a. Browser validation (manual, after implementation)
Workflows: **Backend** (uvicorn :8000), **Frontend** (:5000); drive via `$REPLIT_DEV_DOMAIN`.
1. **System user (bypass):** site → Reconciliation → baseline review; create draft → see draft-preview overlay vs active → approve → activate. All succeed.
2. **Telemetry-admin without company-admin** (seed role/membership): approve/activate render **read-only explanation** (no enabled button); create-draft still works; draft-preview visible; calling `approve`/`activate` directly returns **structured 403** with the right `action`/`reason` (verify in Network panel).
3. **Normal site viewer:** governance panel read-only; **O&M expected chart still renders** (public `expected-preview` unaffected).
4. **Isolation check:** confirm the draft series appears **only** in the admin draft-preview overlay, never in the O&M expected chart.
Use `screenshot` (app_preview) for panel states; `refresh_all_logs` + Network for the 403 body.

### 8b. Authorization regression-test matrix (backend pytest)
Harness notes (from memory): needs `test_db_name` + own DB, override coverage `addopts`, no `pytest-mock` (use `monkeypatch`), `PermissionType` is a plain `str`. `is_company_admin` reads `user_company_access` → tests must seed memberships.

| Actor | reads (list/diff/active/draft-preview) | draft-author (create/points) | lifecycle (approve/activate) |
|---|---|---|---|
| system user (bypass) | ✅ | ✅ | ✅ |
| telemetry-admin **+** company-admin (target company) | ✅ | ✅ | ✅ |
| telemetry-admin, **not** company-admin (lower role in same company) | ✅ | ✅ | **403** `reason=company_admin_required` |
| telemetry-admin via legacy `Settings Page.edit`, not company-admin | ✅ | ✅ | **403** `company_admin_required` |
| company-admin **but not** telemetry-admin | ✅ if read requires only site access; **403** where telemetry-admin required | **403** `telemetry_admin_required` | **403** `telemetry_admin_required` (route dep fires first) |
| normal site viewer (no telemetry-admin) | public `expected-preview` ✅; governance reads per Decision D1 | **403** | **403** |
| telemetry-admin + company-admin of **company A**, acting on **company B** baseline | per visibility | per visibility | **403** (company-admin checked against baseline's company) |
| no site access (foreign company) | 403/404 on resolve | 403/404 | 403/404 |

Plus **no-side-effect** assertions: a forbidden approve/activate leaves the draft and the existing active baseline **unchanged** (status, points, validation JSON).

### 8c. Phase 1 + FE regression tests
- **Backend:** draft-preview computes for a draft; 404 on cross-site baseline; **isolation** — public `expected-preview` still 409 on a draft; zero-writes assertion; invalid draft → suppressed (NULL) expected.
- **FE jest** (needs libuuid; trust fork-ts-checker): `DraftBaselineReviewPanel` — `viewer_can_manage_lifecycle=true` → approve/activate enabled; `false` → disabled + explanation; `BaselineFromFactsPanel` canDraft; `Reconciliation` wiring. Mock `useAuth` + baseline query returning capability flags.
- **Existing suites** (baseline lifecycle happy-path with system user / company-admin) must still pass; consumer audit confirms no non-admin read surface breaks (Decision D1).

---

## 9. Precise change list & out-of-scope notes

**Backend (`backend/ilios-server`)**
- `app/helpers/authorization/module_based/telemetry.py` — add `BaselineLifecycleForbiddenError`, `enforce_baseline_lifecycle_authority`, `can_manage_baseline_lifecycle`.
- `app/routers/telemetry/v2.py` — gate `approve` (3763) + `activate` (3797) with the new helper; add `draft-preview` endpoint; add capability flags to list/active responses; *(Decision D1)* optionally add `telemetry_admin_required` to `list` (3062).
- `app/main.py` — register `BaselineLifecycleForbiddenError` handler (or inline `JSONResponse` per the physics-block pattern).
- `app/schema/telemetry_v2.py` — capability fields on `ExpectedBaselineListResponse`/active; `DraftExpectedPreviewResponse`.
- **No Alembic migration.**

**Frontend (`frontend/rea-investment-fe`)**
- `src/api/telemetryV2.ts`, `src/types/telemetryV2.ts` — capability flags + `getDraftBaselinePreview` + draft-preview type.
- `DraftBaselineReviewPanel.tsx` (lifecycle gate + read-only explanation + draft-preview overlay), `Reconciliation.tsx` (thread `canManageLifecycle`), optional `useBaselineLifecycleAuthority.ts`.
- `BaselineFromFactsPanel.tsx` — unchanged.

**Out of scope / flagged**
- `app/routers/weather.py` (10 uses of the misnamed alias) — same name-only situation; weather declaration governance may merit the same company-admin gate, but that is a **separate follow-up**. We do **not** change the shared alias body (would silently re-gate weather).
- Renaming/removing the misleading `get_authorized_site_with_company_admin` alias — deferred (churn).
- **Separation-of-duties** (approver ≠ activator) — deferred to a separate product-policy decision, per direction.
- **Effective-date policy** (Phase 3) — preserve-only here.

---

## 10. Open decisions to confirm before I implement
- **D1:** Tighten `list` (and/or `active`) reads to telemetry-admin, or leave them at site-access to avoid O&M regressions? (Default: tighten `list` only; keep `active` + public `expected-preview` open, pending caller audit.)
- **D2:** Capability flags embedded in list/active responses (recommended, fewer round-trips) vs a dedicated `/permissions` probe endpoint?
- **D3:** Structured-403 via a registered exception handler (DRY) vs inline `JSONResponse` per handler (matches existing physics-block style)?
- **D4:** Draft-preview accepts `{draft, approved}` or `draft` only?
