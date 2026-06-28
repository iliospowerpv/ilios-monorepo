/**
 * Governed weather-semantics declaration types (Task #65, WS.1–WS.4).
 *
 * These mirror the backend `app/schema/weather.py` shapes for the additive,
 * read-mostly Layer-1 governance surface. Nothing here infers or converts
 * semantics: a value the operator never declared stays `unknown`, and the UI
 * only ever renders what the backend already recorded. String unions stay open
 * (`| string`) so a backend enum addition never breaks the build.
 */

// --- Declared measurement-semantics enums (verbatim from the backend) -------
export type WeatherIrradiancePlane = 'poa' | 'ghi' | 'dni' | 'dhi' | 'unknown';

export type WeatherTemperatureType = 'cell' | 'module' | 'ambient' | 'modeled_cell' | 'unknown';

export type WeatherCalibrationStatus = 'calibrated' | 'uncalibrated' | 'unknown';

export type WeatherDeclarationBasis =
  | 'provider_confirmed'
  | 'source_document'
  | 'reviewer_source_note'
  | 'reviewer_assumption';

export type WeatherDeclarationStatus = 'draft' | 'active' | 'superseded';

// --- Governed taxonomy states ----------------------------------------------
// Declaration axis (the governed declaration verdict states).
export type WeatherDeclarationState =
  | 'source_exists_semantics_unknown'
  | 'declaration_draft'
  | 'declared_not_physics_usable'
  | 'declared_eligible_integration_pending'
  | 'declaration_stale_needs_re_review';

// Reconciliation headline = the declaration states above, the source/profile
// overlay axis (weather_source_missing / weather_source_stale /
// source_coverage_incomplete), plus the observed-device state for a device that
// is telemetry-mapped and/or producing readings but has no governed declaration.
export type WeatherReconciliationState =
  | WeatherDeclarationState
  | 'observed_weather_device_no_governed_declaration'
  | 'weather_source_missing'
  | 'weather_source_stale'
  | 'source_coverage_incomplete';

export type WeatherBlockingLevel = 'blocks_calculation' | 'lowers_confidence' | 'informational';

// --- Declaration row (append-only history; current = latest) ----------------
export interface WeatherDeviceMapping {
  id: number;
  site_id: number;
  device_id: number | null;
  external_device_id: string | null;
  weather_source_id: number | null;
  metric: string;
  provider_key: string | null;
  irradiance_plane: WeatherIrradiancePlane | string;
  temperature_type: WeatherTemperatureType | string;
  calibration_status: WeatherCalibrationStatus | string;
  calibrated_at: string | null;
  calibration_reference: string | null;
  effective_from: string | null;
  effective_to: string | null;
  physics_usable_irradiance: boolean;
  physics_usable_temperature: boolean;

  // WS.2 governance (null on legacy / ungoverned rows).
  declaration_status: WeatherDeclarationStatus | string | null;
  declaration_basis: WeatherDeclarationBasis | string | null;
  declared_by: number | null;
  declared_at: string | null;
  activated_by: number | null;
  activated_at: string | null;
  supersedes_mapping_id: number | null;
  superseded_by_mapping_id: number | null;
  needs_re_review: boolean;
  re_review_reason: string | null;
  source_document_id: number | null;
  source_file_id: number | null;
  reviewer_note: string | null;
  sensor_role: string | null;
  sensor_model: string | null;

  // WS.2 derived verdict (read-only; recomputed live, never persisted).
  expected_model_eligible: boolean;
  declaration_state: WeatherDeclarationState | string | null;
  eligibility_reason_codes: string[];
  eligibility_blocking_level: WeatherBlockingLevel | string | null;
  eligibility_required_action: string | null;
  layer1_message: string | null;
}

// --- Declare / activate / re-review request payloads ------------------------
// Sent verbatim to the backend Pydantic models, so fields stay snake_case.
export interface WeatherDeclareRequest {
  device_id: number;
  metric: string;
  declaration_basis: WeatherDeclarationBasis;
  weather_source_id?: number | null;
  external_device_id?: string | null;
  provider_key?: string | null;
  irradiance_plane?: WeatherIrradiancePlane;
  temperature_type?: WeatherTemperatureType;
  calibration_status?: WeatherCalibrationStatus;
  calibrated_at?: string | null;
  calibration_reference?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  source_document_id?: number | null;
  source_file_id?: number | null;
  reviewer_note?: string | null;
  sensor_role?: string | null;
  sensor_model?: string | null;
  supersedes_mapping_id?: number | null;
  // `reviewer_assumption` basis requires this explicit confirmation (friction).
  assumption_confirmed?: boolean;
  // When true the draft is created AND activated atomically.
  activate?: boolean;
}

export interface WeatherActivateRequest {
  rationale?: string | null;
}

export interface WeatherReReviewRequest {
  reason: string;
}

// --- Upstream-change / stale detector (WS.3, read-only signal) --------------
export interface WeatherUpstreamMappingDivergence {
  mapping_id: number;
  device_id: number | null;
  metric: string | null;
  needs_re_review: boolean;
  has_stored_fingerprint: boolean;
  diverged: boolean;
  changed_keys: string[];
  summary: string | null;
  would_flag: boolean;
  flagged: boolean;
}

export interface WeatherUpstreamReEvaluateResponse {
  site_id: number;
  applied: boolean;
  total_active: number;
  diverged_count: number;
  would_flag_count: number;
  already_flagged_count: number;
  newly_flagged_count: number;
  mappings: WeatherUpstreamMappingDivergence[];
}

// --- 9-state semantics reconciliation (WS.4, read-only) ---------------------
export interface WeatherSemanticsReconciliationRow {
  device_id: number;
  device_name: string | null;
  device_category: string | null;
  metric: string | null;
  mapping_id: number | null;

  reconciliation_state: WeatherReconciliationState | string;
  state_label: string;
  state_explanation: string;
  required_action: string | null;
  blocking_level: WeatherBlockingLevel | string;

  declaration_state: WeatherDeclarationState | string | null;
  source_state: string;

  declaration_status: WeatherDeclarationStatus | string | null;
  declaration_basis: WeatherDeclarationBasis | string | null;
  needs_re_review: boolean;
  re_review_reason: string | null;
  expected_model_eligible: boolean;
  physics_usable_irradiance: boolean;
  physics_usable_temperature: boolean;
  irradiance_plane: WeatherIrradiancePlane | string | null;
  temperature_type: WeatherTemperatureType | string | null;
  calibration_status: WeatherCalibrationStatus | string | null;
  layer1_message: string | null;
  eligibility_reason_codes: string[];
}

export interface WeatherSemanticsReconciliationResponse {
  site_id: number;
  generated_at: string;
  total_weather_capable_devices: number;
  has_weather_source: boolean;
  has_active_weather_profile: boolean;
  eligible_count: number;
  needs_re_review_count: number;
  state_counts: Record<string, number>;
  blocking_counts: Record<string, number>;
  devices: WeatherSemanticsReconciliationRow[];
}

// ---------------------------------------------------------------------------
// Third-party weather provider framework (Phases A–D) — CONTEXT-ONLY.
//
// These mirror `app/schema/weather.py`. External weather is context/provenance
// only: every provider/source/preview/run carries `expected_eligible_capable:
// false` and is never converted to POA irradiance or cell temperature. The UI
// must surface that verdict honestly and never fabricate a value (a missing
// reading is the ABSENCE of a row, never a 0). String unions stay open so a
// backend enum addition never breaks the build.
// ---------------------------------------------------------------------------
export interface WeatherProviderEntry {
  provider_key: string;
  display_name: string;
  licensing_class: string | null;
  docs_url: string | null;
  is_enabled: boolean;
  requires_credentials: boolean;
  config_schema: Record<string, unknown>;
  capabilities: Record<string, unknown> | null;
  // Always false in Phases A–D — external weather is never expected-eligible.
  expected_eligible_capable: boolean;
}

export interface WeatherProviderList {
  items: WeatherProviderEntry[];
}

export type WeatherProviderAccountStatus = 'active' | 'paused' | 'archived' | string;

// Credentials are sent write-only and never returned by any response.
export interface WeatherProviderCredentials {
  fields: Record<string, string>;
}

export interface WeatherProviderAccountCreate {
  provider_key: string;
  display_name: string;
  external_account_label?: string | null;
  credentials?: WeatherProviderCredentials | null;
  licensing_acknowledged?: boolean;
}

export interface WeatherProviderAccountUpdate {
  display_name?: string | null;
  external_account_label?: string | null;
  status?: WeatherProviderAccountStatus;
  credentials?: WeatherProviderCredentials | null;
  licensing_acknowledged?: boolean | null;
}

export interface WeatherProviderAccountResponse {
  id: number;
  company_id: number;
  provider_key: string;
  display_name: string;
  external_account_label: string | null;
  status: string;
  credential_status: string;
  last_sync_status: string;
  licensing_acknowledged: boolean;
  licensing_acknowledged_at: string | null;
  last_success_at: string | null;
  last_error_at: string | null;
  last_error_message: string | null;
  is_archived: boolean;
  has_stored_credentials: boolean;
  credential_fingerprint: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface WeatherProviderAccountList {
  items: WeatherProviderAccountResponse[];
}

export interface WeatherProviderTestResponse {
  success: boolean;
  message: string;
  credential_status: string;
}

// --- Provider import (preview / run / batches) -----------------------------
// Window fields are naive-UTC ISO strings (the existing storage convention).
export interface ProviderImportRequest {
  provider_key: string;
  account_id?: number | null;
  window_start: string;
  window_end: string;
  metrics?: string[] | null;
  granularity?: string;
}

export interface ProviderImportPreviewResponse {
  provider_key: string;
  display_name: string;
  licensing_class: string | null;
  context_only: boolean;
  expected_eligible_capable: boolean;
  verdict: string;
  requested_metrics: string[];
  native_plane: WeatherIrradiancePlane | string;
  native_temperature_type: WeatherTemperatureType | string;
  is_modeled: boolean;
  window_start: string;
  window_end: string;
  effective_window_start: string | null;
  effective_window_end: string | null;
  chunk_count: number;
  chunks_to_pull: number;
  chunks_already_covered: number;
  estimated_provider_calls: number;
  existing_observation_count: number;
  rate_limit_remaining_minute: number | null;
  rate_limit_remaining_day: number | null;
  warnings: string[];
}

export interface ProviderImportResponse {
  status: string;
  pull_status: string;
  batch_id: number | null;
  site_id: number;
  weather_source_id: number | null;
  provider_key: string;
  account_id: number | null;
  context_only: boolean;
  expected_eligible_capable: boolean;
  rows_pulled: number;
  rows_inserted: number;
  rows_duplicate: number;
  distinct_metrics: string[];
  physics_usable_rows: number;
  stored_not_usable_rows: number;
  modeled_rows: number;
  chunks_pulled: number;
  chunks_skipped: number;
  period_start: string | null;
  period_end: string | null;
  api_version: string | null;
  rate_limited: boolean;
  warnings: string[];
  errors: string[];
}

export interface ProviderPullBatchResponse {
  id: number;
  site_id: number;
  weather_source_id: number;
  account_id: number | null;
  batch_kind: string;
  pull_status: string | null;
  period_start: string | null;
  period_end: string | null;
  row_count: number | null;
  provider_api_version: string | null;
  error_summary: string | null;
  created_at: string | null;
}

export interface ProviderPullBatchList {
  items: ProviderPullBatchResponse[];
}

// --- External weather context (read-only provenance, Phase D) ---------------
export interface ExternalWeatherContextMetric {
  metric: string;
  observation_count: number;
  earliest_obs: string | null;
  latest_obs: string | null;
}

export interface ExternalWeatherContextSource {
  weather_source_id: number;
  source_type: string;
  provider_key: string | null;
  display_name: string;
  is_modeled: boolean;
  default_confidence: string | null;
  licensing_note: string | null;
  active: boolean;
  observation_count: number;
  earliest_obs: string | null;
  latest_obs: string | null;
  metrics: ExternalWeatherContextMetric[];
}

export interface ExternalWeatherContextResponse {
  site_id: number;
  context_only: boolean;
  expected_eligible_capable: boolean;
  banner: string;
  source_count: number;
  total_observation_count: number;
  sources: ExternalWeatherContextSource[];
  last_pull: ProviderPullBatchResponse | null;
  recent_batches: ProviderPullBatchResponse[];
}
