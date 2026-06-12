---
name: Due-diligence ↔ expected-baseline truth-store disconnect
description: How parsed DD facts, project_facts, site_additional_fields, BigQuery characteristics, and telemetry_expected_baselines (dis)connect, and the facts→draft-baseline bridge (Phase 2) that now joins project_facts to baselines.
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

## facts→draft-baseline bridge (Phase 2 — BUILT)
A SECOND, side-by-side producer now turns promoted `project_facts` into a baseline DRAFT,
**without** repointing or touching the legacy `create_draft` snapshot path:
- It reads ONLY `project_facts` (active/promoted) for module/inverter physics and calls
  `create_draft(site_additional=None)` so the legacy `SiteAdditionalFieldList` snapshot NEVER fires.
  Reviewer supplies the 5 datasheet constants (thermal coeff, power-tolerance-min, yr1 + annual
  degradation, CEC eff) that have no fact source — via the create request body, tracked as
  `reviewer_supplied`.
- **Honesty contract:** required physics field missing or non-numeric ⇒ BLOCK (no row written) +
  honest `missing_fields`; defaults are NEVER fabricated. Optional losses/soiling/PTO absent ⇒ warning only.
- **Draft-only / never overwrite:** always inserts `status=draft`; never approve/activate; an existing
  ACTIVE baseline is left untouched. Idempotency is scoped to `status=draft` only (a promoted/approved
  baseline with the same signature is NOT short-circuited).
- **Provenance now produced:** `source_type=diligence_ai_parse`, `source_project_fact_id` (module_wattage
  fact), per-field `model_parameters_json['field_sources']`, `ai_confidence_json`, and a content
  signature; `source_document_id` is set ONLY when exactly one contributing document resolves (else null).
- **Unit hazard preserved:** module_wattage is W, inverter_wattage is kW — RAW values surfaced, plausibility
  warning, never auto-converted.
- 422 "review_required" must be returned as the structured response model with `response.status_code=422`,
  NOT a raised `HTTPException` — the app's global handler flattens `HTTPException.detail` to a string,
  which would destroy machine-readable `missing_fields`.

## Key disconnects that REMAIN
- The legacy `create_draft` SAFL-snapshot path still exists side-by-side (intentionally kept; not repointed).
- `TelemetryExpectedBaselinePoint` still has ZERO producers — monthly/annual/8760 → points unbuilt;
  `weather_adjusted_model` computes expected on-read from snapshot columns + live irradiance/temp.
- DD→BigQuery characteristics write is still gated behind `legacy_telemetry_enabled` (Phase-2 removal target,
  not yet retired).
- `ilios-DocAI` (external PVsyst CSV-instruction parser) is offline / unreferenced in `ilios-server`.
- `_next_version` is read-then-insert with no unique constraint on (site, type, version) — concurrent
  create could duplicate a version number (acceptable for an admin-triggered action; future constraint).
