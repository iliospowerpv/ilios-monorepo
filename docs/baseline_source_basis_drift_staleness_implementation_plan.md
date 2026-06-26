# Baseline Source-Basis Drift / Staleness — Implementation Plan (Phase B4)

**Status:** Implementation **plan only**. No production code, schema, or Site 4
data is changed by this document. Build begins only after this plan is reviewed
and approved.

**Companion:** builds directly on
`docs/baseline_source_basis_drift_staleness_audit.md` (the audit/findings). This
document is the concrete, build-ready refinement of audit §5–§12.

**Approved direction (governance — non-negotiable):**

- Source-basis drift is **needs-review / informational only**.
- **No** automatic deactivation, recalculation, lifecycle transition, or
  historical-expected rewrite. The active baseline stays active and immutable;
  the only remediation remains the existing manual "create + activate a new
  draft."
- **Correct the Site 4 false-positive** (active baseline #4 currently flags all
  four fact-backed fields as outdated even though values match).

The plan is phased so the **no-migration** core (D1–D3) delivers all approved
value; the optional acknowledgement ledger (D4) is explicitly **out of scope**
for this approval.

---

## 1. Affected files / routes / models

### Backend — new (read-only)

- **`app/services/telemetry/baseline_source_basis_drift.py`** (NEW) — a pure,
  read-only resolver. Given the active `weather_adjusted_model` baseline + the
  current active `project_facts`, returns a per-field and baseline-level
  value-based verdict. Zero writes, zero commits, zero promotion.

### Backend — edited (derive / additive only)

- **`app/services/due_diligence/reconciliation_service.py`**
  - Re-derive the existing `W_ACTIVE_OUTDATED` per-field warning (lines 817–828)
    from the new value-based resolver instead of the id-membership + timestamp
    heuristic (`_baseline_source_fact_ids` / `ctx.wam_active_fact_ids` /
    `ctx.wam_active_created`). The warning **constant and its meaning are
    unchanged**; only the detection becomes accurate.
  - Populate an additive `source_basis_drift` object on the readiness block via
    the resolver.
- **`app/schema/reconciliation.py`**
  - Add an additive, **nullable** `source_basis_drift` model to
    `ReconciliationReadiness` (and a small `SourceBasisDrift` /
    `SourceBasisDriftField` schema), declared with an **explicit default** —
    `source_basis_drift: Optional[SourceBasisDrift] = None`. (Under modern
    Pydantic, `Optional[...]` **without** a default is still required, which
    would break existing clients; the `= None` default keeps it back-compatible.)
    No existing field changes type or becomes required. `ReconciliationRow`,
    `SiteReconciliationResponse`, and `TelemetryReality` are untouched in shape.

### Backend — read-only inputs, **unchanged**

- `app/models/telemetry_expected.py` (`TelemetryExpectedBaseline`,
  `…BaselinePoint`) — read only; no column added in D1–D3.
- `app/models/project_facts.py` (`ProjectFact`) — read only.
- `app/crud/telemetry_expected.py` (lifecycle: approve/activate/supersede) —
  untouched.
- `app/services/telemetry/baseline_from_facts_service.py` — the resolver
  **reuses** its helpers (`_unwrap`, `_coerce_number`, `_signature`) and the
  normalization module (`baseline_input_normalization` →
  `input_norm.propose` / `input_norm.values_match` /
  `input_norm.is_normalizable_field`); the bridge itself is not modified.
- `app/services/promotion_service.py` (pre-promotion freshness guard) —
  untouched and unrelated.

### Routes

- **Unchanged contract:** `GET /api/due-diligence/sites/{site_id}/reconciliation`
  (router `reconciliation_router` `GET /reconciliation`; auth `Diligence:view`
  via `require_module_permission` + `get_authorized_site`). The `source_basis_drift`
  block rides on the existing response — no new required params, no breaking
  change.
- **Optional, deferred (not required for approval):** a dedicated read-only
  `GET /api/telemetry/v2/sites/{site_id}/baselines/{baseline_id}/source-basis-drift`
  under `app/routers/telemetry/v2.py`. If built, it must reuse the **same** guard
  as the reconciliation route — `Diligence:view` + `get_authorized_site` — **not**
  a broader asset-view scope, so it cannot widen access to diligence provenance.
  Zero writes. Only add if a baseline-card consumer outside reconciliation needs
  it.

### Frontend

- `src/api/reconciliation.ts` — extend the readiness type with the additive
  nullable `source_basis_drift` shape (mirrors the backend schema).
- `Reconciliation/components/ValidationHistoryPanel.tsx` — baseline-level drift
  badge on the active baseline.
- `Reconciliation/components/ReadinessSummary.tsx` — one-line baseline-level
  drift summary + the existing "Rebuild the active baseline…" action.
- `Reconciliation/components/StatusCell` + table `utils.ts` — no behavior
  change; per-field `active_baseline_outdated` now reflects the accurate
  value-based result automatically.

---

## 2. Exact drift comparison algorithm

The resolver is a pure function over two inputs:

- `baseline` = the single **active** `weather_adjusted_model`
  `TelemetryExpectedBaseline` (header + `model_parameters_json`). If none →
  empty, honest result (no drift, no 500).
- `active_facts` = `{canonical_name → ProjectFact}` for `status = active`.

### Step 0 — Baseline basis presence gate (fixes Site 4)

Build the recorded basis from `model_parameters_json`:

- `recorded_signature = model_parameters_json.get("source_fact_signature")`
- `recorded_field_sources = model_parameters_json.get("field_sources", {})`
- `recorded_source_facts = model_parameters_json.get("source_facts", [])`
- `recorded_basis_by_field` = `{column → recorded value}` assembled from
  `source_facts[]` (keyed by `column`) and `field_sources{}`.

Determine basis presence **per field** — **not** from the header FK:

- A field with **no** entry in `recorded_source_facts` / `recorded_field_sources`
  has **no recorded basis** → that field is **`basis_unknown`** (we cannot
  attribute its typed-column value to any fact lineage).
- The **baseline-level** state is `basis_unknown` **only when no field has any
  recorded basis** (`recorded_source_facts` empty **and**
  `recorded_signature is None`). Do **not** treat `source_project_fact_id` alone
  as a sufficient basis manifest — a header FK without
  `source_facts`/`field_sources` is still (partially) `basis_unknown`.
- For any `basis_unknown` field, **never** compute `drifted`. This is exactly
  Site 4 #4 (empty `source_facts`, NULL signature, NULL `source_project_fact_id`)
  → baseline-level `basis_unknown`.

> Rationale: the typed columns on a non-bridge baseline (e.g. #4's
> `module_wattage = 340`) exist, but there is **no recorded lineage** tying them
> to any fact, so we cannot honestly assert "the source changed." We report the
> basis as unrecorded rather than fabricate drift.

### Step 1 — Signature short-circuit (optional, best-effort, sufficient-only)

The bridge `source_fact_signature` is a SHA-256 over
`{baseline_type, facts:{canonical_name→value}, reviewer:{non-null reviewer
values}}`. It **can** confirm "nothing changed" cheaply, but it mixes in the
reviewer payload (and possible per-field normalization metadata) that is **not
fully reconstructable** from `model_parameters_json` after the fact, so a recompute
may legitimately fail to match even when nothing drifted. Therefore:

- Use the signature **only** as an optional short-circuit, and **only** when the
  recorded reviewer values are fully present in the snapshot: recompute
  `_signature(baseline_type, current_source_facts, recorded_reviewer_values)`; if
  it equals `recorded_signature` → treat the fact-backed fields as
  **`up_to_date`** and skip per-field diffing.
- **Signature inequality is never drift** and is never relied upon. If the
  reviewer payload cannot be exactly reconstructed, **skip this step entirely**.
- **Per-field value comparison (Step 2) is the SOLE authoritative mechanism.** The
  signature path is a performance nicety, never a correctness dependency.

### Step 2 — Per-field value comparison (authoritative)

For each fact-backed `HEADER_COLUMN` field in `BRIDGE_FACT_FIELDS`
(`module_wattage`, `module_quantity`, `inverter_wattage`, `inverter_quantity`)
**that has a recorded basis** (per Step 0):

1. **Recorded basis value** = the value recorded for that column in
   `recorded_source_facts` / `recorded_field_sources`; fall back to the immutable
   typed column on the baseline (e.g. `baseline.module_wattage`, cast to `float`)
   only when the snapshot records the field but omits an explicit value.
2. **Current fact value** = `_unwrap(active_facts[name].value)`. If there is no
   active fact for the field:
   - if the **recorded basis fact id** (the `fact_id` from this field's
     `source_facts` entry) now resolves to a **retired/superseded** fact and no
     active replacement exists → **`source_retired`** — keyed off the *recorded*
     fact id, **not** "any retired fact for this canonical name";
   - else → **`no_fact_lineage`**.
3. **Compare by value** (see §3 for the unit-safe strategy). Equal →
   `up_to_date`; positively unequal → `drifted` (record `{field, basis_value,
   current_value, current_fact_id}` in `drifted_fields[]`); ambiguous/uncoercible
   on either side → neutral/informational, **never** `drifted`.

### Step 3 — Reviewer-supplied fields

For the reviewer-only fields (`thermal_coefficient_pct`,
`power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`,
`cec_efficiency_pct`, the loss fields, `pto_date`) whose `field_sources` entry is
`{"source": "reviewer_supplied"}` (no `fact_id`): classify as
**`no_fact_lineage`** — there is no "live reviewer value" anywhere to drift
against (reviewer values live only inside the baseline snapshot). Informational;
never `drifted`.

### Step 4 — Temporal anchor

**Drop** the `fact_time > baseline.created_at` test (audit gap G4) — value
comparison replaces it. Timestamps are retained only as informational metadata
(`basis_captured_at = approved_at or active_from or created_at`), never as a
drift trigger.

### Step 5 — Baseline-level rollup

Precedence (informational ordering, not a blocker escalation):

```
basis_unknown            (no recorded basis at all)         → neutral
> drifted                (>=1 fact-backed field differs)    → needs-review
> source_retired         (basis fact retired, no active)    → needs-review
> up_to_date             (all compared fields match)        → ok
no_fact_lineage fields never escalate the rollup.
```

The resolver returns:

```
SourceBasisDrift {
  state: "up_to_date" | "drifted" | "basis_unknown" | "source_retired",
  baseline_id: int | null,
  basis_captured_at: datetime | null,
  unknown_basis: bool,
  drifted_fields: SourceBasisDriftField[]   # [{field, basis_value, current_value, current_fact_id}]
  no_fact_lineage_fields: string[],
  note: string                              # honest, human-readable summary
}
```

All-read-only; the function never flushes, commits, or writes.

---

## 3. Value-sensitive comparison strategy

The fact `value` is the envelope `{"v": <scalar>}` and the scalar is frequently
**text-with-unit** (Site 4: `"340 Wp"`, `"66 kWac"`). The comparison must mirror
the **bridge's own ordering** in `baseline_from_facts_service.py`, which is:

1. `raw = _unwrap(fact.value)` → strip the envelope.
2. **Try plain numeric first:** `numeric = _coerce_number(raw)`. If
   `numeric is not None`, compare `numeric` against the recorded basis value.
3. **Only if `_coerce_number` returns `None`** (a non-numeric, unit-bearing
   string) **and** `input_norm.is_normalizable_field(column)`: call
   `input_norm.propose(column, raw)`. If the proposal is **not** `blocked` and
   `proposed_value is not None`, compare `proposal.proposed_value` against the
   basis. (Calling `propose()` on an already-numeric value returns a `blocked`
   proposal — which is exactly why coercion must come first; the bridge does the
   same.)
4. **Cast both sides to `float`** before comparing — typed baseline columns are
   `Numeric`/`Decimal`. Use `input_norm.values_match(basis_float, current_float)`
   for tolerant equality (it returns `False` if either side is `None`).
5. **Quantity fields** (`module_quantity`, `inverter_quantity`) are unitless
   counts — `_coerce_number` only; never normalized.
6. **Dates** (`pto_date`) compare as calendar dates; reviewer-only by nature →
   `no_fact_lineage`.
7. If neither path yields a comparable number on either side → classify
   neutral/informational (`basis_unknown`-style), **never** assert `drifted`.

> Principle: a value is only `drifted` when we can **positively** establish that
> the normalized current value differs from the recorded basis. Any
> ambiguity resolves to a neutral/informational state, never a false "drift."
> This is what eliminates the Site 4 false positive and audit gaps G1/G1b.

---

## 4. Handling missing bridge snapshots

(Audit gap G3; Site 4 #4 is the live case.)

- **Detection (per field, then rolled up):** a field with no entry in
  `source_facts` / `field_sources` has **no recorded basis** → that field is
  `basis_unknown`. The **baseline-level** state is `basis_unknown` only when
  **no** field has any recorded basis (`source_facts` empty **and**
  `source_fact_signature is None`) — manual create, legacy `create_draft`, or the
  replacement/correction path. `source_project_fact_id` alone is **not** a
  sufficient basis manifest and is never used to declare a baseline "known."
- **Classification:** baseline-level **`basis_unknown`**; per-field
  `basis_unknown`. **Never** `drifted`, **never** `blocks_reporting`. Blocking
  level is `informational` (or omitted) so it does not gate reporting.
- **UI:** a neutral chip "Source basis not recorded" (not red). The honest
  message is "this baseline was not built from tracked facts, so drift can't be
  evaluated" — not "the source changed."
- **Explicitly NOT done:** we do **not** back-fill a synthetic snapshot, do
  **not** infer lineage from the typed columns, and do **not** mutate #4. (An
  optional, clearly-labeled *informational* "typed-column vs current-fact value
  match" line could be shown later, but it is **off by default** and never
  rendered as drift — deferred, not part of this approval.)

---

## 5. Handling reviewer-supplied constants

(Audit gap G2.)

- The five required reviewer constants + loss fields + PTO have no `fact_id` in
  `field_sources` and no live counterpart outside the baseline snapshot, so they
  **cannot drift via facts**.
- Classify each explicitly as **`no_fact_lineage`** (returned in
  `no_fact_lineage_fields[]`) — informational, surfaced as "set by reviewer; can
  only change via a new baseline." They are **never** silently ignored and
  **never** flagged as `drifted`.
- They do not escalate the baseline-level rollup state.
- **Surfacing note:** in the current reconciliation catalog the per-row
  `HEADER_COLUMN` entries are only the four fact-backed fields — the reviewer
  constants are **not** active-baseline table rows (they appear as
  equipment/`NONE`-target or baseline source metadata). So `no_fact_lineage` for
  these constants is reported as **baseline-level source metadata**
  (`no_fact_lineage_fields[]`), not as a new per-row table warning.

---

## 6. Baseline-level UI surfacing plan

(Audit gap G5 — today drift appears only per-field in the table.)

- **`ValidationHistoryPanel.tsx`:** on the **active** baseline row, render a
  source-basis chip driven by `readiness.source_basis_drift.state`:
  - `up_to_date` → subtle "Source basis: up to date" (success/neutral).
  - `drifted` → "Source basis drifted (N field(s))" with the drifted field names
    in a tooltip; the existing copy "Rebuild the active baseline to include the
    latest promoted value." as the action caption.
  - `basis_unknown` → neutral "Source basis not recorded" (never red).
  - `source_retired` → "Source fact retired" (needs-review).
- **`ReadinessSummary.tsx`:** one summary line mirroring the same state, so the
  reviewer sees baseline-level drift without scanning every row.
- **Per-field table (`StatusCell`):** unchanged UI; `active_baseline_outdated`
  now reflects the accurate value-based result, so the four Site 4 rows stop
  showing a false `blocks_reporting`.
- All surfaces are read-only display; no new mutation affordance is introduced.
  The only call-to-action remains the pre-existing manual rebuild path.

---

## 7. Site 4 validation plan (read-only)

**No Site 4 rows are mutated.** All checks are observation / GET-only.

- **Pre-change baseline (today):** Project Hub → Site 4 (110 Shawmut) →
  Reconciliation. Confirm the four fact-backed fields show
  `active_baseline_outdated` / `blocks_reporting` even though the typed values
  (340 / 1900 / 66 / 7) equal the current facts — the documented false positive.
- **Post-change expected:**
  - Baseline #4 baseline-level state = **`basis_unknown`** (it has NULL
    signature / empty `source_facts`) → neutral chip, **not** drift.
  - The four fact-backed fields = **not** `drifted`, **not** `blocks_reporting`.
  - Expected output, baseline status (#4 stays active), the active row, and #3's
    superseded state are all **unchanged**.
- **Network check:** the reconciliation / drift surfaces issue **GET** only; no
  POST/PUT/PATCH/DELETE fires from viewing drift.
- Backend assertion: a read-only DB `SELECT` before/after confirms Site 4 facts
  and baselines #3/#4 are byte-identical (no writes).

---

## 8. Migration impact

- **D1–D3 (the approved scope): NO migration.** Every input already exists —
  `model_parameters_json` (`source_facts`, `field_sources`,
  `source_fact_signature`), the header pointers, the immutable typed-column
  snapshot, and the live `project_facts`. The change is a read-only resolver plus
  additive **nullable** response fields.
- **D4 (acknowledgement ledger): OUT OF SCOPE** for this approval. If later
  desired, it would be a single **additive** migration (append-only table,
  nullable FKs, no backfill, no destructive change) and would remain
  informational — never altering baseline status. Not built unless separately
  approved.
- No column is added to `telemetry_expected_baselines` or `project_facts` in
  this plan.

---

## 9. Mutation boundaries

**Frozen — must NOT change:**

- Expected math / `expected_service`, the weather-adjusted formula, and every
  stored/active baseline value. The active baseline stays **immutable** (replaced
  only via supersede, never edited).
- Baseline lifecycle (`approve` / `activate` / supersede), the single-active
  partial unique index, and `can_drive_expected` (frozen to
  `{inverter, module, weather_station}`).
- Authorization / permissions, WS.5, weather semantics, device mappings,
  ingestion contracts, the telemetry scheduler, and O&M charts.
- `project_facts` rows and promotion behavior (no auto-promote, no source
  replacement).
- **Site 4** facts and baselines — read-only throughout.

**MAY change — additive / read-only only:**

- New read-only `baseline_source_basis_drift.py` resolver.
- Additive **nullable** `source_basis_drift` on the reconciliation readiness
  response (+ its schema).
- Re-derivation (not behavior change) of the existing `active_baseline_outdated`
  warning from the value-based resolver.
- Frontend display (badge + summary line).
- (Optional, deferred) a dedicated read-only drift endpoint.

---

## 10. Backend / frontend test plan

**Backend unit (resolver — pure, read-only):**

- Value-equal current fact vs. recorded basis → `up_to_date` (covers the Site 4
  false positive: new fact id, same value ⇒ **not** drift).
- Value-changed current fact → `drifted`, field present in `drifted_fields`.
- Re-promotion to the **same** value with a new `fact_id` → `up_to_date` (G1).
- Re-promotion that changes only the **string form** of an equal value
  (`"340 Wp"` → `"340Wp"`) → `up_to_date` (signature mismatch must fall through
  to value comparison, not flag drift).
- Active baseline with empty `source_facts` / NULL `source_project_fact_id` →
  `basis_unknown`, **not** `drifted` (G3 / Site 4 #4).
- Reviewer-supplied field (no fact) → `no_fact_lineage` (G2).
- Text-with-unit fact (`"340 Wp"`) vs. numeric snapshot `340.0` → equal **only**
  after `input_norm` normalization; assert `_coerce_number` alone is insufficient.
- Basis fact retired with no active replacement → `source_retired`.
- No active baseline / no facts → empty honest result (no 500).
- **Zero-write assertion:** the resolver performs no flush/commit (spy/count).

**Backend integration:** the reconciliation endpoint returns the additive
`source_basis_drift` block and the re-derived `active_baseline_outdated` with no
mutation; superseded/draft baselines are ignored; response stays
back-compatible.

**Harness notes:** ilios-server pytest needs `test_db_name` + a separate DB; run
client/lifespan tests with `telemetry_scheduler_enabled=false` (lowercase,
case-sensitive) so the scheduler doesn't hang; no `pytest-mock` (use
`monkeypatch`); `PermissionType` is a plain `str`.

**Frontend (component tests):**

- Badge renders `up_to_date` / `drifted (N)` / `basis_unknown` (neutral) /
  `source_retired` from `source_basis_drift.state`.
- `basis_unknown` **never** renders a red drift state.
- Readiness summary line matches the badge state and shows the rebuild action
  only when `drifted`.
- Build/lint gates: trust the Frontend webpack "No issues found." (fork-ts-checker)
  signal; the production build also runs ESLint (prettier/display-name/unused) —
  keep new components lint-clean.

---

## 11. Browser-validation plan

All steps are **read-only observation** (no Site 4 mutation):

1. **Site 4 false-positive fix:** Reconciliation tab → confirm the four
   fact-backed fields no longer show `blocks_reporting`/`active_baseline_outdated`
   and the active baseline (#4) badge reads **basis not recorded** (neutral), not
   "drift."
2. **Positive drift (a non-protected site):** build a draft from facts → approve
   → activate; re-promote a physics fact to a **different** value; confirm the
   field shows `drifted`, the baseline badge shows "drifted (1)", the action
   reads "Rebuild the active baseline…", and the **expected line, baseline
   status, and active row are unchanged**.
3. **Equal-value re-promotion (non-protected site):** re-promote the same value;
   confirm **no** drift appears (G1 fixed).
4. **Governance check:** confirm the expected/O&M chart and baseline status never
   change due to any drift state, and the drift surfaces are GET-only.

---

## 12. Confirmation: scope of change

This plan, when built, changes **only** read-only detection + additive display.
It explicitly does **not** change any of the following:

- **Expected math / output:** frozen — no recalculation, no historical rewrite,
  expected stays N/A where honest (never fabricated 0).
- **Baseline lifecycle:** frozen — no auto-deactivation, no auto-activation, no
  status transition; the single-active index and immutability hold.
- **Permissions / authorization:** unchanged — reconciliation stays
  `Diligence:view` + `get_authorized_site`; any optional endpoint reuses the
  **same** `Diligence:view` + `get_authorized_site` guard (never a broader
  asset-view scope), so diligence provenance access is not widened.
- **Facts (`project_facts`):** read-only — no promotion, no acceptance, no
  override, no source replacement.
- **WS.5 / weather semantics:** untouched.
- **Device mappings / `can_drive_expected`:** untouched and frozen.
- **Ingestion, scheduler, O&M charts:** untouched.
- **Site 4:** read-only — no row mutated.
- **Migrations:** none in the approved scope (D1–D3).

The single behavioral change users will notice is **more accurate, honest drift
information** (and the disappearance of the Site 4 false positive), surfaced as
needs-review / informational signals with the existing manual "rebuild" as the
only remediation.
