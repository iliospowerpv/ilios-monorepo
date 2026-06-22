# Phase 2 — Module Datasheet Schema, Equipment-Aware Parsing & Governed Review

**Scope:** `module_specs` document type ONLY.
**Goal:** Replace the generic 10-field contractual stub previously assigned to `module_specs`
with a specialized **Module Datasheet** schema plus an equipment-aware extraction prompt, routed
through the **existing** governed Due-Diligence workflow
(parse → review → accept/override → candidate fact → freshness guard → reconciliation).

This sprint is **additive and read-only with respect to governance**. It changes no baseline math,
no truth-store semantics, no WeatherResolver, no device-eligibility classifier, no SAFL, no
BigQuery/Firestore paths, and does not touch the `Site` entity.

---

## 1. Confirmed decisions (user-approved)

- **`module_wattage` is the single canonical field** for per-module STC / nameplate power
  (unit: W per module). In the Module Datasheet context its UI label is
  **"Module Nameplate Power at STC"**. A parser display alias may appear in parsed metadata only,
  but it MUST map to `module_wattage` before any DocumentKey / candidate fact is written.
  **`module_power_stc_w` was deliberately NOT created.**
- **Multi-variant (multi-SKU) datasheets** preserve **ALL** variants in metadata, mark the field
  `status = ambiguous`, do **not** auto-populate an accepted/candidate value, create **no**
  competing candidate facts, and require an explicit reviewer selection/override before acceptance.
  Range evidence and the reviewer's chosen value/reason are preserved.
- **`is_required` is a parse/review requirement only.** A parse is **never** failed because an
  optional spec (e.g. degradation) is absent. Absent → `not_found`; present-but-unclear →
  `unclear`/`ambiguous`; never a hallucinated substitute.
- **Non-current versions:** fixtures are parsed WITHOUT being marked current. Acceptance / override /
  candidate / promotion / stale-protection all remain file-version-scoped, and the UI visibly
  indicates a source-not-current version.
- **Physics fields** (`thermal_coefficient_pct`, `power_tolerance_min_pct`, `power_tolerance_max_pct`,
  `year_1_degradation_pct`, `annual_degradation_pct`) are added to the schema/reconciliation catalog
  but are **NOT** added to `BASELINE_DRIVING_FACT_FIELDS`, `FACT_FIELD_TO_COLUMN`,
  baseline-from-facts mappings, baseline creation defaults, or any expected calc.
- **Minimal additive metadata:** preserve raw value + unit; carry evidence/confidence/status/variants
  in parse-result metadata; additive optional schema fields only; no historical rewrite; **no silent
  unit/% conversion.**

---

## 2. What changed (P1–P5)

### P1 — Canonical fields + `module_specs` registry version
- Added the missing Module Datasheet canonical fields (efficiency, thermal coefficient, power
  tolerance min/max, year-1 & annual degradation, Voc/Isc/Vmp/Imp, NOCT, dimensions, product
  warranty years).
- One additive nullable `expected_unit` column on `canonical_fields`.
- Created and **activated** a new `module_specs` `ExtractionSchemaVersion` (id **220**, **18 fields**
  with `is_required` + `priority`) and an equipment-aware `ExtractionPromptTemplate` via the existing
  CRUD. The generic stub (schema version id **125**, 10 fields) is preserved as inactive history.
- Verified: the active config for `module_specs` resolves to the specialized schema via
  `ExtractionPipelineService`; generic stub rows are untouched; no other document type changed.

### P2 — Equipment-aware prompt + richer parse output
- Authored the module prompt: emit raw value + unit, evidence (page / table-or-section / snippet /
  anchor), confidence, and `not_found` / `unclear` semantics; for multi-variant sheets list **ALL**
  variants and **never** pick or convert.
- Extended parser handling + the `parsed_result` JSON so each field carries
  `raw_value` / `raw_unit` / `evidence` / `confidence` / `status` / `variants`.
- Verified `combine_user_ai_parsing_results` + the OpenAI JSON parsing preserve the nested
  variants/status unchanged; the `module_wattage` alias maps correctly; no auto-candidate is created
  for an ambiguous field.

### P3 — Additive review UI
- Extended `DocumentModal` / `CollapsibleDocumentTermRenderer` / `DocumentTermUserInputField` to show
  raw value/unit, evidence, confidence, status badges, and multi-variant selection while retaining
  the accept/override/task actions and the server-side override-rationale guardrail, and visibly
  flagging a non-current source version.
- An ambiguous field cannot be accepted without a reviewer choice. Frontend webpack reported
  "No issues found."

### P4 — Reconciliation catalog rows
- Added read-only catalog entries for the new module fields in
  `app/static/reconciliation_catalog.py` (17 Module Datasheet rows appended last, classified
  `EQUIPMENT` / `NONE`). Only `module_wattage` / `module_quantity` keep baseline targets; the physics
  fields get **no** baseline target and never enter `FACT_FIELD_TO_COLUMN`.
- Verified existing reconciliation rows are identical before/after; new rows render read-only.

### P5 — Tests
- New suite `tests/unit/due_diligence/module_datasheet_phase2_test.py` — **21 tests pass**. Coverage:
  - `MODULE_FIELDS` static guard (18 fields; `module_wattage` is the sole STC field; no
    `module_power_stc_w`).
  - Registry seeding versioning + idempotency.
  - Real `combine_user_ai_parsing_results` proving verbatim variant/unit passthrough, no auto-pick,
    and contractual back-compat.
  - `FileKeySchema` / `FileParsingEvidence` back-compat.
  - Reconciliation catalog: 17 read-only rows appended last.
  - Explicit identity guard: `BASELINE_DRIVING_FACT_FIELDS == {4}` and the baseline-from-facts
    mappings are unchanged.
- Parity suites pass: `test_extraction_registry` + `test_baseline_from_facts` (54),
  `reconciliation_test` (40).

---

## 3. P6 — Controlled parse (existing parse pipeline, no mark-current)

Both fixtures are **non-current** versions and were parsed through the existing parse pipeline only
— the script builds the same queued `ai_parsing_results` record the `POST /parsing/` endpoint creates
and then invokes the same `_run_parsing_background` background function (it bypasses only the HTTP
auth/permission/extension wrapper, not the parse/merge logic). Parsing writes **only** an
`ai_parsing_results` run; **no DocumentKeys and no candidate facts** are created until a reviewer
accepts in the Data Room. No version was marked current.

| Fixture | Site / Doc | Product | Run | Result |
|--------|-----------|---------|-----|--------|
| file 25 | Site 4 / doc 1113 | AXITEC AXIpremium 330–350 | 44 | **Completed** — 18 fields |
| file 17 | Site 1 / doc 207 | Q-CELLS Q.PEAK 405–415 | 43 | **Processing Failed** — environment blocker (see §4) |

### file 25 — full result (AXIpremium 330–350)

```
module_manufacturer        extracted   'AXITEC'            (single value, no variants)
module_model               ambiguous   value=None          5 variants (per SKU)
module_wattage         <<< ambiguous   value=None          5 variants  330/335/340/345/350 Wp
module_efficiency_pct      ambiguous   value=None          5 variants
voc                        ambiguous   value=None          5 variants
isc                        ambiguous   value=None          5 variants
vmp                        ambiguous   value=None          5 variants
imp                        ambiguous   value=None          5 variants
thermal_coefficient_pct    extracted   '-0.40' unit %/K    (raw value + unit preserved, NOT converted)
noct                       extracted   '45' unit °C +/-2K
power_tolerance_min_pct    not_found
power_tolerance_max_pct    not_found
year_1_degradation_pct     not_found
annual_degradation_pct     not_found
module_length_mm           extracted   '1956' mm
module_width_mm            extracted   '992' mm
module_area_m2             not_found
module_product_warranty_years  extracted  '12' years
```

**`module_wattage` persisted JSON (run 44), proving nested-metadata survival to the Data Room:**

```json
{
  "field_key": "module_wattage",
  "value": null,
  "raw_value": null,
  "raw_unit": null,
  "status": "ambiguous",
  "confidence": "high",
  "evidence": {
    "page": 2,
    "anchor_text": "Nominal output",
    "table_or_section": "Electrical data (STC) table",
    "snippet": "Type Nominal output\nAC-330M/156-72S 330 Wp ...\nAC-350M/156-72S 350 Wp ..."
  },
  "variants": [
    {"label": "AC-330M/156-72S", "raw_value": "330", "raw_unit": "Wp"},
    {"label": "AC-335M/156-72S", "raw_value": "335", "raw_unit": "Wp"},
    {"label": "AC-340M/156-72S", "raw_value": "340", "raw_unit": "Wp"},
    {"label": "AC-345M/156-72S", "raw_value": "345", "raw_unit": "Wp"},
    {"label": "AC-350M/156-72S", "raw_value": "350", "raw_unit": "Wp"}
  ]
}
```

### What file 25 validates

- **Wattage-range ambiguity surfaced:** `module_wattage` = `ambiguous`, `value`/`raw_value` = `null`,
  all 5 SKU variants preserved. The parser did **not** pick a value and created **no** candidate fact.
- **Units verbatim, no silent conversion:** `Wp`, `%/K`, `°C`, `mm`, `years` are carried exactly as
  printed; `thermal_coefficient_pct` is `-0.40` (raw), not coerced to a decimal fraction.
- **`module_wattage` is the sole STC nameplate field** — no `module_power_stc_w` appears.
- **Optional-absent ≠ failure:** the four tolerance/degradation fields and `module_area_m2` are
  `not_found`; the parse still **Completed** rather than failing, with no hallucinated substitute.
- **Single-value fields extract cleanly** (`module_manufacturer = AXITEC`) without spurious variants.
- **Nested metadata survives** parse → merge → persistence (the variants/evidence/status block above
  is read straight back out of the stored `parsed_result`).

### file 17 — blocked by environment (see §4)

Run 43 was recorded as `Processing Failed` with the honest error
`[text_extraction_failed] PDF text extraction failed: cryptography>=3.1 is required for AES algorithm`,
and **no** `parsed_result`, **no** DocumentKeys, and **no** candidate facts were written. This is the
correct governed behavior: a provider/extraction failure is recorded on the run without fabricating
data. The Q.PEAK 405–415 multi-variant shape is covered deterministically by the P5 suite.

---

## 4. Environment blockers discovered (pre-existing, NOT introduced by Phase 2)

These are environment/ops conditions in this Replit container, independent of the Phase 2 code:

1. **AES-encrypted PDFs cannot be text-extracted here.** `pypdf` needs either `cryptography` or
   `pycryptodome` for AES; **both are absent** and pypdf is on its `local_crypt_fallback` provider.
   Neither package can be installed in this container: the Nix store is immutable, `uv add` fails with
   a permission error, and `pip install --user` is disabled by PEP 668. file 17 is AES-encrypted, so
   its text extraction fails. (file 25 is not AES-encrypted and extracted normally.)
2. **The seeded prompt templates declare `model_name = "claude-sonnet-4-5"`**, which the current
   Replit AI gateway rejects with `UNSUPPORTED_MODEL`. This is **registry-wide** — essentially every
   auto-seeded template uses that model — **not** specific to the Phase 2 `module_specs` template. For
   this controlled validation run only, the script forced the gateway-supported default `gpt-5.2`
   **without mutating the seeded registry** (it only swaps which LLM backend answers, so the
   equipment-aware prompt, specialized schema, and full governed combine path are still exercised).
   `gpt-5.2` returned a valid response, confirming the prompt + schema work end-to-end.

Neither blocker is a Phase 2 defect. They are surfaced here so they can be addressed as ops/follow-up
work (provide an AES-capable crypto provider; align the registry default model with a
gateway-supported model).

---

## 5. Governance guarantees verified

- **Parse-without-current:** both fixtures stayed non-current; only `ai_parsing_results` runs were
  written; no DocumentKeys / candidate facts were created (acceptance still happens in the Data Room).
- **File-version scoping** for acceptance/override/candidate/promotion/stale-protection is unchanged.
- **No baseline/math/truth-store change:** `BASELINE_DRIVING_FACT_FIELDS == {4}` and the
  baseline-from-facts mappings are identity-guarded by P5; physics fields carry no baseline target.
- **`module_wattage` is the only STC nameplate fact** end-to-end (schema, parse, catalog, tests).
- **No incorrect auto-normalization or auto-candidate** was observed: ambiguous multi-variant fields
  produced `value = null` and zero candidate facts; raw units were preserved verbatim.
