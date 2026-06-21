# Equipment Datasheet Parsing + Governed Baseline Field Coverage — Audit & Design

**Status:** Audit / design only. No production code, migrations, endpoints, parser
rewrites, UI changes, data repairs, or baseline changes were made in this sprint.
Everything below is investigation and proposal; nothing here is implemented.

**Date:** 2026-06-21
**Scope owner:** Telemetry / Data Room / Baseline Readiness
**Related prior audits:**
- `docs/expected_baseline_readiness_input_audit.md`
- `docs/weather_adjusted_baseline_physics_validation_audit.md`
- `docs/data_room_transactional_integrity_audit.md`
- `docs/telemetry/telemetry_v2_baseline_selection_design.md`

---

## 1. Executive Summary

### What we set out to answer
A module/inverter specification sheet was uploaded and "did not produce useful
operational fields." The hypothesis was that the parser ran generic/contractual
extraction instead of equipment-specific document intelligence. This audit traces
the real attempt against live data, inventories current parser/document coverage,
and designs the source-backed equipment-document workflow (taxonomy, schemas,
unit policy, Data Room + Reconciliation UX, phased roadmap, and tests).

### Root cause (confirmed, two layers)
The hypothesis is **correct, and the situation is worse than a single misroute**:

1. **Immediate symptom — no parse ever ran.** The two module datasheets actually
   present in the system (Site 1 `doc 207 / file 17`, Site 4 `doc 1113 / file 25`)
   have **zero `ai_parsing_results` rows, zero `document_keys`, and zero
   `project_facts`**. Nothing was extracted, surfaced, or promoted. Both files are
   also `is_actual = false` (never marked the current version). The user saw an
   **empty, silent result with no error** — a "false empty," not an actionable
   "parse failed / no equipment schema" state.

2. **Structural defect — the equipment schema is a contractual stub.** Even if a
   parse had run, it could not have produced equipment fields. `module_specs`
   (registry id 125) and `inverter_specs` (id 132) are each mapped to the **exact
   same generic *contractual* 10-field schema** — `document_title`,
   `document_date`, `counterparties`, `effective_date`,
   `expiration_or_termination_date`, `term_or_duration`, `key_obligations`,
   `key_amounts_or_fees`, `governing_law_or_jurisdiction`, `summary` — driven by a
   generic "document extraction specialist" prompt. **201 of 218 registered
   document types share this identical contractual fieldset.** There is no
   `module_wattage`, `thermal_coefficient_pct`, `inverter_ac_power_kw`, etc.
   anywhere in the equipment schemas.

In short: the registry has the *labels* "Module Specs" / "Inverter Specs" and
marks them parsable, but it carries contractual *intelligence*, not equipment
intelligence. The blanket seeder gave every non-specialized type the contract
fieldset.

### The governance spine is sound and must be reused
The downstream governance chain is well-built and should **not** be rebuilt:
upload → (manual type) → registry-driven extraction → `document_keys`
(raw value + evidence + confidence + accept/override with reason/user/timestamp)
→ candidate `project_fact` → promotion to active fact (with freshness/stale
guard) → Reconciliation truth ladder → create-draft-from-facts → baseline review
/ approve / activate / period-effective selection / invalid-segment suppression.
The gap is purely at the **front of the chain**: equipment document intelligence
(schemas, prompts, canonical fields) and the **honest failure/empty UX**.

### Highest-impact recommendations (detail in §14)
1. Make parse failure / no-fields / not-yet-parsed **visible and actionable** in
   the Data Room and Reconciliation (kill the silent empty).
2. Replace the contractual stub schemas for **Module Datasheet** and **Inverter
   Datasheet** with real equipment schemas + equipment-aware prompts + new
   canonical fields (§5, §6).
3. Add the missing **canonical fields** for the physics inputs that today have
   *no fact source at all* (`thermal_coefficient_pct`, `power_tolerance_min_pct`,
   `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct`) so
   reviewers can supply/override them as governed values (§9).
4. Enforce the **governed unit/normalization policy** (preserve raw, never
   silently convert) end-to-end (§10).
5. Align **PTO/COD canonical naming** so a promoted date actually reaches Baseline
   Readiness (§8).

### Durable invariant reaffirmed
AI extraction is never operational truth by itself. Reviewer-entered values are
governed, auditable overrides/assumptions and must remain **visibly distinct**
from source-extracted values. No accepted/promoted/baseline/O&M state may silently
survive an upstream source change.

---

## 2. Failed Spec-Sheet Root-Cause Analysis (Section A)

### 2.1 The traced attempts (live data)

Two equipment specification documents exist in the system; both are module
datasheets. There are **no inverter datasheet uploads at all**.

| Attribute | Site 1 attempt | Site 4 attempt |
|---|---|---|
| `site_id` | 1 | 4 |
| `document_id` | 207 | 1113 |
| `documents.name` (enum) | `module_specs` ("Module Specs") | `module_specs` ("Module Specs") |
| `file_id` (version) | 17 (v1) | 25 (v1) |
| `filename` | `Module cut sheet-Q_CELLS_Data_sheet_Q.PEAK_DUO_L-G8.3_BFF_405-415_2019-12_Rev02_EN (1).pdf` | `modules_AXIpremium 72c 330-350Mono_F40.pdf` |
| `files.is_actual` | **false** | **false** |
| upload type selected by user | `module_specs` (correct) | `module_specs` (correct) |
| detected/classified type | n/a — no auto-classifier exists | n/a |
| parser route that *would* run | `ExtractionPipelineService` → registry config for `module_specs` | same |
| extraction registry record | doc type 125; active schema version 125 (v1, 10 fields); active prompt 125 (v1) | same |
| prompt/schema used | **generic contractual 10-field schema + generic prompt** | same |
| AI response status | **none** (no call recorded) | none |
| `ai_parsing_results` row | **none** | **none** |
| raw parsed result | none | none |
| fields attempted | none recorded (would be 10 contractual fields) | none |
| fields extracted | **none** | none |
| `document_keys` created | **none** | none |
| `project_facts` from file | **none** | none |
| Data Room behavior shown | empty — no extracted keys, no parse-run history, no error | empty |
| visible outcome | **no actionable output (silent empty)** | silent empty |

### 2.2 Registry state (live)
- `module_specs` (125) and `inverter_specs` (132) are both `is_parsable = true`,
  `is_active = true`, each with an active schema version (10 fields) and an active
  prompt template (`model_name = claude-sonnet-4-5`). So a parse would **not** be
  rejected for "config not found"; the config exists — it is just the wrong
  (contractual) config.
- Registry totals: **218 document types, all 218 `is_parsable` and `is_active`,
  all 218 with an active schema *and* fields *and* an active prompt.** This blanket
  state is itself a finding (see §3).
- **201 of 218 active schemas share the identical contractual 10-field set.** Only
  ~17 types carry purpose-built schemas (e.g., PVsyst 47-field set shared by 4
  PVsyst variants, Operating Agreement 8-field set, Loan/Security 14-field set,
  Site Lease 38-field set).
- Parse-run usage in practice is confined to contractual/PVsyst types
  (`site_lease`, `engineering_procurement_construction_epc_agreement`,
  `phase_1_esa`, `pv_syst_*`, `operating_agreement_*`). **No run has ever
  referenced `module_specs` or `inverter_specs`.** Five orphan runs exist with a
  `NULL document_type_id` (all non-completed) — a separate small data-hygiene
  signal.

### 2.3 The generic prompt + contractual fields (evidence)
Active `module_specs` system prompt is the generic:
> "You are a document extraction specialist. Your task is to extract specific data
> fields from the provided document text… Extract ONLY the fields listed… If a
> field value cannot be found, set value to null but still provide your best guess
> at where it might appear…"

(The "best guess at where it might appear" instruction is itself a mild
hallucination-risk pattern for equipment specs and should be tightened in §13.)

The 10 mapped canonical fields for both `module_specs` and `inverter_specs` are
contractual: `document_title, document_date, counterparties, effective_date,
expiration_or_termination_date, term_or_duration, key_obligations,
key_amounts_or_fees, governing_law_or_jurisdiction, summary`. None map to any
baseline/operational equipment field.

### 2.4 Answers to the nine required questions

1. **Did parsing fail technically or succeed with no relevant fields?** Neither
   *completed*. For the two real files **no parse run exists at all** — the
   immediate state is "never parsed" (silent empty). Structurally, had it run, it
   would have "succeeded with no relevant fields," because the schema is
   contractual.
2. **Was the document classified incorrectly?** No. There is **no auto-classifier**;
   the user manually selected `module_specs`, which is correct. Misclassification
   is not the cause.
3. **Did generic/contractual extraction run instead of equipment extraction?**
   **Structurally yes** — `module_specs`/`inverter_specs` are bound to the generic
   contractual schema/prompt. (No run fired for these two files, but any run would
   have used the contractual config.)
4. **Is a specialized datasheet schema absent?** **Yes — the central defect.** No
   equipment canonical fields exist; the equipment types reuse the contract stub.
5. **Did table/specification layout prevent extraction?** Unprovable from a run
   (none exists), but datasheets are table/figure-dense and the current pipeline is
   plain-text + generic prompt with no table/figure awareness — a likely
   contributor once parsing is enabled (see §13).
6. **Did extracted values fail canonical mapping?** N/A (no run); but by
   construction the available canonical fields have **no equipment targets**, so
   mapping to baseline inputs is impossible today.
7. **Did `document_keys` / candidate facts fail to generate?** Yes — none exist for
   either file.
8. **Did the Data Room fail to surface parsed results?** There were **no results to
   surface**. The Data Room did not throw; it simply had nothing — which is exactly
   the UX problem.
9. **Was the failure visible/understandable to the user?** **No.** The files look
   uploaded yet yield no fields and no error and were never marked `is_actual`.
   This silent empty is the most damaging user-facing issue.

### 2.5 One-line root cause
> Equipment datasheets are registered as parsable but bound to a generic
> *contractual* schema/prompt (201/218 types share it); the two real uploads were
> never parsed and produced a silent empty Data Room with no equipment fields, no
> facts, and no error.

---

## 3. Current Parser & Document Coverage Inventory (Section B)

### 3.1 Pipeline components (file map)
- **Document type enum:** `app/static/default_site_documents_enum.py`
  (`SiteDocumentsEnum`, 400+ values incl. `module_specs`, `inverter_specs`,
  `transformer_specs`, `storage_specs`, `battery_specs`, `racking_specs`,
  module/inverter warranty variants).
- **Registry models/tables:** `ExtractionDocumentType`, `ExtractionSchemaVersion`,
  `ExtractionSchemaVersionField`, `ExtractionPromptTemplate`, `CanonicalField`
  (tables `extraction_document_types`, `extraction_schema_versions`,
  `extraction_schema_version_fields`, `extraction_prompt_templates`,
  `canonical_fields`).
- **Config fallback:** `configs/ai_parsing_config.json` (gated by
  `settings.allow_config_fallback`); contains specialized lists only for
  contractual/PVsyst types — **not** module/inverter.
- **Pipeline/prompt assembly:** `app/services/extraction_pipeline_service.py`
  (`get_extraction_config`, `build_extraction_prompt`, `{{FIELD_LIST}}`,
  `{{DOC_TYPE}}`, `{{DOCUMENT_TEXT}}`).
- **Parsing service:** `app/services/in_app_parsing_service.py`
  (`InAppParsingService.parse_file`) — file fetch, text extraction, LLM call,
  observability, retries, idempotency/concurrency.
- **Trigger router:** `app/routers/due_diligence/files_parsing.py`
  (`trigger_file_parsing`, returns 400 "Parsing config is not found…" only when no
  registry **and** no JSON config exists — not the case for equipment today).
- **Keys/merge:** `app/helpers/files/file_helper.py`
  (`combine_user_ai_parsing_results`), file-version-scoped.
- **Baseline-driving flag:** `app/static/baseline_driving_fields.py`.
- **Reconciliation catalog:** `app/static/reconciliation_catalog.py`
  (`RECONCILIATION_CATALOG`, `SAFL_FIELD_MAP`).
- **Facts→baseline bridge:** `app/services/telemetry/baseline_from_facts_service.py`
  (`FACT_FIELD_TO_COLUMN`).
- **Input normalization:** `app/services/telemetry/baseline_input_normalization.py`.
- **Design points producer:** `app/services/telemetry/baseline_points_service.py`.
- **Promotion + freshness guard:** `app/services/.../promotion_service.py`
  (`promote_version`, `validate_promotion_freshness` → 409 `PROMOTION_SOURCE_STALE`).

### 3.2 Coverage by document type (representative)

Legend: ✅ purpose-built · ⚠️ generic/contractual stub · ❌ none

| Upload label | Parser schema | Generic fallback? | App-critical fields extracted today | Canonical mappings | Data Room review | Override | Task | Reconciliation | Downstream use | Known gaps |
|---|---|---|---|---|---|---|---|---|---|---|
| Module Specs | ⚠️ contractual stub (10) | yes (is the stub) | none equipment | none equipment | ✅ flow exists | ✅ | ✅ default task | ❌ no equipment rows | none today | **no module schema; no equipment canonical fields** |
| Inverter Specs | ⚠️ contractual stub (10) | yes | none equipment | none equipment | ✅ | ✅ | ✅ | ❌ | none | **no inverter schema; `inverter_ac_power_kw` etc. absent** |
| Module/Inverter Warranty | ⚠️ contractual stub (10) | yes | none degradation | none | ✅ | ✅ | ✅ | ❌ | none | **no degradation/warranty schema** |
| Transformer/Storage/Battery/Racking Specs | ⚠️ contractual stub (10) | yes | none | none | ✅ | ✅ | ✅ | ❌ | none | no equipment schemas |
| PVsyst (Initial/IFC/As-Built/Independent) | ✅ 47-field set | n/a | module/inverter qty+wattage, monthly+annual production, GHI, P50/P90, system type | `module_wattage`, `module_quantity`, `inverter_wattage`, `inverter_quantity`, `[month]_estimated_production_year_1`, `estimated_production_year_1`, `p50_mwh`, `p90_mwh` | ✅ | ✅ | ✅ | ✅ header + points | unit confirmation gaps; no thermal/degradation/efficiency |
| Site Lease | ✅ 38-field set | n/a | lease economics/terms | contractual | ✅ | ✅ | ✅ | n/a baseline | n/a | not equipment |
| EPC / Operating Agreement / Loan | ✅ purpose-built | n/a | contractual terms | contractual | ✅ | ✅ | ✅ | n/a baseline | n/a | not equipment |
| Interconnection / PTO | ⚠️ contractual stub | yes | PTO not isolated as canonical | `pto_date` exists but naming/route gap (§8) | ✅ | ✅ | ✅ | partial | baseline gate | **PTO parse→readiness gap** |
| All other (~201) | ⚠️ contractual stub | yes | generic | generic | ✅ | ✅ | ✅ | n/a | n/a | blanket stub |

### 3.3 Cross-cutting findings
- The governance chain (keys → candidate → promote → reconciliation → baseline)
  is **complete and shared**; it is not the bottleneck.
- The **registry is blanket-seeded** to "parsable + contractual," which makes
  *every* type look ready while only ~17 carry real intelligence. This is the
  source of the "looks supported but isn't" trap for equipment.
- **No document classifier** exists; document type is user-selected only.
- The prompt template references `claude-sonnet-4-5` while the platform's in-app
  parsing is configured via Replit AI Integrations (OpenAI). Whether
  `InAppParsingService` honors the template `model_name` or uses the integration
  default should be confirmed during implementation (open item §16); it does not
  change the schema root cause.

---

## 4. App-Critical Document Taxonomy (Section C)

Target Ilios taxonomy. "Manual select" = user can choose the type on upload (all
true today); "Classifier suggests" = proposed future suggestion (none today,
proposed in §13/§14 Phase 1).

| # | Document type (label) | Parser strategy | Manual select | Classifier suggests (future) | Baseline-driving fields | Operational fields | Investor/reporting fields | Evidence level | Review/override | Downstream modules |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Module Datasheet | Specialized equipment + table-aware | yes | yes | module_wattage, module_power_stc_w, thermal_coefficient_pct, power_tolerance_min_pct | efficiency, NOCT, Voc/Isc/Vmp/Imp, dimensions/area | manufacturer/model, warranty term | page+table+snippet | confirm units; override allowed | Baseline, Reconciliation, Overview |
| 2 | Inverter Datasheet | Specialized equipment + table-aware | yes | yes | inverter_ac_power_kw (=`inverter_wattage`), cec_efficiency_pct | MPPT range, max DC V, AC V/current, PF, temp range | manufacturer/model | page+table+snippet | confirm units | Baseline, Reconciliation, O&M device detail |
| 3 | Equipment Schedule | Tabular roster extraction | yes | yes | module_quantity, inverter_quantity | per-line make/model/qty | BOM totals | table rows | confirm counts | Baseline header, device mapping |
| 4 | PVsyst / Design Estimate Report | Specialized (exists) | yes | yes | module/inverter qty+wattage | losses, GHI, system type | P50/P90 | page+table | confirm units | Baseline header + design points |
| 5 | Production Estimate / Energy Model | Specialized (overlaps PVsyst) | yes | yes | monthly/annual production | specific yield | P50/P90, energy AC | table | confirm kWh vs MWh | Design points, reporting |
| 6 | Interconnection / PTO | Date/term extraction | yes | yes | pto_date / COD | utility, meter approval | milestone dates | page+snippet | confirm date | Baseline gate, reporting |
| 7 | Warranty Document | Warranty/degradation schema | yes | yes | year_1_degradation_pct, annual_degradation_pct (only if explicit) | warranty term, perf-warranty | guaranteed production | exact wording + page | reviewer-confirm derived | Baseline, reporting |
| 8 | EPC Agreement | Contractual (exists) | yes | optional | none | scope, milestones | contract value | clause | override | Acquisitions |
| 9 | PPA / Revenue Contract | Contractual (exists) | yes | optional | none | rate, term | revenue terms | clause | override | Finance, reporting |
| 10 | O&M Agreement | Contractual (exists) | yes | optional | none | scope, guarantees | fees | clause | override | O&M, Finance |
| 11 | DAS / Telemetry Provider Doc | Reference/metadata | yes | optional | none | provider, channels | — | snippet | override | Telemetry config |
| 12 | Weather Station / Sensor Spec | Equipment semantics (no conversion) | yes | yes | none (W0: never assume POA/cell) | irradiance plane, temp type, calibration | — | page+table | declare semantics (unknown default) | Weather provenance (W0) |
| 13 | Site Layout / One-Line / Electrical | Drawing (low text yield) | yes | optional | none | equipment counts (manual) | — | drawing ref | manual entry | Device mapping |
| 14 | Revenue Meter Documentation | Reference/metadata | yes | optional | none | meter make/model/CT ratio | — | snippet | override | Revenue, telemetry |
| 15 | Commissioning Report | Mixed (dates + results) | yes | optional | none | commissioning date, test results | — | page+snippet | override | O&M, reporting |
| 16 | As-Built Package | Composite (route sub-docs) | yes | optional | inherits from sub-docs | inherits | inherits | per sub-doc | per sub-doc | Multiple |

**Rule:** equipment specs (1, 2, 3, 12, 14) must **never** be inferred from
contracts (8, 9, 10) or unrelated documents, and contracts must never be parsed
with equipment schemas.

---

## 5. Module Datasheet Extraction Schema (Section D)

New canonical fields + a specialized schema/prompt. Units are **preserved raw**;
normalization is **suggested, never silently applied** (§10). `module_wattage`'s
baseline target is **Watts**.

| Canonical key | Display label | Raw extraction format | Expected unit | Normalized candidate policy | Baseline-driving | Reviewer confirm req’d | Source-backed override allowed | Required evidence | Confidence rule | Reconciliation target | Baseline Readiness target |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `module_manufacturer` | Module Manufacturer | text | — | none | no | no | yes | page+snippet | text match | informational | none |
| `module_model` | Module Model | text | — | none | no | no | yes | page+snippet | text match | informational | none |
| `module_wattage` | Module Wattage (STC) | number+unit | **W** | strip `W/Wp`; ×1000 from `kW/kWp` (suggest) | **yes** | yes if unit present | yes | page+table+snippet | numeric+unit | header row | `module_wattage` (header) |
| `module_power_stc_w` | Power at STC | number+unit | W | same as above (alias of wattage if equal) | yes (alias) | yes | yes | table | numeric | header row | feeds `module_wattage` |
| `module_power_ptc_w` | Power at PTC | number+unit | W | none | no | yes | yes | table | numeric | informational | none |
| `module_efficiency_pct` | Module Efficiency | number+`%` | % | strip `%` (suggest) | no | yes | yes | table | numeric | informational | none |
| `thermal_coefficient_pct` | Temp Coefficient of Pmax | number+`%/°C` | **%/°C** (negative) | **no auto-convert** °C↔°F; flag sign | **yes** | **yes (always)** | yes | table | numeric+unit+sign | new row | `thermal_coefficient_pct` (currently no fact source) |
| `voltage_temperature_coefficient_pct_per_c` | Temp Coeff of Voc | number+`%/°C` | %/°C | no auto-convert | no | yes | yes | table | numeric+unit | informational | none |
| `current_temperature_coefficient_pct_per_c` | Temp Coeff of Isc | number+`%/°C` | %/°C | no auto-convert | no | yes | yes | table | numeric+unit | informational | none |
| `power_tolerance_min_pct` | Power Tolerance (min) | number+`%` | % (≤0) | strip `%`; preserve sign | **yes** | **yes** | yes | table | numeric+sign | new row | `power_tolerance_min_pct` (no fact source today) |
| `power_tolerance_max_pct` | Power Tolerance (max) | number+`%` | % (≥0) | strip `%` | no | yes | yes | table | numeric | informational | none |
| `open_circuit_voltage_voc` | Voc | number+`V` | V | strip `V` | no | yes | yes | table | numeric | informational | none |
| `short_circuit_current_isc` | Isc | number+`A` | A | strip `A` | no | yes | yes | table | numeric | informational | none |
| `voltage_at_max_power_vmp` | Vmp | number+`V` | V | strip `V` | no | yes | yes | table | numeric | informational | none |
| `current_at_max_power_imp` | Imp | number+`A` | A | strip `A` | no | yes | yes | table | numeric | informational | none |
| `nominal_operating_cell_temperature_noct` | NOCT | number+`°C` | °C | no auto-convert | no | yes | yes | table | numeric+unit | informational | none |
| `module_length_mm` / `module_width_mm` | Module Dimensions | number+unit | mm | mm↔in suggest only | no | yes | yes | table | numeric+unit | informational | none |
| `module_area_m2` | Module Area | number+unit | m² | m²↔ft² suggest only | no | yes | yes | table | numeric+unit | informational | none |
| `module_product_warranty_years` | Product Warranty Term | number+`yr` | years | none | no | yes | yes | snippet | numeric | informational | none |
| `year_1_degradation_pct` | Year-1 Degradation | number+`%` | % | **no derivation from prose** | **yes** | **yes (always)** | yes | exact wording+page | numeric | new row | `year_1_degradation_pct` (no fact source today) |
| `annual_degradation_pct` | Annual Degradation | number+`%` | % | **no derivation from prose** | **yes** | **yes (always)** | yes | exact wording+page | numeric | new row | `annual_degradation_pct` (no fact source today) |

Notes:
- `module_wattage` and `module_power_stc_w` should reconcile to one header value;
  if both extracted and unequal, raise a reconciliation conflict, not a silent pick.
- Degradation values from a **datasheet** are acceptable when explicitly stated;
  degradation from **warranty prose** requires reviewer confirmation (§7).

---

## 6. Inverter Datasheet Extraction Schema (Section E)

**Critical:** the weather-adjusted baseline's `inverter_wattage` is **kW AC per
inverter**. Do not label it Watts. New canonical fields below.

| Canonical key | Display label | Expected unit | Raw-value preservation | Normalized candidate policy | Baseline-driving | Reviewer confirm | Evidence | Reconciliation target | Baseline Readiness target |
|---|---|---|---|---|---|---|---|---|---|
| `inverter_manufacturer` | Inverter Manufacturer | — | text | none | no | no | page+snippet | informational | none |
| `inverter_model` | Inverter Model | — | text | none | no | no | page+snippet | informational | none |
| `inverter_ac_power_kw` | Rated AC Power (per unit) | **kW AC** | keep raw+unit | strip `kW/kWac`; ×0.001 from `W/Wac` (suggest) | **yes** | **yes if unit present** | table | header row | `inverter_wattage` (header; kW AC) |
| `inverter_dc_power_kw` | Max DC Power (per unit) | kW DC | keep raw+unit | suggest only | no | yes | table | informational | none |
| `cec_efficiency_pct` | CEC Efficiency | % | keep raw+`%` | strip `%` | **yes** | **yes** | table | new row | `cec_efficiency_pct` (no fact source today) |
| `euro_efficiency_pct` | Euro Efficiency | % | keep raw+`%` | strip `%` | no | yes | table | informational | none |
| `max_efficiency_pct` | Max Efficiency | % | keep raw+`%` | strip `%` | no | yes | table | informational | none |
| `max_dc_voltage_v` | Max DC Voltage | V | keep raw+`V` | strip `V` | no | yes | table | informational | none |
| `mppt_voltage_min_v` / `mppt_voltage_max_v` | MPPT Voltage Range | V | keep raw+`V` | strip `V` | no | yes | table | informational | none |
| `nominal_ac_voltage_v` | Nominal AC Voltage | V | keep raw+`V` | strip `V` | no | yes | table | informational | none |
| `max_ac_current_a` | Max AC Current | A | keep raw+`A` | strip `A` | no | yes | table | informational | none |
| `power_factor_range` | Power Factor Range | — | text/range | none | no | yes | table | informational | none |
| `operating_temp_min_c` / `operating_temp_max_c` | Operating Temp Range | °C | keep raw+`°C` | **no auto-convert** | no | yes | table | informational | none |
| `cooling_method` | Cooling Method | — | text | none | no | no | snippet | informational | none |
| `monitoring_capabilities` | Comms/Monitoring | — | text | none | no | no | snippet | informational | none |

Note: `inverter_total_power_ac` already exists in the PVsyst schema; keep it
distinct from the per-unit `inverter_ac_power_kw` (per-unit × quantity should
reconcile to the total, surfaced as a check, not an auto-fill).

---

## 7. Warranty, Degradation & Design Assumptions (Section F)

Canonical fields and rules. **Degradation must not be derived from ambiguous
warranty prose without reviewer confirmation;** preserve original wording + source.

| Canonical key | Display label | Unit | Extraction rule | Candidate type produced | Reviewer policy |
|---|---|---|---|---|---|
| `year_1_degradation_pct` | Year-1 Degradation | % | extract only if explicitly stated as year-1 | extracted **or** derived-candidate (flagged) | confirm required if derived |
| `annual_degradation_pct` | Annual Degradation | % | explicit linear/annual rate only | extracted or derived-candidate | confirm required if derived |
| `linear_degradation_rate_pct` | Linear Degradation Rate | %/yr | explicit | extracted | confirm if converting to annual |
| `performance_warranty_terms` | Performance Warranty | text | preserve wording | extracted text | informational |
| `guaranteed_production_value` | Guaranteed Production | kWh/% | preserve wording+unit | extracted | confirm unit |
| `p50_value` / `p90_value` | P50 / P90 | MWh | numeric+unit | extracted (`p50_mwh`/`p90_mwh` exist) | confirm MWh vs kWh |
| `degradation_schedule` | Degradation Schedule | table | preserve table | extracted table | informational |
| `warranty_duration_years` | Warranty Duration | years | numeric | extracted | informational |
| `performance_ratio_assumption` | PR Assumption | — | explicit only | extracted | confirm |
| `loss_assumption_*` | Documented Loss Assumptions | % | explicit only (dc/ac/mv/soiling) | extracted | confirm; maps to loss fields §9 |

**Four-way value provenance must remain distinguishable** in the model and UI:
(1) source-extracted value, (2) derived candidate (system-proposed from prose,
flagged), (3) reviewer override (corrected source value, reason+evidence), (4)
reviewer-supplied assumption (no source value existed). The current model carries
the columns to express (1), (3), (4); **(2) "derived candidate" needs an explicit
flag** (open item §16) so a prose-derived degradation is never mistaken for a
datasheet-stated one.

---

## 8. PTO & Interconnection Flow (Section G)

### 8.1 Current behavior
- Canonical key is `pto_date`. Reconciliation maps it for **display** to the
  legacy SAFL field `permission_to_operate` via `SAFL_FIELD_MAP` (display/compare
  only — SAFL is never a baseline source).
- The expected physics model treats `pto_date` as a **hard gate**: if missing,
  expected is suppressed for the whole window (honest N/A) — by design.
- The facts→baseline bridge expects `pto_date` as a **reviewer-supplied required**
  input, **not** a fact-backed column in `FACT_FIELD_TO_COLUMN`.

### 8.2 The gap (why PTO can parse but not reach readiness)
If a reviewer promotes the date under a different canonical name (e.g.,
`permission_to_operate`, `cod`, `commercial_operation_date`,
`interconnection_approval_date`), it will **not** be recognized by Baseline
Readiness, which looks specifically for `pto_date` in the reviewer-supplied path.
There is also no Interconnection/PTO **extraction schema** today (contractual
stub), so PTO is not isolated as a first-class extracted field.

### 8.3 Design
- Add an **Interconnection / PTO** extraction schema with canonical fields:
  `pto_date`, `commercial_operation_date`, `interconnection_approval_date`,
  `utility_name`, `meter_approval_date`.
- Establish **`pto_date` as the single canonical truth**; define explicit aliases
  (`permission_to_operate`, `cod` where it means PTO) that **normalize to
  `pto_date` with reviewer confirmation** (never silently).
- Decide (open item §16) whether `pto_date` should additionally be **fact-backed**
  through the bridge (recommended) so a promoted PTO fact flows to readiness
  without a separate reviewer-supplied step — while preserving the hard-gate
  semantics.
- Reconciliation should show PTO with its real ladder position and a precise
  "Next:" action when the date exists but under the wrong canonical name.

---

## 9. Baseline Field Coverage Matrix (Section H)

Sources today: **F** = fact-backed via bridge; **R** = reviewer-supplied (no fact
source); **D** = derived; **default** = silent default applied.

| Field | Current source path | Desired source doc type | Parser support today | Canonical field today | DR review/override | Candidate/promotion path | Reconciliation row/status | Baseline readiness use | Current gap | Recommended remedy |
|---|---|---|---|---|---|---|---|---|---|---|
| `module_wattage` (W) | PVsyst fact (F) | Module Datasheet ∥ PVsyst | PVsyst only | `module_wattage` | yes | yes | header ladder | header | no datasheet path; unit confusion | §5 schema; unit policy §10 |
| `module_quantity` | PVsyst fact (F) | Equipment Schedule ∥ PVsyst | PVsyst only | `module_quantity` | yes | yes | header ladder | header | no schedule path | §4 #3 |
| module mfr/model | PVsyst fact | Module Datasheet | PVsyst only | `module_manufacturer/model` | yes | yes | informational | none | no datasheet path | §5 |
| `inverter_wattage` (kW AC) | PVsyst fact (F) | Inverter Datasheet ∥ PVsyst | PVsyst only | `inverter_wattage` | yes | yes | header ladder | header | no datasheet path; W/kW risk | §6; unit policy |
| `inverter_quantity` | PVsyst fact (F) | Equipment Schedule ∥ PVsyst | PVsyst only | `inverter_quantity` | yes | yes | header ladder | header | no schedule path | §4 #3 |
| inverter mfr/model | PVsyst fact | Inverter Datasheet | PVsyst only | `inverter_manufacturer/model` | yes | yes | informational | none | no datasheet path | §6 |
| `thermal_coefficient_pct` (%/°C) | **R (no fact source)** | Module Datasheet | none | exists as physics input only | not as governed field | none | **no row today** | physics required | **add canonical field + schema** §5 |
| `power_tolerance_min_pct` | **R** | Module Datasheet | none | physics input only | no | none | no row | physics required | add canonical field §5 |
| `year_1_degradation_pct` | **R** | Datasheet/Warranty | none | physics input only | no | none | no row | physics required | add §5/§7 |
| `annual_degradation_pct` | **R** | Datasheet/Warranty | none | physics input only | no | none | no row | physics required | add §5/§7 |
| `cec_efficiency_pct` | **R** | Inverter Datasheet | none | physics input only | no | none | no row | physics required | add §6 |
| `dc_loss_pct` | R / default 0 | PVsyst/Design | partial | optional | partial | partial | optional | optional | confirm-or-default clarity | §10 |
| `ac_loss_pct` | R / default 0 | PVsyst/Design | partial | optional | partial | partial | optional | optional | same | §10 |
| `medium_voltage_loss_pct` / `mv_line_loss_pct` | R / default 0 | PVsyst/Design | partial | optional | partial | partial | optional | optional | naming duplication | consolidate (§16) |
| `soiling_factor` | R / default 1.0 | PVsyst/Design | partial | optional | partial | partial | optional | optional | default masks absence | surface default explicitly |
| `pto_date` | **R required** | Interconnection/PTO | stub | `pto_date` (alias drift) | yes | partial | partial | **hard gate** | naming/route gap §8 | §8 remedy |
| system size DC | D (module W×qty) | PVsyst | derived | `system_size_dc` | n/a | derived | informational | derived | none critical | keep derived + show |
| system size AC | D (inverter kW×qty) | PVsyst | derived | `system_size_ac` | n/a | derived | informational | derived | none critical | keep derived + show |
| monthly production | PVsyst fact (F) | PVsyst/Production | yes | `[month]_estimated_production_year_1` | yes | yes | points ladder | design points | unit (kWh vs MWh) | confirm unit §10 |
| annual production | PVsyst fact (F) | PVsyst/Production | yes | `estimated_production_year_1` | yes | yes | points ladder | design point | unit | confirm unit |
| P50 / P90 | PVsyst fact (F) | PVsyst/Production | yes | `p50_mwh` / `p90_mwh` | yes | yes | metadata | reporting | unit MWh | keep |
| equipment warranty | none | Warranty | stub | none | no | none | no row | reporting | no schema | §7 |

**Headline:** the five physics inputs `thermal_coefficient_pct`,
`power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`,
`cec_efficiency_pct` have **no governed fact source at all today** — they exist
only as physics inputs filled by reviewer entry outside the fact/reconciliation
spine. This matches Root Cause B in `expected_baseline_readiness_input_audit.md`.

---

## 10. Unit & Normalization Policy (Section I)

### 10.1 Invariants
The system must persist, for every value that carries a unit: raw extracted value,
raw unit, normalized candidate value, normalized unit, normalization method,
reviewer confirmation flag, source evidence, timestamp, user, and override reason
if changed. Today `document_keys`/`project_facts` carry value/override/evidence/
reason/user/time but **do not carry an explicit raw-unit / normalized-unit /
normalization-method triplet** — that is the main schema extension this policy
needs (open item §16).

### 10.2 Per-unit policy

| Unit class | Examples | Safe same-unit strip (suggest) | Conversion (reviewer-confirmed only) | Ambiguity → review |
|---|---|---|---|---|
| Power (DC module) | `W`, `Wp` | strip to number (W) | `kW/kWp` → ×1000 | bare number with no unit on a kW-magnitude value |
| Power (AC inverter) | `kW`, `kWac` | strip to number (kW) | `W/Wac` → ×0.001 | `W` value that could be per-unit vs total |
| Energy | `kWh`, `MWh` | strip to number | `MWh` → ×1000 (kWh) | specific-yield check < 50 ⇒ likely MWh; **never auto-convert** |
| Percent | `%` | strip `%` | none | sign on tolerance/thermal coeff |
| Temp coefficient | `%/°C`, `%/°F` | strip to number keeping basis | **°C↔°F basis change requires confirm** | unit basis absent |
| Temperature | `°C`, `°F` | none | `°F`↔`°C` confirm | basis absent |
| Voltage / Current | `V`, `A` | strip | none | — |
| Irradiance | `kWh/m²`, `W/m²` | strip keeping basis | basis change confirm | plane/basis unknown (W0: stays `unknown`) |

### 10.3 Hard rules
- Safe same-unit stripping may be **suggested** but never silently applied to an
  accepted value or a `project_fact`.
- Any conversion (kW↔W, MWh↔kWh, °F↔°C) requires **explicit reviewer
  confirmation**.
- Ambiguous/unknown units **must route to review**, never a guess.
- A reviewer override must **retain the original raw value and raw unit**.
- No normalization may mutate an existing accepted value or active fact in place;
  a change creates new lineage / supersession (durable invariant §1).
- Weather semantics (irradiance plane, temperature type) follow the W0 rule:
  default `unknown`, never assume POA/cell (out of scope to change here).

---

## 11. Data Room Parsed-Document UX (Section J)

The equipment parsed-document view must support, per field:
- document classification display **and correction** (with re-parse implications);
- raw extracted value; source evidence (page/table/snippet); confidence; raw unit;
  normalized suggestion **where safe** (never auto-applied);
- baseline-driving indicator; operational/reporting impact indicator;
- **accept as-is**; **override/correct in field**; override reason + source note;
  reviewer identity + timestamp;
- task creation/escalation; stale/reparse state; promotion readiness;
- a **useful parse-failed / no-fields / not-yet-parsed** state (the fix for the
  silent empty in §2).

For an overridden value, the UI must show: extracted source value, reviewer
value, reason, evidence/source note, user+timestamp, promotion status — keeping
reviewer values **visibly distinct** from source-extracted values.

Explicit states the equipment view must render (currently the empty case is
silent):
1. **Not yet parsed** — file uploaded, no run → "Parse this document" CTA.
2. **Parsing in progress** — queued/running run.
3. **Parse failed (technical)** — run with error → reason + retry.
4. **Parsed, no usable fields** — completed run, zero mapped equipment fields →
   "This document type has no equipment schema / no equipment fields were found."
5. **Wrong document type for content** — heuristic mismatch (e.g., contractual
   fields on a datasheet) → suggest correcting type.
6. **Parsed, awaiting review** — extracted values present, not accepted.
7. **Accepted / overridden / promoted** — normal ladder.

---

## 12. Reconciliation UX (Section K)

Reconciliation should express these source-aware states (extends the existing
ladder; remains strictly read-only):
- source document **missing**;
- document uploaded but **wrong type**;
- **parse failed**;
- **parsed but no usable fields**;
- parsed value **awaiting review**;
- **accepted source-backed** value;
- **source-backed overridden** value (distinct chip);
- **reviewer-supplied assumption** (distinct chip — no source existed);
- accepted **not promoted**;
- **active fact**;
- active fact **but not baseline-usable** (e.g., non-numeric / unit unconfirmed);
- **normalization required**;
- **stale after reparse**;
- **baseline-ready**;
- source-backed value **superseded by reviewer override**.

These map cleanly onto the current status ladder + blocking levels
(`blocks_baseline`/`blocks_expected`/`blocks_reporting`/`lowers_confidence`/
`informational`); the additions are mostly new **provenance/source chips** and
precise `required_action` captions, plus rows for the five physics fields once
they become canonical (§9). No new truth store; no recomputation; no SAFL source.

---

## 13. Parser Intelligence Requirements (Section L)

For every specialized equipment parser:
- explain the **document purpose** to the model (e.g., "this is a PV module
  datasheet; extract electrical/thermal specifications");
- list **app-critical fields and why they matter** (baseline-driving vs
  informational);
- extract **raw text first**, then **extract the unit separately**;
- return a **normalized candidate only when safe** (else raw only);
- identify **table/page/evidence** for each value;
- return **confidence**;
- return **`not_found` explicitly**, and **distinguish unclear from absent**;
- **never infer equipment specs from contracts** or unrelated documents;
- **never hallucinate** missing values (remove the current prompt's "best guess at
  where it might appear" instruction for equipment schemas — it invites
  fabrication);
- **never auto-activate** a source value.

Additional intelligence needs surfaced by this audit:
- **Table/figure awareness**: datasheets are spec tables; plain-text extraction
  loses structure. Evaluate table-aware text extraction or vision input.
- **Multi-variant datasheets**: one PDF may list several SKUs/wattage bins
  (e.g., 405–415, 330–350) — the parser must surface the **variant** and the
  reviewer must select the installed one (never auto-pick).
- **Model selection**: confirm the active integration model is actually used and
  appropriate; reconcile the template `model_name` vs the Replit AI Integration
  default (§16).

---

## 14. Phased Implementation Roadmap (Section M)

Each phase is independently shippable; risk, likely files, tests, non-goals,
dependencies listed. **No production code in this sprint** — this is the proposed
plan for *future* approved sprints.

### Phase 1 — Failed-parse visibility & classification correction
- **Risk:** low. **Backend:** `files_parsing.py`, `in_app_parsing_service.py`
  (surface states), reconciliation service (states). **Frontend:** Data Room
  parsed-document panel, Reconciliation cells. **Config:** none. **Tests:**
  not-parsed / failed / no-fields render; no silent empty. **Non-goals:** new
  schemas. **Deps:** none. *Kills the silent empty (the #1 user-facing issue).*

### Phase 2 — Module Datasheet type + extraction schema
- **Risk:** med. **Backend:** new `canonical_fields` rows, schema version + fields
  for `module_specs`, equipment prompt template. **Frontend:** equipment field
  rendering. **Config/registry:** seeder for module schema (must **not** clobber
  the 17 specialized types — dedupe by normalized name). **Tests:** module
  datasheet classified+parsed; raw+unit+evidence+confidence+`not_found`; no
  hallucination. **Non-goals:** inverter, warranty. **Deps:** Phase 1.

### Phase 3 — Inverter Datasheet type + extraction schema
- **Risk:** med. Mirrors Phase 2 for `inverter_specs`; **kW AC** labeling for
  `inverter_ac_power_kw`. **Tests:** inverter parsed; W↔kW normalization
  suggested+confirmed, never silent. **Deps:** Phase 1 (Phase 2 patterns).

### Phase 4 — Data Room equipment review/override/normalization UX
- **Risk:** med. **Frontend:** raw unit, safe-normalization suggestion, baseline
  indicator, override w/ reason, four-way provenance display. **Backend:** raw-
  unit/normalized-unit/method persistence (schema extension §10/§16). **Tests:**
  accept; override retains raw; normalization requires confirm. **Deps:** 2–3.

### Phase 5 — Warranty/degradation extraction support
- **Risk:** med (prose ambiguity). **Backend:** warranty schema + degradation
  canonical fields + derived-candidate flag. **Tests:** no derivation from
  ambiguous prose without confirm; original wording preserved. **Deps:** 4.

### Phase 6 — PTO/interconnection canonical alignment
- **Risk:** med (touches a baseline gate). **Backend:** PTO schema; `pto_date`
  canonical truth + confirmed aliases; optional fact-backed bridge for PTO.
  **Tests:** promoted PTO reaches readiness; alias→`pto_date` only with confirm;
  hard-gate semantics preserved. **Deps:** 1, 4. **Non-goals:** changing
  suppression behavior.

### Phase 7 — Canonical field & Reconciliation coverage expansion
- **Risk:** med. **Backend:** new rows for the five physics fields (§9);
  reconciliation rows + states (§12). **Tests:** new rows show correct ladder +
  blocking level. **Deps:** 2–6.

### Phase 8 — Source-backed Baseline Readiness integration
- **Risk:** higher (feeds physics). **Backend:** bridge maps newly-canonical
  physics fields from facts (without changing the formula math). **Tests:**
  promoted source-backed physics fields recognized; non-numeric/unconfirmed
  blocks. **Non-goals:** expected-math changes, auto-baseline/auto-activate.
  **Deps:** 7.

### Phase 9 — Parser failure / no-fields UX hardening
- **Risk:** low. Polish of Phase 1 states across all equipment types + telemetry
  on parse outcomes. **Deps:** 1–8.

### Phase 10 — Test suite, fixtures, documentation
- **Risk:** low. Golden-file datasheet fixtures (Q CELLS, AXIpremium, an inverter
  sheet), end-to-end governance tests, docs. **Deps:** all.

Cross-phase non-goals (all phases): no BigQuery/Firestore/legacy paths; no SAFL as
baseline source; no auto-accept/override/promote/baseline/activate; no mutation of
existing facts/accepted values; no expected-math change; no telemetry ingestion /
rollup / WeatherResolver / device-eligibility / baseline-lifecycle change.

---

## 15. Test Plan (Section N)

Design (not yet implemented) tests:
1. Module datasheet correctly classified (manual type) and parsed to equipment
   fields.
2. Inverter datasheet correctly classified and parsed; `inverter_ac_power_kw`
   labeled kW AC.
3. Parser returns raw value, raw unit, evidence (page/table/snippet), confidence,
   and explicit `not_found`; distinguishes unclear vs absent.
4. **No hallucinated values** — absent fields are `not_found`, never invented;
   "best guess location" prompt removed for equipment.
5. Table/specification layout handled, or **fails visibly** (no silent empty).
6. Data Room shows source-backed parsed values with all provenance.
7. User can **accept** a source value.
8. User can **override** with an audit record (reason/source/user/time).
9. Override **retains the original extracted value + raw unit**.
10. Task creation retains document/field context.
11. Accepted/overridden values become candidates **only** through the existing
    governed flow.
12. Promotion creates active facts **only after review** (freshness guard honored;
    `PROMOTION_SOURCE_STALE` on stale basis).
13. Reconciliation reflects a source-backed overridden value (distinct chip).
14. Baseline Readiness recognizes promoted source-backed physics values; blocks
    on non-numeric/unconfirmed units.
15. Reparse marks prior acceptance/override lineage **stale** as designed.
16. **No SAFL source**; **no BigQuery/Firestore/legacy** path; **no auto-baseline /
    auto-activation** anywhere in the flow.
17. Unit policy: kW↔W and MWh↔kWh conversions require reviewer confirmation;
    same-unit strip is only suggested.
18. PTO alias (`permission_to_operate`/`cod`) normalizes to `pto_date` only with
    confirmation and then reaches readiness.
19. Architect review of the implementation sprint(s).

Fixtures: the two real datasheets already in the system (Q CELLS Q.PEAK DUO L-G8.3
405–415; AXIpremium 72c 330–350) plus at least one inverter datasheet, as golden
files for deterministic parse/governance tests.

---

## 16. Open Decisions for the User

1. **Make `pto_date` fact-backed?** Recommended (so a promoted PTO fact reaches
   readiness without a separate reviewer-supplied step), while preserving the
   hard-gate suppression. Confirm.
2. **Five physics fields as canonical/fact-backed** (`thermal_coefficient_pct`,
   `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`,
   `cec_efficiency_pct`): adopt as governed canonical fields (recommended) vs keep
   as reviewer-only inputs. Confirm.
3. **Unit metadata schema extension:** add explicit `raw_unit`,
   `normalized_unit`, `normalization_method` (+ a derived-candidate flag for §7)
   to `document_keys`/`project_facts`. Confirm scope (additive, nullable).
4. **Document classifier:** add a type *suggestion* on upload (never auto-commit)
   vs remain manual-only. Confirm appetite.
5. **Table/vision extraction:** approve evaluating table-aware extraction (or
   vision input) for datasheets, since plain-text loses spec tables.
6. **Model alignment:** confirm whether the active integration model (Replit AI /
   OpenAI) should be used and whether the template `model_name`
   (`claude-sonnet-4-5`) is intended; align template vs runtime.
7. **MV loss field duplication:** `medium_voltage_loss_pct` vs `mv_line_loss_pct`
   — consolidate to one canonical field? Confirm.
8. **Blanket registry remediation:** should the 201 contractual-stub types be
   re-scoped over time (mark non-equipment types appropriately) or left as-is and
   addressed type-by-type? Confirm strategy.
9. **Orphan parse runs** (5 rows with `NULL document_type_id`, all non-completed):
   investigate/clean up as a separate hygiene item? Confirm.

---

## Appendix A — Full Registry Enumeration (all 218 document types)

This appendix completes §3 by accounting for **every** registered document type
(not a representative sample), derived directly from the live registry. Types are
grouped by their **active schema family** (identical canonical fieldset). All 218
types are `is_parsable = true`, `is_active = true`, and have an active prompt
template.

### A.1 Schema families (every type belongs to exactly one)

| Schema family | Field count | Member types | Purpose-built? | Equipment-relevant members trapped here |
|---|---|---|---|---|
| **Generic contractual stub** (`document_title, document_date, counterparties, effective_date, expiration_or_termination_date, term_or_duration, key_obligations, key_amounts_or_fees, governing_law_or_jurisdiction, summary`) | 10 | **201** | ⚠️ **No** | **Module Specs, Inverter Specs, Transformer Specs, Storage Specs, Battery Specs, Racking Specs**, all `*_warranty` + `*_warranty_backup_documents` (module/inverter/transformer/storage/racking/battery), **Permission to Operate (PTO)**, **Commercial Operation Date (COD)**, Net Metering / Interconnection Application, Interconnection 25%/75%, Monitoring System and DAS, Final PV Syst Reports Average, Financial Model, Financial Projections, and ~170 contractual/closing/permit/draw docs |
| PVsyst design-estimate | 47 | 4 | ✅ Yes | PV Syst – As Built (Second Buyer), Independent (Seller), Initial Package (Seller), IFC (First Buyer) |
| Operating Agreement | 8 | 4 | ✅ Yes | Operating Agreement (all variants incl. pre/post tax equity, original) |
| Loan / Security Agreement | 14 | 2 | ✅ Yes | Construction Loan Security Agreement, Permanent Loan Security Agreement |
| O&M / Production Guarantee | 34 | 1 | ✅ Yes | Operations and Maintenance (O&M) & Production Guarantee Agreement |
| Site Lease | 37 | 1 | ✅ Yes | Site Lease |
| EPC Agreement | 56 | 1 | ✅ Yes | Engineering, Procurement, Construction (EPC) Agreement |
| PPA | 28 | 1 | ✅ Yes | PPA – Power Purchase Agreement |
| Interconnection Agreement | 27 | 1 | ✅ Yes | Interconnection Agreement and Amendments |
| Subscriber Management | 7 | 1 | ✅ Yes | Subscriber Management Agreement |
| Phase 1 ESA | 5 | 1 | ✅ Yes | Phase 1 ESA |

**Totals:** 218 types across 11 schema families. **17 types** have purpose-built
schemas (PVsyst×4, Operating Agreement×4, Loan×2, O&M×1, Site Lease×1, EPC×1,
PPA×1, Interconnection×1, Subscriber Mgmt×1, Phase 1 ESA×1); **201 types** share
the single generic contractual stub. **Zero** equipment-datasheet schemas exist.

### A.2 Prompt families
All equipment types (and the entire 201-type contractual family) use the **single
generic "document extraction specialist" prompt template** (system prompt ~596
chars, extraction prompt ~680 chars, `{{FIELD_LIST}}`/`{{DOC_TYPE}}`/
`{{DOCUMENT_TEXT}}` placeholders, `model_name = claude-sonnet-4-5`). The
specialized schema families pair with their own field lists but the same prompt
scaffold. There is **no equipment-aware prompt** anywhere today.

### A.3 Parse-run usage (live)
Runs have only ever fired for contractual/PVsyst types:

| Doc type | Runs | Completed | Non-completed |
|---|---|---|---|
| `site_lease` | 12 | 5 | 7 |
| `pv_syst_as_built_second_buyer_report` | 6 | 1 | 5 |
| `phase_1_esa` | 4 | 0 | 4 |
| `pv_syst_initial_package_for_modeling_seller` | 4 | 4 | 0 |
| `operating_agreement_including_all_amendments_pretax_equity` | 4 | 0 | 4 |
| `engineering_procurement_construction_epc_agreement` | 3 | 0 | 3 |
| *(NULL document_type_id — orphan)* | 5 | 0 | 5 |

`module_specs` and `inverter_specs`: **0 runs ever** — consistent with §2 (the two
uploaded module datasheets were never parsed).

### A.4 Complete member list of the 201-type contractual-stub family
For full enumeration (alphabetical): 10% K1; 12 months of Utility Bills; 20%
Funding; 3rd Party Review - Final Acceptance; 70% Funding; ALTA Survey; Air;
Application for Building Permit; Application for Electrical Permit; Application for
Encroachment / Driveway Access Permit; Articles of Organization; As Built Project
Drawings; As-Built ALTA Survey; Assignment of Interconnection Agreement and
Amendments; Assignment of Membership Interests; Assignment of PPA to ProjectCo;
Assignment of Site Lease to ProjectCo (Lessor); Assignment of Warranties;
**Battery Specs**; Battery Warranty; Battery Warranty Backup Documents; Bond
Rating or other Third Party Financial Review; Building Permit; CESIR; CRA
(Community Reinvestment Act); Certificate of Good Standing; Change Order Requests;
**Commercial Operation Date (COD)**; Community Solar Program Participation; Consent
to Assignment of EPC; Consent to Assignment of O&M; Consent to Assignment of
Offtaker; Construction & Demolition Debris; Construction Lien Releases;
Construction Loan Guaranty; Construction Prom Note; Construction Stormwater;
Current Progress Report / Construction % Complete; Date of Investor Closing;
Decommissioning Bonds; Deliverables at Closing; Documents Evidencing Title
Exceptions; Draw #1–#20; EPA Greenhouse Gas Equivalencies Calculator; EPC Closeout
Documents; EPC Final Completion/Acceptance Report/Certificate; EPC Mechanical
Completion Report/Certificate; EPC Permit & Studies Letter; EPC Production
Guaranty; EPC Substantial Completion Report/Certificate; EPC's Insurance
(Liability & Builders Risk); ESG Statement; Electrical Permit; Employer
Identification Number (W-9 or IRS Letter); Encroachment / Driveway Access Permit;
**Endangered Species**; Enforceability Opinion; Environmental Reports; Evidence of
Application for Municipal Permits; Evidence of Initial Payment; Executive Summary;
FAA Obstruction Evaluation / Airport Airspace Analysis; FEMA (Disaster Declaration
Y/N); FERC 556; FIRPTA; Final Completion/Acceptance; Final Construction Lien
Releases; **Final PV Syst Reports Average**; Final Title Policy; **Financial
Model**; Financial Projections (Project Life); Financials and Tax Returns (3
years); Flow of Funds; Forbearance Agreement; Formal Notice of Commencement of
Lease; Full Notice to Proceed; Fully Executed Racking Warranty; GeoTechnical
Report; Guaranty Agreement; IDA; IFC (Issued for Construction) Stamped Project
Drawings; Incumbency Certificate & Resolutions; Independent Engineer Report;
Insurance Companies are A rated or better; Interconnection 25%; Interconnection
75%; **Inverter Specs**; **Inverter Warranty**; **Inverter Warranty Backup
Documents**; Leasehold Area Metes and Bounds Legal Description; Loan Maturity Date;
Local Building Permits; MIPA Assignment Agreement; MIPA to Lessee HoldCo;
Member/Officer Resignations; **Module Specs**; **Module Warranty**; **Module
Warranty Backup Documents**; **Monitoring System and DAS**; NMTC; NYSDAM NOI Final
Determination; NYSEG 100%/25%/75% Payment; NYSERDA Grant; NYSERDA Grant Status;
Net Metering / Interconnection Application; O&M Insurance; OFE Proof of
Procurement; Offtaker; Opinions; Org Chart (Before & After Investment); PPA
Estoppel; Payoff Letters; Permanent Loan Guaranty; Permanent Promissory Note;
**Permission to Operate (PTO)**; Phase 1 ESA Reliance Letter; Phase 2 ESA; Photos
of Completed Project; Placed in Service (PIS) Letter; Pledge Agreement;
Pre-Appraisal Data Check; Preliminary Drawings for Model – Civil; Preliminary
Drawings for Model – Electrical; Preliminary IE Review for Model; Pro Forma Title
Policy; Production Based Incentive (PBI) Approval; Project Appraisal; Project
Budget and Draws Requests; Project Preview; Project Schedule; ProjectCo Invoices;
ProjectCo's Business Interruption / Liability / Property Insurance; Proof of Legal
Name; Proof of ProjectCo Ownership (+ AMIPA/PMIPA variants); Proof of Start of
Construction; Property Tax Agreements; Purchase Option; **Racking Specs**; Racking
Warranty; Racking Warranty Backup Documents; Real Estate Owner's/Landlord's
Insurance; Recorded Memorandum of Site Lease & Assignments; SNDAs, Lien Releases,
and Waivers; SREC Approval; SREC Contracts or Proof of Ability to Merchandise;
Seller Acceptance of Second Buyer PV Syst Report; Seller Certificate per 3(b)(v);
Servicer's Statement of Qualifications; Servicing Agreement; Site Assessment; Site
Lease Estoppel for Benefit of Investor; Sources and Uses; Statement of
Qualifications; **Storage Specs**; Storage Warranty; Storage Warranty Backup
Documents; Term Sheet for Permanent Financing; Third Party Invoices; Title Report /
Title Commitment; **Transformer Specs**; Transformer Warranty; Transformer
Warranty Backup Documents; UCC Financing Statements (Construction/Permanent); UCC
Terminations; UCC/Tax/Bankruptcy/Judgment & Pending Litigation Searches; UCC3
Release or Termination; USDA / REAP; USDA Pre-Cert Checklist; USFWS Concurrence
Letter; Utility Approval of Assignment of Interconnection Agreement; Utility/City
Mechanical Completion Tests; Wetlands; Wire Instructions; Zoning Approval /
Conditional Use Permit; i39 Approval.

**Bolded** members above are the equipment/telemetry/PTO/design types whose
operational intelligence is currently lost to the contractual stub — the direct
remediation targets of §4–§9.

---

*End of audit/design. No production code, schema, registry, or data changes were
made in this sprint.*
