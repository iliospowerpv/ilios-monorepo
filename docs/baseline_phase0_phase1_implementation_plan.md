# Baseline Lifecycle Authorization Hardening (Phase 0) + Draft Preview (Phase 1) — Implementation Plan

**Status:** PLAN ONLY — no production code written. Return for review; implementation begins only after approval.
**Date:** 2026-06-25
**Approved decisions baked in:** D1, D2, D3, D4 (see §0.2).
**Supersedes a claim in:** `docs/baseline_review_approval_activation_and_staleness_ux_audit.md` §0.3 / §D (see §0.1).

### Required-return checklist (maps to your 13 items)
1. Affected backend files & routes → **§2, §9**
2. Affected frontend files/components → **§5, §9**
3. Authorization helper design → **§3**
4. Structured 403 response contract → **§4**
5. Capability-flag response schema → **§5.1**
6. Draft-preview API contract → **§6**
7. Migration impact confirmation → **§7**
8. Full permission matrix → **§1, §8b**
9. Mutation boundaries → **§10**
10. Backend test plan → **§8b, §8c**
11. Frontend test plan → **§8d**
12. Browser-validation plan incl. Site 4 / 110 Shawmut → **§8a**
13. Confirmation math/expected/active/historical unchanged → **§11**

---

## 0.1 Audit correction (why Phase 0 is reframed)

The accepted audit reported a "live permission defect": that the backend required **company-admin** for `approve`/`activate` while the FE only checked telemetry-admin (→ 403 mismatch). **That was inferred from a function _name_, not its body.** Verified:

- `get_authorized_site_with_company_admin` (`app/helpers/authorization/project_access.py:216`) is a **misnamed alias** of `get_authorized_site` — resolver **site visibility** only; its docstring says the legacy company-admin fallback was **deprecated**.
- The real gate today for create/draft/approve/activate/diff is `telemetry_admin_required` (`app/helpers/authorization/module_based/telemetry.py:57`) = platform-bypass **OR** `Telemetry.admin` **OR** `Settings Page.edit`. The FE `useTelemetryAdminPermission` already mirrors it.

So there is **no 403 defect** today. Phase 0 is therefore a deliberate **governance strengthening**: make telemetry-admin **AND** company-admin a real requirement for lifecycle mutations, enforced backend-first.

## 0.2 Approved decisions

- **D1 — Reads:** Tighten **`list`/history** to telemetry-admin only. **Keep `active` and public `expected-preview` open** to authorized site viewers (caller audit may justify tightening later). *Audit result: the only consumers of `list`/`active` are the two governance panels in the Reconciliation tab (§5.3); no O&M chart, dashboard, or company/portfolio aggregation path uses them, so tightening `list` is safe once the FE gates the list query on telemetry-admin.*
- **D2 — Capability flags:** Add server-computed `viewer_can_author_draft` + `viewer_can_manage_lifecycle` to the baseline **list** and **active** responses (§5.1).
- **D3 — Structured 403:** Use a **registered exception handler** for lifecycle 403s (§4).
- **D4 — Draft preview:** Preview baselines with status **`draft` or `approved` only** (§6).

---

## 1. Target permission model

Every tier also requires **normal site access** (resolver visibility). Platform-bypass (system / global admin) satisfies all tiers.

| Tier | Actions | Required authority |
|---|---|---|
| **Read-only** | list/history; view active; view validation; source-basis lineage; compare/diff; read-only draft preview | telemetry-admin **+** site access |
| **Draft-authoring** | create draft from facts; edit draft inputs (where supported); generate design points | telemetry-admin **+** site access |
| **Governance / lifecycle** | approve; activate; supersede-via-replacement-activation; acknowledge activation warnings | telemetry-admin **AND** company-admin (baseline's company) **+** site access |

`company-admin` = `crud.is_company_admin(user_id, company_id)` (`app/crud/user_company_access.py:101`) = active `user_company_access` membership with `role == company_admin` for the **baseline's** `company_id`.
*Out of scope per directive:* reject, retire/deactivate, staleness, separation-of-duties — not implemented here (when reject/retire are later added they must use the lifecycle gate).

---

## 2. Affected backend routes (current → target) — all in `app/routers/telemetry/v2.py`

### 2a. Governance / lifecycle mutations — **CHANGE: add company-admin gate**

| Route | Line | Current | Target |
|---|---|---|---|
| `POST /v2/expected-baselines/{baseline_id}/approve` | 3763 | `telemetry_admin_required` + alias + `_enforce_company_visibility` | `telemetry_admin_required` + **`enforce_baseline_lifecycle_authority(action="approve")`** |
| `POST /v2/expected-baselines/{baseline_id}/activate` | 3797 | same (covers supersede + `acknowledge_warnings`) | same gate, `action="activate"` |

No reject/retire/deactivate routes exist (verified: next route after `activate` is the GET preview at 3858). The acknowledge-warnings path is the `acknowledge_warnings=true` branch *inside* `activate`, so it inherits the gate.

### 2b. Draft-authoring — **NO AUTH CHANGE** (stay telemetry-admin + site access)
`create-draft-from-facts` (3240), `generate-design-points` (3645), `readiness-from-facts` (3205), `points-readiness` (3618), deprecated snapshot create (3094). (They resolve the site via the alias = site visibility; correct for this tier. No change required.)

### 2c. Reads

| Route | Line | Current | Target (D1) |
|---|---|---|---|
| `GET /v2/expected-baselines/{baseline_id}/diff` | 3502 | `telemetry_admin_required` + alias | unchanged ✅ |
| `GET /v2/sites/{site_id}/expected-baselines` (list/history) | 3062 | `get_authorized_site` only | **ADD `telemetry_admin_required`** + capability flags on envelope |
| `GET /v2/sites/{site_id}/expected-baselines/active` | 3079 | `get_authorized_site` only | **keep site-access**; wrap in envelope + capability flags |
| `GET /v2/sites/{site_id}/expected-preview` (O&M feed) | 3858 | `get_authorized_site` only | **unchanged** (public; refuses non-`{approved,active,superseded}` → never exposes drafts) |

### 2d. New endpoint (Phase 1)
`GET /v2/sites/{site_id}/expected-baseline/{baseline_id}/draft-preview` — `telemetry_admin_required` + `get_authorized_site` (read tier). See §6.

---

## 3. Authorization helper design

**New, baseline-only helpers** in `app/helpers/authorization/module_based/telemetry.py` (beside `telemetry_admin_required`). We **do not** modify the shared `get_authorized_site_with_company_admin` alias — `app/routers/weather.py` reuses it in 10 places and changing its body would silently re-gate weather (out of scope).

1. `class BaselineLifecycleForbiddenError(Exception)` — fields: `action_code` (`approve`/`activate`), `reason_code` (`company_admin_required` | `telemetry_admin_required`), `company_id`, `message`.
2. `enforce_baseline_lifecycle_authority(db, current_user, *, company_id, site_id, action_code) -> None` (throwing):
   - resolve site access for `site_id` (fail-closed on no visibility);
   - require telemetry-admin via existing non-throwing `user_has_telemetry_admin(current_user)` (`telemetry.py:60`);
   - require `current_user.has_platform_bypass OR crud.is_company_admin(current_user.id, company_id)`;
   - else raise `BaselineLifecycleForbiddenError(...)`.
3. `can_author_draft(db, current_user, *, company_id, site_id) -> bool` and `can_manage_baseline_lifecycle(db, current_user, *, company_id, site_id) -> bool` (non-throwing) — drive the capability flags (§5.1) using the same predicates, guaranteeing FE/BE parity.

**Handler edit (approve, activate):** replace the current `get_authorized_site_with_company_admin(baseline.site_id, ...) + _enforce_company_visibility(...)` with one `enforce_baseline_lifecycle_authority(db, current_user, company_id=baseline.company_id, site_id=baseline.site_id, action_code=...)`. The route-level `Depends(telemetry_admin_required)` stays (telemetry-admin still 403s first via the dependency for non-telemetry-admins). Physics gate, supersede, acknowledge flow, and the 404-on-missing-baseline checks are untouched.

---

## 4. Structured 403 response contract (D3 — registered handler)

`http_exception_handler` flattens `HTTPException.detail` to a string, so we register a dedicated handler in `app/main.py`:
`app.add_exception_handler(BaselineLifecycleForbiddenError, baseline_lifecycle_forbidden_handler)` (handler fn in `app/utils.py`, returning `JSONResponse(status_code=403, content=<body>)`). Future reject/retire get structured 403s for free.

```json
{
  "error": "baseline_approve_forbidden",        // baseline_<action>_forbidden
  "action": "approve",                            // approve | activate
  "reason": "company_admin_required",             // company_admin_required | telemetry_admin_required
  "message": "Approving this baseline requires Telemetry admin AND Company admin for this company.",
  "required_roles": ["telemetry_admin", "company_admin"]
}
```
CORS: 403 is a normal response; no expose-headers change. The body is read from the JSON payload, not a header.

---

## 5. Frontend gates

**Core constraint:** the FE `user` object has `is_system_user`/`is_global_admin`/`parent_company_id`/global `role.permissions` — **no per-company `company_admin` membership**. So the FE must **not** re-derive company-admin (`useAccess.isCompanyAdminFull` = `Settings Page.view`, which is the wrong signal). FE gates lifecycle UI **only** off the backend flags (D2).

### 5.1 Capability-flag response schema (item 5)
Both flags are **viewer-scoped** (about the requesting user), additive, non-null.

- `ExpectedBaselineListResponse` (`app/schema/telemetry_v2.py:891`, currently `{site_id, baselines[]}`) → add:
  - `viewer_can_author_draft: bool`
  - `viewer_can_manage_lifecycle: bool`
- `/active` currently returns `ExpectedBaselineResponse | None` (no place to hang flags when null). Introduce a thin envelope **`ActiveExpectedBaselineResponse`**:
  ```
  ActiveExpectedBaselineResponse {
    site_id: int
    baseline: ExpectedBaselineResponse | None
    viewer_can_author_draft: bool
    viewer_can_manage_lifecycle: bool
  }
  ```
  Because `/active` stays **open** (site-access), every site viewer can read these flags even after `list` is tightened — so the FE sources `viewer_can_manage_lifecycle` from the **active** response (always reachable). The flags are computed identically on both responses via the §3 non-throwing predicates.

### 5.2 FE permission matrix

| UI action | Component | Gating signal (target) |
|---|---|---|
| Create draft from facts | `BaselineFromFactsPanel.tsx` | `useTelemetryAdminPermission()` (**unchanged**) |
| Generate design points | review panel | `useTelemetryAdminPermission()` (unchanged) |
| Compare / diff | `DraftBaselineReviewPanel.tsx` | `useTelemetryAdminPermission()` (unchanged) |
| Read-only draft preview (Phase 1) | review panel | `useTelemetryAdminPermission()` |
| **Approve** | `DraftBaselineReviewPanel.tsx` | **`viewer_can_manage_lifecycle`** (backend flag) |
| **Activate** | `DraftBaselineReviewPanel.tsx` | **`viewer_can_manage_lifecycle`** |
| **Acknowledge warnings** | `DraftBaselineReviewPanel.tsx` | **`viewer_can_manage_lifecycle`** |

When `viewer_can_manage_lifecycle` is false, render a **read-only explanation** (not a disabled-then-403 button): *"You can review this baseline. Approving or activating requires Telemetry admin **and** Company admin for {company}."*

### 5.3 Affected FE files/components (item 2)
- `src/api/telemetryV2.ts` — list/active types gain the two flags + `ActiveExpectedBaselineResponse`; add `getDraftBaselinePreview`.
- `src/types/telemetryV2.ts` — flag fields, `ActiveExpectedBaselineResponse`, `DraftExpectedPreviewResponse`.
- `DraftBaselineReviewPanel.tsx` — bind approve/activate/ack to `viewer_can_manage_lifecycle` (from active response); add draft-vs-active overlay (§6); **gate the list query** (`enabled: isTelemetryAdmin`) so non-admins don't fire the now-tightened `list` (clean read-only state instead of a 403 toast).
- `BaselineFromFactsPanel.tsx` — **gate its list query** on telemetry-admin too (D1); create still gated by `canDraft`. No lifecycle change.
- `Reconciliation.tsx` — thread `canManageLifecycle` (from loaded active response) into the review panel alongside existing `canDraftBaseline`.

---

## 6. Draft-preview API contract (Phase 1, item 6)

`GET /v2/sites/{site_id}/expected-baseline/{baseline_id}/draft-preview`
- **Auth:** `Depends(telemetry_admin_required)` + `get_authorized_site` (read tier; **no** company-admin).
- **Params:** optional `start`, `end`, `bucket_size` — same clamping as `expected-preview` (default last 24h, 24h max, `bucket_size ∈ _PREVIEW_BUCKET_SIZES`).
- **Baseline gate (D4):** load baseline; 404 if missing or `site_id` mismatch; **409 if status ∉ {draft, approved}** (mirrors the public preview's status guard, inverted for the admin surface).
- **Compute:** `expected_service.compute_site_expected(db, site=site, baseline=<that baseline>, start, end, bucket_size, weather_resolver=default)` — specific baseline, **no** active-resolution, **no** stitching. `validate_baseline` on read → honest suppression (NULL expected on invalid/missing-inputs; never fabricated 0). **Zero DB writes.**
- **Response — `DraftExpectedPreviewResponse`** (superset of `ExpectedPreviewResponse`, additive):
  - all `ExpectedPreviewResponse` fields (buckets, energies, counts, weather provenance, …)
  - `is_draft_preview: bool = true`
  - `baseline_status: str` (`draft`|`approved`)
  - `validation_summary` (validate-on-read verdict so the panel can show "draft invalid: …")
  - `disclaimer: str = "Draft preview — not approved or active. Not used for operations."`

**FE overlay:** new `getDraftBaselinePreview(siteId, baselineId, {start,end,bucket_size})`; reuse `getBaselineDiff(draftId, activeId)` (exists) for field diff; fetch the **active** series via existing `expected-preview` (no `baseline_id`) over the same window. Render active = solid "Current active", draft = dashed "Draft (not active)", with the disclaimer banner, honest gaps where the draft is invalid/missing-inputs, and a note that the draft would take over **at activation** (effective-date policy is preserve-only, not implemented here).

---

## 7. Migration impact confirmation (item 7)

**None.** Pure role-based authorization + additive response fields (Pydantic only). No new tables/columns/enums, no Alembic revision. `is_company_admin` and the `user_company_access` rows it reads already exist. The capability flags and draft-preview compute read existing data only.

---

## 8. Validation & test plans

### 8a. Browser validation incl. Site 4 / 110 Shawmut (item 12)
Workflows: **Backend** (uvicorn :8000), **Frontend** (:5000); drive via `$REPLIT_DEV_DOMAIN`. **Site 4 = 110 Shawmut** is a protected site whose current active baseline (#4, corrected thermal −0.35) and superseded invalid #3 (thermal=350) must remain byte-identical throughout.

1. **System user (bypass):** Site 4 → Reconciliation → baseline review. Confirm list/active/diff load; create a draft (a NEW draft, not touching #3/#4); open **draft-preview overlay** vs active; approve then activate the **new draft only**. (If you prefer not to change Site 4's active during validation, use a throwaway test site for the approve/activate happy-path and use Site 4 only for the read/forbidden/isolation checks.)
2. **Telemetry-admin without company-admin** (seed role + non-admin membership on Site 4's company): approve/activate show the **read-only explanation** (no enabled button); create-draft still available; draft-preview visible. Direct `POST .../approve` and `.../activate` return **structured 403** (`action`, `reason=company_admin_required`) — verify in Network panel.
3. **Diligence.view but not telemetry-admin:** Reconciliation opens; baseline panels show the telemetry-admin read-only state (list query not fired); no 403 toast.
4. **Normal site viewer:** O&M expected chart for Site 4 still renders the **active** (−0.35) curve; governance panel read-only/absent.
5. **Isolation (Site 4):** the new draft appears **only** in the admin draft-preview overlay; the public `expected-preview` for Site 4 still returns the active series and **409s** if asked for the draft `baseline_id`; the invalid #3 still suppresses (no corrupt curve).
6. **No-side-effect (Site 4):** after every forbidden approve/activate attempt, re-read `list` → #3/#4 status, points, and validation JSON unchanged.
Use `screenshot` (app_preview) for panel states; `refresh_all_logs` + Network for 403 bodies.

### 8b. Backend authorization regression matrix (item 8/10)
Harness (memory): needs `test_db_name` + own DB; override coverage `addopts`; no `pytest-mock` (use `monkeypatch`); `PermissionType` is a plain `str`; seed `user_company_access` memberships.

| Actor | reads: diff / **list** / active / draft-preview | draft-author | lifecycle (approve/activate) |
|---|---|---|---|
| system user (bypass) | ✅ / ✅ / ✅ / ✅ | ✅ | ✅ |
| telemetry-admin **+** company-admin (target company) | ✅ / ✅ / ✅ / ✅ | ✅ | ✅ |
| telemetry-admin, **not** company-admin | ✅ / ✅ / ✅ / ✅ | ✅ | **403 `company_admin_required`** |
| telemetry-admin via legacy `Settings Page.edit`, not company-admin | ✅ / ✅ / ✅ / ✅ | ✅ | **403 `company_admin_required`** |
| company-admin **not** telemetry-admin | diff **403** / list **403** / active ✅ / draft-preview **403** | **403 `telemetry_admin_required`** | **403 `telemetry_admin_required`** |
| site viewer (no telemetry-admin) | diff **403** / list **403** / active ✅ / draft-preview **403** | **403** | **403** |
| telemetry-admin + company-admin of company A, on company B baseline | per visibility | per visibility | **403** (checked against baseline's company) |
| no site access (foreign company) | 403/404 on resolve | 403/404 | 403/404 |

Plus **no-side-effect** assertions (see §10).

### 8c. Backend Phase-1 + behavior tests (item 10)
- draft-preview computes for `draft` and `approved`; **409** for `active`/`superseded`/`retired`; **404** cross-site baseline; **zero-writes** assertion (DB row counts + active baseline unchanged after preview); invalid draft → suppressed (NULL) expected.
- **Isolation:** public `expected-preview` still 409s on a `draft` `baseline_id`.
- Existing lifecycle happy-path tests (system / company-admin) still pass.

### 8d. Frontend test plan (item 11)
FE jest (needs libuuid; trust fork-ts-checker):
- `DraftBaselineReviewPanel`: `viewer_can_manage_lifecycle=true` → approve/activate enabled; `false` → disabled + read-only explanation; list query disabled when not telemetry-admin.
- `BaselineFromFactsPanel`: `canDraft` gating; list query disabled when not telemetry-admin.
- `Reconciliation`: threads `canManageLifecycle` from the active response.
- Draft-preview overlay: renders active+draft series; shows disclaimer; honest gaps. Mock `useAuth` + the active/list queries returning capability flags.

---

## 9. Precise change list (items 1 & 2)

**Backend (`backend/ilios-server`)**
- `app/helpers/authorization/module_based/telemetry.py` — `BaselineLifecycleForbiddenError`, `enforce_baseline_lifecycle_authority`, `can_author_draft`, `can_manage_baseline_lifecycle`.
- `app/routers/telemetry/v2.py` — gate `approve` (3763) + `activate` (3797); add `telemetry_admin_required` to `list` (3062); wrap `/active` (3079) in `ActiveExpectedBaselineResponse` + flags; add flags to list envelope; add `draft-preview` endpoint.
- `app/utils.py` + `app/main.py` — `baseline_lifecycle_forbidden_handler` + register it.
- `app/schema/telemetry_v2.py` — flags on `ExpectedBaselineListResponse`; new `ActiveExpectedBaselineResponse`; new `DraftExpectedPreviewResponse`.
- **No Alembic migration.**

**Frontend (`frontend/rea-investment-fe`)**
- `src/api/telemetryV2.ts`, `src/types/telemetryV2.ts` — flags, `ActiveExpectedBaselineResponse`, `getDraftBaselinePreview`, `DraftExpectedPreviewResponse`.
- `DraftBaselineReviewPanel.tsx` (lifecycle gate + read-only explanation + overlay + list-query gating), `BaselineFromFactsPanel.tsx` (list-query gating), `Reconciliation.tsx` (thread `canManageLifecycle`).

**Out of scope / flagged:** weather.py alias reuse (separate follow-up); renaming the misleading alias (deferred); reject/retire/staleness/SoD/WS.5/device-mapping/weather-declaration — all excluded per directive.

---

## 10. Mutation boundaries (item 9)

- **Writes occur ONLY in:** `approve` (status draft/in-review → approved, stamps reviewer/approver) and `activate` (approved → active, supersede prior active, stamp activation identity in `validation_result_json`). Unchanged from today except the added pre-check.
- **A forbidden approve/activate (403) writes NOTHING:** the authority check runs **before** any `crud.approve`/`crud.activate` call, so on 403 there is no change to baseline status, the active baseline, `validation_result_json`, design points, expected output, or historical ownership/period-effective windows.
- **Draft-preview writes NOTHING** (read-only compute; no `db.add/flush/commit`).
- **Capability-flag computation writes NOTHING** (read-only predicates).
- **`list` tightening** changes only *who may read*; it performs no writes.
- **Acknowledge-warnings** remains the only waiver path and only for warning-level (never `hard_invalid`); it still requires a non-empty `activation_source_note` and is now additionally gated by company-admin.

---

## 11. Unchanged-behavior confirmation (item 13)

This work changes **authorization, response envelopes, and a new read-only endpoint** only. It does **not** change:
- **Baseline math / physics formulas** — `expected_service` compute path and `BaselineParams` mapping are untouched.
- **Expected output for operations** — O&M charts/health/readiness/aggregation continue to read the public `expected-preview` / active resolution unchanged; draft preview is isolated (§6/§8c) and never feeds them.
- **Active baseline state** — no endpoint here mutates an existing active baseline; activation behavior (supersede, validate-on-activate, fail-closed physics gate) is byte-for-byte the same, only with an added pre-authorization check.
- **Period-effective selection / historical expected ownership** — `get_baselines_effective_in_window` and stitching are not touched; no backdating, no historical rewrite.
- **Protected Site 4 / 110 Shawmut** — #3 (superseded, invalid) and #4 (active, −0.35) remain unchanged; validation re-confirms before/after (§8a step 6).
