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
// Declaration axis (states 1-5).
export type WeatherDeclarationState =
  | 'source_exists_semantics_unknown'
  | 'declaration_draft'
  | 'declared_not_physics_usable'
  | 'declared_eligible_integration_pending'
  | 'declaration_stale_needs_re_review';

// Source/profile overlay axis (states 6-8) + the declaration states above; the
// reconciliation headline is one of all eight.
export type WeatherReconciliationState =
  | WeatherDeclarationState
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

// --- 8-state semantics reconciliation (WS.4, read-only) ---------------------
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
