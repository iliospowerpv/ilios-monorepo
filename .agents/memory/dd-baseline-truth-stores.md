---
name: Due-diligence ↔ expected-baseline truth-store disconnect
description: How parsed DD facts, project_facts, site_additional_fields, BigQuery characteristics, and telemetry_expected_baselines (dis)connect today — the gap the DD V2 upgrade must close.
---

# DD parsing ↔ expected-baseline data flow (current reality)

There are THREE partially-connected "truth" stores, plus a live legacy BQ write:

1. `site_additional_fields` (`SiteAdditionalFieldList`, models/site.py) — legacy flattened
   site characteristics (dc/ac/mv losses, permission_to_operate, system sizes).
2. `project_facts` (`ProjectFact`, candidate/active/retired) — the newer canonical fact
   store. DD writes candidates here on accept/override.
3. `telemetry_expected_baselines` (+ `telemetry_expected_baseline_points`) — V2 physics
   snapshot baseline.

**Key disconnects (verified, not obvious from any single file):**
- The DD key-edit handler (`routers/due_diligence/documents.py`) does TWO things on a key
  change: (a) when the doc is `as_built_pv_syst_with_full_data_package` and the key is in
  `DueDiligenceBQKeys`, it STILL writes BigQuery characteristics via
  `SiteDDCharacteristicsHandler(site).sync_to_bq(...)` (live legacy write, on the prior
  sprint's KEEP list); (b) on accepted/overridden keys it creates a candidate `ProjectFact`
  via `ProjectFactsService.create_candidate_from_document_key`.
- Baseline `create_draft` (crud/telemetry_expected.py) snapshots loss%/PTO/timezone from
  `SiteAdditionalFieldList` — **NOT** from `project_facts` and **NOT** from documents. It is
  invoked only from the telemetry V2 router (`routers/telemetry/v2.py`), never from the DD
  flow. So promoting a ProjectFact does NOT feed the baseline; the baseline reads the legacy
  site table.
- `source_type='diligence_ai_parse'`, `source_project_fact_id`, `source_document_id` columns
  on `TelemetryExpectedBaseline` are MODELED BUT HAVE ZERO PRODUCERS — provenance bridge
  unbuilt.
- `TelemetryExpectedBaselinePoint` has ZERO producers — monthly/annual/8760 → points is
  unbuilt; `weather_adjusted_model` computes expected on-read from snapshot columns + live
  irradiance/temp instead.
- `ilios-DocAI` (the external PVsyst CSV-instruction parser, `pv-syst/terms-instructions.csv`)
  is NOT referenced anywhere in `ilios-server` — it's the old offline pipeline. The live
  in-app parser (`InAppParsingService` + the DB `extraction_registry`) extracts generic
  document keys and has NO PVsyst physics field schema wired.

**Why this matters:** the DD V2 upgrade's job is to route parsed/PVsyst facts →
`project_facts` (with provenance + confidence) → on accept, populate a baseline DRAFT
(`source_type=diligence_ai_parse`, `source_project_fact_id`) instead of the legacy
`site_additional_fields` path, and eventually retire the DD→BigQuery characteristics write.
