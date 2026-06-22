# Weather Device Semantics Review, Eligibility, and Governed Declaration — Design / Audit Sprint

**Status:** Design & audit only. **No production code changes in this sprint.**
**Scope:** Define the governed workflow that lets an authorized reviewer *declare and
maintain* weather‑device measurement semantics required for the weather‑adjusted
expected model — auditably, distinctly from provider/source metadata, and without
ever inferring, silently changing, or auto‑clearing anything.

This document answers the ten required return items in order (§1–§10), grounded in
the verified current code/schema and in Site 4 (110 Shawmut) live data.

---

## Hard rules this design must obey (carried verbatim from the brief)

1. Do **not** infer POA, cell temperature, or calibration merely from device name/type.
2. Do **not** silently change existing weather mappings.
3. Do **not** auto‑clear Site 4's blocking weather dependency.
4. Do **not** alter expected formula math, telemetry ingestion, rollups, baseline
   lifecycle, or device eligibility without an explicit approved follow‑up.
5. Preserve the W0 rule: **unknown semantics remain unknown**.
6. A reviewer declaration must be **auditable** and **distinct** from
   provider‑confirmed / source‑backed metadata.
7. Any change must create **new lineage or explicit supersession** — never rewrite a
   prior weather assumption.

---

## 1. Current weather‑device mapping & semantics model (as built)

### 1.1 Storage — `weather_device_mappings` (verified columns)

Per‑`(device, metric)` row. Verified live columns:

| Column | Type / default | Notes |
|---|---|---|
| `id` | int PK | |
| `site_id` | int NOT NULL | tenant anchor |
| `device_id` | int NULL | the iliOS device (e.g. IMT cell) |
| `external_device_id` | varchar NULL | provider device id |
| `weather_source_id` | int NULL | optional W0 source identity |
| `metric` | varchar **NOT NULL** | e.g. `irradiance_wm2`, `cell_temperature_f` |
| `provider_key` | varchar NULL | provenance only |
| `irradiance_plane` | enum **NOT NULL** default `unknown` | `poa, ghi, dni, dhi, unknown` |
| `temperature_type` | enum **NOT NULL** default `unknown` | `cell, module, ambient, modeled_cell, unknown` |
| `calibration_status` | enum **NOT NULL** default `unknown` | `calibrated, uncalibrated, expired, unknown` |
| `calibrated_at` | timestamp NULL | |
| `calibration_reference` | varchar NULL | free‑text cert/reference |
| `effective_from` / `effective_to` | timestamp NULL | effective window (open bounds allowed) |
| `created_at` / `updated_at` | timestamp | `updated_at` implies in‑place edit is *possible* today |

**"Current" selection:** `WeatherDeviceMappingCRUD.get_current_for_device()` returns
the **latest row by `id` desc**. Supersession is therefore *implicit* ("latest id
wins"); there is no explicit `supersedes_*`, no `status`, and no declarer identity.

### 1.2 Physics‑usability verdict (read‑only, derived)

`app/schema/weather.py`:
* `_PHYSICS_USABLE_PLANES = {poa}`
* `_PHYSICS_USABLE_TEMPERATURES = {cell, module, modeled_cell}`

Used by `device_eligibility_diagnostics_service` to emit
`weather_semantics_undeclared` / `weather_semantics_unknown` /
`weather_not_physics_usable` / `weather_calibration_unknown` indicators. These are
**disclosure only** — they never convert or promote.

### 1.3 Resolver consumption (`WeatherResolver`, W1)

`resolve_window()` is the read seam `compute_site_expected` uses for
`irradiance_poa_wm2` and `cell_temperature_f`. A window is `semantics_verified`
**only** when the declaring mappings for a metric (a) declare exactly one distinct
non‑`unknown` value, (b) their effective periods' union **fully covers** the window,
and (c) no coexisting `unknown` mapping overlaps. Otherwise it resolves
`legacy_das_unverified` — the value stays `unknown`, never promoted to POA/cell.

### 1.4 Existing write path & governance ledger

* Declare endpoint already exists: `POST /api/weather/sites/{site_id}/device-mappings`
  (`telemetry_admin_required` + site/company‑admin), body
  `WeatherDeviceMappingDeclareRequest`. It can create a mapping today.
* `weather_source_approvals` is an **append‑only ledger**
  (`site_id, target_type, target_id, action, approved_by, approved_at, rationale`).
* `expected_weather_provenance` exists but is **written by no runtime** (W0/W1).

### 1.5 Gap analysis — why the *existing* model is not yet "governed"

The semantic *columns* exist, but the **governance layer the brief requires does
not**:

| Required by brief | Present today? |
|---|---|
| Reviewer identity + timestamp on the declaration | ❌ (only `created_at`; no `declared_by`) |
| Declaration **basis** distinguishing reviewer‑assumption vs provider‑confirmed vs source‑document vs reviewer‑source‑note | ❌ |
| Evidence references (document/file id, provider‑metadata pointer, free note) | ⚠️ only `calibration_reference` free‑text |
| Sensor role & model captured on the declaration | ❌ (model lives on `devices`, not confirmed into the mapping) |
| Explicit status lifecycle (draft/active/superseded/needs‑re‑review) | ❌ |
| Explicit supersession lineage (`supersedes_mapping_id`) | ❌ (implicit latest‑id) |
| Re‑review trigger when upstream device identity/config/evidence changes | ❌ |
| Append‑only guarantee (no in‑place edit) | ⚠️ `updated_at` suggests edits are reachable |

**Conclusion:** this sprint's work is an *additive governance layer over the existing
`weather_device_mappings`* (plus reuse of the approvals ledger) — not a new semantics
store and not a change to the resolver/physics.

---

## 2. Site 4 — IMT Reference Cell evidence inventory (live data)

**Site:** id 4, "110 Shawmut", company 6, timezone `America/New_York`, not archived.

**Devices (13 total):** 7× SunGrow 60k inverters (all telemetry‑mapped), 1× Elkor
Production Meter (`meter`, mapped), 2× `network_gateway` (PowerLogger 1000 mapped; one
unmapped), 1× modem (unmapped), 1× **weather_station = "IMT Reference Cell w/ Mod"**
(device **318**, mapped), 1× null‑category "Site Performance" (device 320, unmapped —
likely a virtual aggregation target).

**The IMT Reference Cell (device 318):**
* `category = weather_station`; `type`, `manufacturer`, `model`, `serial_number` all **NULL**.
* All telemetry‑classification columns **NULL** → everything is *derived*
  (`weather_source_capable = True` via category only). No operator overrides.
* **Telemetry‑mapped and live:** `telemetry_devices_mapping` id 88 →
  `external_device_id 127737`, active, `provider_account_id 6`. Readings flow.
* **Weather semantics: NONE.** Zero `weather_device_mappings` rows for Site 4 →
  `has_declaration = False` → plane/temperature/calibration all effectively `unknown`.
* **No native weather provenance at all:** zero `weather_sources`, zero
  `weather_source_profiles` for Site 4.

**Documented weather facts (active `project_facts`):** 12 monthly + annual **GHI**
estimates (e.g. annual `1408.1 kWh/m²`), `weather_forecasting_model =
"Meteonorm 7.1 (1991-2005) - Synthetic"`, type `Synthetic`. So the *documented*
weather is **modeled GHI**, not measured POA — it cannot substitute for a
physics‑usable on‑site POA/cell declaration.

**Documented equipment inventory (for context, all JSONB `{"v": …}` envelopes):**
`inverter_quantity = 7`, `inverter_model = "SG60KU-M"`, `module_quantity = 1900`.

**This confirms the accepted Phase A truth model:** documented + discovered inverter
inventory reconcile (7/7); Site 4 remains `needs_reconciliation` **solely** because
the active weather‑adjusted expected depends on the IMT Reference Cell whose
irradiance plane, temperature type, and calibration are **unresolved** (no governed
declaration exists). Nothing here should be auto‑cleared.

---

## 3. Available provider metadata & document sources (what evidence exists)

**Provider (AlsoEnergy) metadata for the IMT — verified `raw_metadata`:**
```
functionCode: "WS"   (weather station)
stringId:     "C10843_S41345_WS0"
flags:        ["IsEnabled"], iconUrl, lastUpdate, lastUpload
```
→ The provider declares **weather‑station capability only**. It says **nothing**
about plane (POA vs GHI), temperature type (cell vs ambient), or calibration. So
provider metadata can *suggest a sensor exists*, never *confirm its semantics*.

**Ingestion metric‑catalog assumptions (`telemetry_metric_catalog`, AlsoEnergy):**
```
Sun   -> POA_Irradiance -> irradiance_wm2
Sun2  -> GHI_Irradiance -> irradiance_wm2
Temp1 -> Temp_Module    -> cell_temperature_f
```
> **Critical distinction.** These are **ingestion‑normalization assumptions** that map
> a raw provider field to a normalized metric (even *naming* one "POA"). They are
> **not** governed reviewer declarations of physical semantics and **must never** be
> treated as the truth that promotes `unknown → POA/cell`. The governed declaration is
> the only authority for physics‑usability; the catalog only decides which raw field
> becomes which stored metric. Keeping these two layers distinct is the heart of rule 1.

**Document sources:** Site 4 carries Diligence documents. Sensor datasheets,
commissioning/PTO reports, and calibration certificates (if uploaded) are the
file‑level evidence a reviewer would cite as `source_document`. File‑level evidence
inspection is deferred to implementation (it requires opening individual files).

**Net:** for the IMT today, the strongest *automatable* signal is "it is a weather
station." Everything physics‑relevant (POA, module‑back temp, calibration) requires a
**human reviewer declaration with a stated basis** — exactly what this sprint defines.

---

## 4. Proposed declaration schema (additive over `weather_device_mappings`)

Extend the existing per‑`(device, metric)` mapping with governance columns; **forbid
in‑place edits**; version by **new row + explicit supersession**. New enums:

* **`weather_declaration_basis`** (the audit distinction required by rule 6):
  * `provider_confirmed` — provider metadata explicitly states the semantic.
  * `source_document` — an uploaded document/spec states it (cite the file).
  * `reviewer_source_note` — reviewer cites an external source, not an uploaded file.
  * `reviewer_assumption` — reviewer‑supplied assumption, **no external backing**
    (lowest confidence; explicitly flagged, never silent).
* **`weather_declaration_status`**: `draft → active → superseded`, plus
  `needs_re_review` (a re‑review demand, never auto‑cleared).

Additive nullable columns on `weather_device_mappings`:

| Column | Purpose |
|---|---|
| `declaration_basis` (enum, NULL) | which of the four bases above |
| `declared_by` (FK users) / `declared_at` | reviewer identity + timestamp |
| `declaration_status` (enum, default `active` for new governed rows) | lifecycle |
| `supersedes_mapping_id` (self‑FK) | explicit lineage (never edit prior) |
| `superseded_by_mapping_id` (self‑FK) | forward pointer (set on the prior row only as a status flip, not a value rewrite) |
| `needs_re_review` (bool) + `re_review_reason` (varchar) | upstream‑change demand |
| `source_document_id` (FK documents) / `source_file_id` (FK files) | evidence refs |
| `provider_metadata_json` (jsonb) | snapshot of provider metadata used as basis |
| `reviewer_note` (text) | rationale / external‑source citation |
| `sensor_role` (varchar) / `sensor_model` (varchar) | confirmed role & model |
| `eligibility_snapshot_json` (jsonb, NULL) | the derived verdict at declaration time (audit only; live verdict still computed on read) |

**Invariants:**
* A declaration is created as a **new row**; the prior current row is flipped to
  `superseded` (status only) and back‑linked — **its semantic values are never
  changed**. (Implementation forbids UPDATE of value columns; the only mutation to a
  prior row is the `superseded` status flip + `superseded_by_mapping_id`.)
* Defaults remain `unknown` (rule 5). A reviewer must *choose* a non‑unknown value;
  the system never fills it.
* Every state change also appends a `weather_source_approvals` row
  (`target_type = weather_device_mapping`, `target_id`, `action`, `approved_by`,
  `rationale`) — the immutable audit trail.

**Per‑metric granularity:** the IMT cell yields **two** declarations — one
`metric = irradiance_wm2` (plane) and one `metric = cell_temperature_f`
(temperature_type) — matching the resolver's per‑metric verification.

---

## 5. Permission model

* **Declare / supersede / re‑review (writes):** `telemetry_admin_required` **+**
  site/company‑admin authorization (`get_authorized_site_with_company_admin`) — the
  same bar as the existing declare endpoint.
* **Cross‑tenant safety:** any `weather_source_id` / document / file referenced is
  validated via `WeatherSourceCRUD.get_visible_to_site` (and equivalent site‑scoped
  checks) so a site‑A admin can never attach site‑B evidence (W1 byte‑identity memo).
* **`reviewer_assumption` basis** requires an explicit confirmation flag + non‑empty
  `reviewer_note` (raise the friction for the lowest‑confidence basis).
* **Read (diagnostics / history):** asset‑view + company‑visibility (the eligibility
  diagnostics bar) — read endpoints never require admin.
* **Reviewer identity** = the authenticated admin, recorded in `declared_by` and the
  approvals ledger.

---

## 6. Relationship to `weather_device_mappings`

* **Extends, does not replace.** All governance is additive columns on the existing
  table + reuse of `weather_source_approvals`. No new semantics store.
* **Append‑only + explicit supersession** replaces the implicit "latest‑id wins"
  with auditable lineage; `get_current_for_device` is refined to prefer
  `declaration_status = active` (falling back to latest‑id for legacy rows so existing
  behavior is preserved where no governed row exists).
* **For Site 4 specifically:** there are zero rows today, so the first IMT
  declarations are clean creates (no supersession) — the foundation is empty and ready.
* **W0/W1 untouched:** observations, profiles, the resolver math, and
  `expected_weather_provenance` are not modified by the declaration layer itself.

---

## 7. Expected / baseline impact rules

* **The resolver math is unchanged (rule 4).** `WeatherResolver` already consumes
  `weather_device_mappings`; a governed POA/cell declaration simply *provides inputs
  the existing math already reads*. No formula, ingestion, rollup, or baseline‑lifecycle
  change ships in the declaration sprint.
* **No auto‑clear (rule 3).** The blocking weather dependency lifts **only** when a
  reviewer issues a verifiable declaration (POA plane and/or cell‑usable temperature,
  physics‑usable, full window coverage per the W1 rule). That is a governed human act,
  not automation; importing readings or running the scheduler never creates/changes a
  declaration.
* **Eligibility verdict is derived, not frozen.** `expected_model_eligible` =
  `plane ∈ physics_usable_planes` (for irradiance) and/or
  `temperature_type ∈ physics_usable_temperatures` (for temperature), AND status
  `active`, AND `needs_re_review = false`. Stored only as an audit snapshot; the live
  verdict is always recomputed on read.
* **GHI/ambient/assumption never promote.** A `ghi`/`dni`/`dhi`/`ambient` declaration,
  or a `reviewer_assumption` without physics‑usable values, is recorded and surfaced
  but does **not** make the window verified (it stays `legacy_das_unverified`).
* **Baseline interaction (deferred):** writing `expected_weather_provenance` and any
  baseline re‑validation triggered by a newly verified window are an **explicit
  approved follow‑up** (Phase WS.5), gated per rule 4. The declaration sprint stops at
  "inputs are now governed and available."

---

## 8. Reconciliation state changes (read‑only reflection)

The Phase A inventory‑reconciliation service already emits a
`weather_expected_dependency` mismatch for Site 4 because the IMT's semantics are
`unknown`. Reconciliation stays **read‑only**; it simply reflects the new mapping
state:

| Reviewer action on the IMT | `weather_expected_dependency` outcome | Site 4 headline |
|---|---|---|
| (today) no declaration | fires — semantics undeclared/unknown, `blocks_*` | `needs_reconciliation` |
| Declare **POA irradiance + cell/module temp**, calibrated, full coverage, basis source/provider | **clears** (declared + physics‑usable + verified) | can move toward reconciled if no other block |
| Declare **GHI** or **ambient**, or `reviewer_assumption` only | **does not clear**; downgrades from "unknown" to "declared‑but‑not‑physics‑usable" (`lowers_confidence`) with a precise reason | stays `needs_reconciliation` |
| Upstream IMT identity/config/evidence changes → `needs_re_review` | re‑fires as "declaration stale, re‑review required" | stays `needs_reconciliation` |

The DD `telemetry_reality` headline follows the same summary (single source of truth),
so the two surfaces can never disagree.

---

## 9. Test plan

**Schema / CRUD (unit):**
* New governed declaration creates a row with `declared_by/at`, basis, status `active`.
* Supersession creates a **new** row and flips the prior to `superseded` +
  back‑link — prior **value columns are byte‑identical before/after** (no rewrite).
* In‑place value edit is rejected (append‑only guard).
* Defaults stay `unknown`; nothing is auto‑filled (rule 5).
* `reviewer_assumption` requires the confirmation flag + note; distinct from
  `provider_confirmed`/`source_document` in storage and read‑back (rule 6).
* `needs_re_review` is set by the detector and **never auto‑cleared** — only a new
  declaration clears it (rule 7).

**Physics‑usability verdict (unit):** POA→usable; GHI/DNI/DHI/unknown→not; cell/
module/modeled_cell→usable; ambient/unknown→not; calibration handling.

**Resolver integration:** declaring POA + cell with full coverage →
`semantics_verified`; partial coverage or a coexisting `unknown` overlap → still
unverified (preserve the W1 rule); a GHI declaration never yields POA.

**Reconciliation (Site‑4‑shaped fixture):** before → `needs_reconciliation` (weather
block); after a POA+calibrated full‑coverage declaration → weather block clears;
after a GHI/assumption declaration → block remains with a changed, precise reason.

**Guardrails / zero‑side‑effect:**
* A declaration never touches `devices`, `telemetry_devices_mapping`, baselines, or
  `project_facts`.
* **Protected‑site fingerprint:** Site 4 telemetry‑mapping rows are identical
  before/after (only the intended new weather declaration rows appear) — abort/rollback
  on any other add/remove/edit.
* Ingestion / scheduler runs create or change **no** declaration (rule 3).
* Name/type alone never produces a non‑unknown value (rule 1) — a fixture named
  "…Reference Cell…" with no reviewer input stays `unknown`.

**Permission:** non‑admin → 403; cross‑tenant `weather_source_id`/document/file →
rejected via `get_visible_to_site`.

---

## 10. Implementation phases (each a separately approvable follow‑up)

* **WS.0 — Design/audit (this document).** No code.
* **WS.1 — Additive migration + enums.** Governance columns on
  `weather_device_mappings` (all nullable), `weather_declaration_basis` /
  `weather_declaration_status` enums, append‑only value guard. No backfill (legacy
  rows keep latest‑id behavior). Read‑only derived‑verdict helper.
* **WS.2 — Governed declaration service + endpoints.** Create / supersede / list /
  history, reusing `weather_source_approvals`; permission + cross‑tenant safety; **no**
  resolver/math change. Refine `get_current_for_device` to prefer `active`.
* **WS.3 — Upstream‑change detector (read‑only signal).** Detect IMT identity/config/
  evidence change → set `needs_re_review` (never auto‑clear); surface in eligibility +
  reconciliation diagnostics.
* **WS.4 — Frontend governed declaration UI.** Reviewer form (basis selection,
  evidence capture, calibration, effective date, supersession & re‑review), read‑only
  history/lineage view, surfaced in the project Telemetry tab + reconciliation panel.
* **WS.5 — (Explicitly gated) expected/baseline integration.** Write
  `expected_weather_provenance` and trigger any baseline re‑validation for newly
  verified windows. Ships **only** under a separate explicit approval (rule 4).

---

### Appendix — verified facts used in this audit
* `weather_device_mappings` enums: plane `{poa,ghi,dni,dhi,unknown}`, temp
  `{cell,module,ambient,modeled_cell,unknown}`, calibration
  `{calibrated,uncalibrated,expired,unknown}`; physics‑usable = `{poa}` /
  `{cell,module,modeled_cell}`.
* Site 4: 13 devices; IMT cell (id 318) mapped to AlsoEnergy `127737`
  (`provider_account 6`); **0** weather mappings/sources/profiles; weather facts are
  modeled GHI (Meteonorm 7.1 synthetic).
* IMT provider metadata declares `functionCode "WS"` only.
* Metric catalog: `Sun→POA`, `Sun2→GHI`, `Temp1→cell_temperature_f` are
  ingestion‑normalization assumptions, not governed semantics.
