---
name: Due-diligence ↔ expected-baseline truth-store disconnect
description: How parsed DD facts, project_facts, site_additional_fields, BigQuery characteristics, and telemetry_expected_baselines (dis)connect — and what DD V2 Phase 1 changed vs what Phase 2 still must close.
---

# DD parsing ↔ expected-baseline data flow

There are THREE partially-connected "truth" stores, plus a (now-gated) legacy BQ write:

1. `site_additional_fields` (`SiteAdditionalFieldList`, models/site.py) — legacy flattened
   site characteristics (dc/ac/mv losses, permission_to_operate, system sizes).
2. `project_facts` (`ProjectFact`, candidate/active/retired) — the newer canonical fact
   store. DD writes candidates here on accept/override.
3. `telemetry_expected_baselines` (+ `telemetry_expected_baseline_points`) — V2 physics
   snapshot baseline.

## What DD V2 Phase 1 changed
- **DD→BigQuery characteristics write is now gated behind `legacy_telemetry_enabled` AND wrapped non-blocking** (Phase 1E). It is NOT removed (Phase 2 removal target). When the flag is off it no-ops; failures never block DD review/promotion.
- `project_facts` gained additive nullable provenance/audit columns (evidence JSONB, ai_confidence, ai_extracted_value, accepted/overridden by/at, override_notes, effective_from/to, `superseded_by_fact_id`). `create_candidate_from_document_key` now threads provenance in both create and update branches; `retire_active_fact` sets the retired fact's `superseded_by_fact_id` (leaves legacy `supersedes_fact_id` intact for summary_stats.py).
- **In-app parser coverage broadened**: every `SiteDocumentsEnum` doc type is now parse-eligible (generic schema/prompt), and the As-Built (Second Buyer) PVsyst report has a specialized v2 schema marking the 16 `DueDiligenceBQKeys` baseline-driving fields required. See `dd-v2-extraction-registry-seeding.md`.

## Key disconnects that REMAIN (Phase 2 work)
- Baseline `create_draft` (crud/telemetry_expected.py) still snapshots loss%/PTO/timezone from
  `SiteAdditionalFieldList` — **NOT** from `project_facts`, **NOT** from documents — and is invoked
  only from the telemetry V2 router, never from the DD flow. Promoting a ProjectFact still does NOT
  feed the baseline. NO baselines are auto-created/activated by DD (by design).
- `source_type='diligence_ai_parse'`, `source_project_fact_id`, `source_document_id` on
  `TelemetryExpectedBaseline` are MODELED BUT HAVE ZERO PRODUCERS — provenance bridge unbuilt.
- `TelemetryExpectedBaselinePoint` has ZERO producers — monthly/annual/8760 → points unbuilt;
  `weather_adjusted_model` computes expected on-read from snapshot columns + live irradiance/temp.
- `ilios-DocAI` (external PVsyst CSV-instruction parser) is offline / unreferenced in `ilios-server`.

**Phase 2 job:** route accepted/promoted PVsyst facts → a baseline DRAFT
(`source_type=diligence_ai_parse`, `source_project_fact_id`) instead of the legacy
`site_additional_fields` path, build the baseline-point producers, then retire the DD→BigQuery write.
