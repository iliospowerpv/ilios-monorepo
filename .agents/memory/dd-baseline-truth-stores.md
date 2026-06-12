---
name: Due-diligence ↔ expected-baseline truth-store disconnect
description: How parsed DD facts, project_facts, site_additional_fields, BigQuery characteristics, and telemetry_expected_baselines (dis)connect, and the facts→draft-baseline bridge (Phase 2) that now joins project_facts to baselines.
---

# DD parsing ↔ expected-baseline data flow

There are THREE partially-connected "truth" stores (a legacy DD→BQ characteristics write also existed but was REMOVED in Phase 5B):

1. `site_additional_fields` (`SiteAdditionalFieldList`, models/site.py) — legacy flattened
   site characteristics (dc/ac/mv losses, permission_to_operate, system sizes).
2. `project_facts` (`ProjectFact`, candidate/active/retired) — the newer canonical fact
   store. DD writes candidates here on accept/override.
3. `telemetry_expected_baselines` (+ `telemetry_expected_baseline_points`) — V2 physics
   snapshot baseline.

## DD→BigQuery characteristics write — REMOVED (Phase 5B)
- The DD→BQ "characteristics" write was deleted from the active DD flow (`set_key`) along with all
  dead helpers (`SiteDDCharacteristicsHandler`, `document_key_sync_helper`, `DocumentKeyCRUD.get_document_keys_by_names`).
  It was originally (Phase 1E) only gated behind `legacy_telemetry_enabled` + non-blocking; now there is
  NO BigQuery path in the DD flow at all. DD term accept/override writes ONLY `project_facts` candidates.
- **Why:** BigQuery was declared non-operational for DD; the gated-but-present write was dead weight and a
  misleading "truth store". The separate device/site-card BQ sync (`SiteCharacteristicsHandler`) is a
  DIFFERENT concern and is intentionally kept.

## What DD V2 Phase 1 changed
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

## facts→baseline POINTS producer (design estimates)
A third producer turns a site's promoted/active PVsyst production `project_facts` into stored
`TelemetryExpectedBaselinePoint` rows (monthly + annual granularity ONLY), attached to an EXISTING
`draft`/`in_review` **`design_estimate`** baseline. Endpoints: GET `.../{baseline_id}/points-readiness`
(read-only) + POST `.../{baseline_id}/generate-design-points` (delete+rebuild).
- **Strict separation from the weather-adjusted curve:** this table is NEVER consulted by
  `weather_adjusted_model` (which still computes on-read from snapshot columns + live telemetry), so design
  points cannot perturb the live actual-vs-expected calc. The producer refuses any non-`design_estimate`
  baseline (409 / ValueError) so the two "expected" notions are never conflated.
- **Never fabricate:** absent month = partial (warning), present-but-unparseable value = hard parse error
  blocking the whole write (422 `malformed`); an annual total is NEVER distributed into months; no production
  facts at all = 422 `no_design_data`. Nothing is written unless ready.
- **Units stored as-extracted** into `expected_energy_kwh` (PVsyst monthly/annual facts carry no unit;
  `unit_verified=false` + MWh plausibility warnings, never auto-converted). GHI insolation and P50/P90
  scenarios CANNOT be represented by the single-value point row — they live in header
  `model_parameters_json['design_points']` metadata only (GHI never written to `irradiance_wm2`), with
  `schema_expansion_recommended`.
- **Reference year** anchors all points: precedence `pto_date.year` else site-local year of `created_at`
  (drafts have no `active_from`). Site-local first-of-month midnight → naive-UTC via
  `baseline.timezone`→`site.timezone`→UTC, matching how readings/rollups are stored.
- **Idempotent rebuild:** delete (scoped to monthly+annual granularities, so any future hourly/interval
  curve survives) → bulk insert → header JSON reassign, all in ONE txn (rollback on error). Immutable
  (`approved`/`active`/`superseded`) baselines are never mutated; guard enforced in BOTH the endpoint and the
  service. Same 422-as-structured-body (not raised HTTPException) rule as the Phase 2 bridge.

## Key disconnects that REMAIN
- The legacy `create_draft` SAFL-snapshot path still exists side-by-side (intentionally kept; not repointed).
  Its HTTP entrypoint (POST `/api/telemetry/v2/sites/{id}/expected-baselines`) is now **deprecated** (Phase 5B:
  `deprecated=True` + a `logger.warning` steering callers to create-draft-from-facts) but still returns 201 for
  manual/backfill use. SAFL is NOT a V2 baseline source; V2 baselines come from `project_facts` via
  create-draft-from-facts. Do NOT hard-410 it without confirming no manual/backfill caller depends on it.
- Hourly/8760 → points are still unbuilt (only monthly+annual design points are produced today).
- `ilios-DocAI` (external PVsyst CSV-instruction parser) is offline / unreferenced in `ilios-server`.
- `_next_version` is read-then-insert with no unique constraint on (site, type, version) — concurrent
  create could duplicate a version number (acceptable for an admin-triggered action; future constraint).
