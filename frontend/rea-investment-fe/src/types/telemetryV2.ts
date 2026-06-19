export type ProviderAccountStatus = 'active' | 'paused' | 'archived';

export type CredentialStatus = 'unverified' | 'verified' | 'invalid' | 'expired';

export type LastSyncStatus = 'never' | 'success' | 'partial' | 'failed';

export type CompanyProviderStatus = 'active' | 'suspended';

export type ExternalSiteSyncStatus = 'seen' | 'missing' | 'stale';

export interface ProviderCatalogEntry {
  id: number;
  provider_key: string;
  display_name: string;
  config_schema: Record<string, unknown>;
  docs_url: string | null;
  is_enabled: boolean;
}

export interface ProviderCatalogList {
  items: ProviderCatalogEntry[];
}

export interface LicensedProvider {
  id: number;
  company_id: number;
  provider_key: string;
  display_name: string;
  status: CompanyProviderStatus;
  notes: string | null;
  account_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface LicensedProviderList {
  items: LicensedProvider[];
}

export interface LicenseCreatePayload {
  provider_key: string;
  notes?: string | null;
}

/**
 * Write-only credential payload. The backend never echoes these fields back
 * in any response. The frontend must not store them in any persistent state,
 * pass them to siblings/components, or include them in props beyond the
 * single dialog that submits them.
 */
export interface ProviderAccountCredentialsPayload {
  fields: Record<string, string>;
}

export interface ProviderAccountCreatePayload {
  name: string;
  provider_key: string;
  external_account_label?: string | null;
  credentials: ProviderAccountCredentialsPayload;
}

export interface ProviderAccountUpdatePayload {
  name?: string;
  external_account_label?: string | null;
  status?: ProviderAccountStatus;
  credentials?: ProviderAccountCredentialsPayload;
}

export interface ProviderAccount {
  id: number;
  company_id: number;
  name: string;
  provider_key: string;
  display_name: string;
  external_account_label: string | null;
  status: ProviderAccountStatus;
  credential_status: CredentialStatus;
  last_sync_status: LastSyncStatus;
  last_success_at: string | null;
  last_error_at: string | null;
  last_error_message: string | null;
  is_archived: boolean;
  archived_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  credentials_fingerprint: string | null;
  external_site_count: number;
  active_mapping_count: number;
}

export interface ProviderAccountList {
  items: ProviderAccount[];
}

export interface TestAccountResponse {
  success: boolean;
  message: string;
  credential_status: CredentialStatus;
  available_sites_count: number | null;
}

export interface ExternalSite {
  id: number;
  provider_account_id: number;
  external_site_id: string;
  external_site_name: string | null;
  sync_status: ExternalSiteSyncStatus;
  first_seen_at: string;
  last_seen_at: string;
  last_synced_at: string;
  last_sync_run_id: string | null;
  last_sync_error: string | null;
}

export interface ExternalSiteListResponse {
  items: ExternalSite[];
  last_sync_run_id: string | null;
  last_sync_status: LastSyncStatus;
  last_success_at: string | null;
}

export interface SyncSitesResponse {
  sync_run_id: string;
  last_sync_status: LastSyncStatus;
  seen_count: number;
  new_count: number;
  missing_count: number;
  error: string | null;
}

/**
 * Payload for the V2 (DB-only) project/site mapping save. The mapping is keyed
 * on `{provider_account_id, external_site_id}`; the display name is resolved
 * server-side from the iliOS external-site cache, so no live provider call is
 * required when the site has already been synced.
 */
export interface SiteMappingSavePayload {
  provider_account_id: number;
  external_site_id: string;
  mapping_role?: string;
}

export interface SiteMappingResponse {
  id: number;
  site_id: number | null;
  company_id: number | null;
  connection_id: number | null;
  provider_account_id: number | null;
  telemetry_site_id: string;
  telemetry_site_name: string;
  mapping_role: string;
  is_active: boolean;
  created_by_user_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * A single external (provider-side) device cached in the iliOS DB. Populated by
 * the V2 `sync-devices` call and read cache-only when opening Device Mapping.
 */
export interface ExternalDevice {
  id: number;
  provider_account_id: number;
  external_site_id: string;
  external_device_id: string;
  external_device_name: string | null;
  sync_status: ExternalSiteSyncStatus;
  first_seen_at: string;
  last_seen_at: string;
  last_synced_at: string;
  last_sync_run_id: string | null;
  last_sync_error: string | null;
}

export interface ExternalDeviceListResponse {
  items: ExternalDevice[];
  last_sync_run_id: string | null;
  last_sync_status: LastSyncStatus;
  last_success_at: string | null;
}

export interface SyncDevicesResponse {
  sync_run_id: string;
  last_sync_status: LastSyncStatus;
  seen_count: number;
  new_count: number;
  missing_count: number;
  error: string | null;
}

/**
 * A single iliOS device -> external device pairing. The display name is resolved
 * server-side from the synced device cache, so it is not sent here.
 */
export interface DeviceMappingItem {
  device_id: number;
  external_device_id: string;
  device_role?: string;
}

/**
 * Payload for the V2 (DB-only) bulk device mapping save. Mappings are keyed on
 * `{provider_account_id, external_site_id}`; each external device must already
 * exist in the synced device cache so no live provider call is required.
 */
export interface DeviceMappingBulkPayload {
  provider_account_id: number;
  external_site_id: string;
  mappings: DeviceMappingItem[];
}

export interface DeviceMappingBulkResponse {
  successful_count: number;
  failed_count: number;
  errors: string[] | null;
}

/**
 * Lifecycle of a single native ingestion attempt (manual refresh). `partial`
 * means some device/metric pulls succeeded while others failed; `failed` means
 * nothing was written.
 */
export type TelemetrySyncStatus = 'queued' | 'running' | 'partial' | 'succeeded' | 'failed';

/**
 * Optional bounded window for a manual readings refresh. Omitting both bounds
 * refreshes the most recent 24h. Timestamps are ISO-8601 (UTC).
 */
export interface RefreshReadingsPayload {
  window_start?: string | null;
  window_end?: string | null;
}

/**
 * Structured outcome of a manual readings refresh. Returned for every outcome
 * (including provider failures) so the UI can show status + last-refreshed
 * without inspecting raw rows.
 */
export interface RefreshReadingsResponse {
  sync_job_id: number;
  correlation_id: string;
  status: TelemetrySyncStatus;
  site_id: number;
  company_id: number;
  provider_key: string | null;
  external_site_id: string | null;
  window_start: string;
  window_end: string;
  devices_mapped: number;
  devices_seen: number;
  targets_attempted: number;
  targets_with_data: number;
  targets_failed: number;
  targets_ambiguous: number;
  readings_received: number;
  readings_written: number;
  rate_limited: boolean;
  started_at: string | null;
  ended_at: string | null;
  error: string | null;
  errors: string[];
  /**
   * Seconds until another manual refresh/backfill is allowed for this project
   * (shared per-project cooldown). 0 means a manual run is available now.
   */
  cooldown_seconds: number;
}

/**
 * Read-only V2 rollup views (chart wiring). These are derived purely from the
 * PostgreSQL rollup/reading tables — reading them never triggers a provider
 * call, credential access, or BigQuery query. An unmapped/empty site returns a
 * successful empty payload (empty `points` / `devices` / `metrics` / `jobs`).
 */
export type TelemetryBucketSize = '15m' | '30m' | '1h' | '1d';

export type TelemetrySyncScope = 'site' | 'company' | 'portfolio';

export type TelemetrySyncTrigger = 'manual' | 'scheduled' | 'backfill';

export interface TelemetrySeriesPoint {
  bucket_start: string;
  value: number;
  sample_count: number;
  completeness: number | null;
}

export interface TelemetrySeriesResponse {
  site_id: number;
  metric: string;
  bucket_size: string;
  unit: string | null;
  agg: string | null;
  count: number;
  latest_bucket_start: string | null;
  points: TelemetrySeriesPoint[];
}

export interface TelemetryDeviceSeries {
  device_id: number;
  device_name: string | null;
  unit: string | null;
  count: number;
  points: TelemetrySeriesPoint[];
}

export interface TelemetryDeviceSeriesResponse {
  site_id: number;
  metric: string;
  bucket_size: string;
  devices: TelemetryDeviceSeries[];
}

export interface TelemetryLatestMetric {
  metric: string;
  value: number;
  unit: string | null;
  bucket_size: string | null;
  bucket_start: string;
}

export interface TelemetryLatestResponse {
  site_id: number;
  latest_reading_at: string | null;
  latest_bucket_start: string | null;
  metrics: TelemetryLatestMetric[];
}

export interface TelemetrySyncJobSummary {
  id: number;
  scope: TelemetrySyncScope;
  status: TelemetrySyncStatus;
  trigger: TelemetrySyncTrigger;
  window_start: string | null;
  window_end: string | null;
  records_received: number;
  records_written: number;
  last_error: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string | null;
}

export interface TelemetrySyncJobListResponse {
  site_id: number;
  jobs: TelemetrySyncJobSummary[];
}

/** Query params for the site-level rollup series read. */
export interface TelemetrySeriesQuery {
  metric: string;
  bucketSize?: TelemetryBucketSize;
  from?: string;
  to?: string;
}

/** Query params for the per-device rollup series read. */
export interface TelemetryDeviceSeriesQuery extends TelemetrySeriesQuery {
  deviceId?: number;
}

/**
 * Whitelisted automatic-refresh cadences (ISO-8601 durations). Mirrors the
 * server-side `ALLOWED_CADENCES`; the PUT endpoint rejects anything else with
 * 422.
 */
export type TelemetryCadence = 'PT15M' | 'PT30M' | 'PT1H' | 'PT6H' | 'PT24H';

/**
 * Current automation state for one mapped site's telemetry scheduler. Returned
 * even when no scheduler row exists yet (synthesized defaults: `enabled=false`,
 * default cadence). Timestamps are naive UTC ISO strings (no timezone suffix);
 * parse them as UTC before comparing/formatting. No credentials/tokens appear
 * in this payload.
 */
export interface SchedulerState {
  site_id: number;
  provider_account_id: number | null;
  company_id: number | null;
  enabled: boolean;
  cadence: TelemetryCadence;
  next_due_at: string | null;
  last_run_at: string | null;
  last_status: string | null;
  last_error: string | null;
  last_successful_pull_at: string | null;
  last_sync_job_id: number | null;
  locked_until: string | null;
}

/**
 * Enable/disable or change cadence for one site's scheduler. Both fields are
 * optional so a caller can change just one; cadence is validated server-side.
 */
export interface SchedulerUpdatePayload {
  enabled?: boolean;
  cadence?: TelemetryCadence;
}

/** Per-site scheduler status across a company's mapped telemetry sites. */
export interface CompanySchedulerStatusList {
  company_id: number;
  items: SchedulerState[];
}

/** Convenience backfill windows offered as one-click presets. */
export type BackfillPreset = '7d' | '30d';

/**
 * Body for a bounded historical backfill. Provide either a `preset` or an
 * explicit window; the total span is capped at 30 days server-side (inverted or
 * oversized windows are rejected with 422). Timestamps are ISO-8601 (UTC).
 */
export interface BackfillReadingsPayload {
  preset?: BackfillPreset;
  window_start?: string;
  window_end?: string;
}

/** Outcome of one 24h backfill chunk. */
export interface BackfillChunkResult {
  window_start: string;
  window_end: string;
  sync_job_id: number | null;
  status: string;
  readings_received: number;
  readings_written: number;
  rollup_status: string | null;
  error: string | null;
}

export type BackfillStatus = 'succeeded' | 'partial' | 'failed';

/**
 * Aggregate outcome of a bounded backfill. The backfill processes 24h chunks
 * oldest->newest and stops on the first failed chunk, returning every chunk
 * attempted. It never advances the scheduled cursor and never wipes data.
 */
export interface BackfillReadingsResponse {
  site_id: number;
  company_id: number | null;
  status: BackfillStatus;
  requested_window_start: string;
  requested_window_end: string;
  chunks_total: number;
  chunks_succeeded: number;
  chunks_failed: number;
  readings_received: number;
  readings_written: number;
  chunks: BackfillChunkResult[];
  error: string | null;
  /**
   * Seconds until another manual refresh/backfill is allowed for this project
   * (shared per-project cooldown). 0 means a manual run is available now.
   */
  cooldown_seconds: number;
}

// ---------------------------------------------------------------------------
// Path-B device eligibility diagnostics (read-only)
// ---------------------------------------------------------------------------

/**
 * How severely a diagnostic indicator limits a device's telemetry usefulness.
 * Mirrors the backend `DiagnosticBlockingLevel` (most -> least severe).
 */
export type DiagnosticBlockingLevel = 'blocks_calculation' | 'lowers_confidence' | 'informational';

/** A single Path-B "why" item for a device (or the site-level rollup). */
export interface DiagnosticIndicator {
  key: string;
  label: string;
  explanation: string;
  blocking_level: DiagnosticBlockingLevel;
  recommended_action: string | null;
}

/**
 * Disclosed weather measurement semantics for a weather-source device. Reflects
 * the latest `weather_device_mappings` declaration verbatim; never inferred or
 * converted. `physics_usable_*` only report whether the *declared* plane /
 * temperature is usable by today's physics (POA / cell-usable).
 */
export interface DeviceWeatherSemantics {
  has_declaration: boolean;
  metric: string | null;
  irradiance_plane: string;
  temperature_type: string;
  calibration_status: string;
  physics_usable_irradiance: boolean;
  physics_usable_temperature: boolean;
}

/** Per-device eligibility / mapping / semantics position + Path-B indicators. */
export interface DeviceEligibilityDiagnostic {
  device_id: number;
  name: string | null;
  category: string | null;
  device_role: string | null;
  mappable: boolean;
  can_drive_expected: boolean;
  telemetry_capable: boolean;
  weather_source_capable: boolean;
  production_meter_capable: boolean;
  gateway_capable: boolean;
  virtual_device: boolean;
  mapped_status: string;
  is_mapped: boolean;
  source_provider: string | null;
  external_device_type: string | null;
  eligibility_reason: string | null;
  ineligibility_reason: string | null;
  weather_semantics: DeviceWeatherSemantics | null;
  indicators: DiagnosticIndicator[];
}

/**
 * Site-level eligibility diagnostics. `indicators` is a deduped site rollup of
 * the distinct Path-B items across devices (most-severe `blocking_level` per
 * key). Strictly read-only: it never changes eligibility, mapping, semantics,
 * the resolver, or the expected math.
 */
export interface DeviceEligibilityDiagnosticsResponse {
  site_id: number;
  total_devices: number;
  mappable_count: number;
  mapped_count: number;
  unmapped_eligible_count: number;
  expected_driving_count: number;
  weather_source_count: number;
  meter_count: number;
  gateway_count: number;
  virtual_count: number;
  ineligible_count: number;
  weather_unknown_semantics_count: number;
  devices: DeviceEligibilityDiagnostic[];
  indicators: DiagnosticIndicator[];
}

// ---------------------------------------------------------------------------
// DD V2 — Baseline Readiness from promoted project_facts (+ reviewer inputs)
// ---------------------------------------------------------------------------

/**
 * What kind of expectation a baseline represents. Only `weather_adjusted_model`
 * drives the live actual-vs-expected calc; `design_estimate` is a separate,
 * non-blocking track. Left open (`| string`) so backend enum additions never
 * break the build.
 */
export type TelemetryBaselineType = 'weather_adjusted_model' | 'design_estimate' | string;

/**
 * One baseline input's source position on the readiness ladder. Open unions so
 * backend additions never break the build.
 */
export type BaselineSourceStatus =
  | 'missing'
  | 'active_fact'
  | 'active_fact_but_non_numeric'
  | 'normalized_confirmed'
  | 'reviewer_supplied_needed'
  | 'reviewer_supplied'
  | 'optional_default_applied'
  | 'pre_pto_expected_suppressed'
  | 'satisfied'
  | string;

export type BaselineBlockingLevel = 'blocks_draft_baseline' | 'blocks_expected' | 'informational' | string;

/**
 * A PROPOSED (never auto-applied) unit normalization for a fact value. `blocked`
 * means the value cannot be normalized (ambiguous/unknown unit, unparseable) and
 * stays missing. A non-blocked proposal is only applied when the reviewer
 * confirms it — and, for a real unit conversion, sets `allow_conversion`.
 */
export interface BaselineFieldNormalization {
  field: string;
  raw_value: string;
  target_unit: string;
  blocked: boolean;
  reason: string;
  proposed_value: number | null;
  from_unit: string | null;
  method: 'unit_strip' | 'unit_convert' | string | null;
  factor: number;
  requires_confirmation: boolean;
  requires_conversion_confirmation: boolean;
}

/**
 * One baseline input's true position on the readiness ladder (descriptive). It
 * never changes `ready` semantics — the panel uses it to show what is usable,
 * what needs a reviewer value or a normalization confirmation, and what the next
 * step is.
 */
export interface BaselineReadinessFieldStatus {
  field: string;
  display_label: string;
  required: boolean;
  expected_type: 'number' | 'count' | 'percent' | 'factor' | 'date' | string;
  expected_unit: string | null;
  source_status: BaselineSourceStatus;
  blocking_level: BaselineBlockingLevel;
  current_raw_value: string | null;
  current_normalized_value: number | null;
  default_value: number | null;
  reason: string | null;
  recommended_action: string | null;
  fact_id: number | null;
  document_id: number | null;
  ai_confidence: number | null;
  normalization: BaselineFieldNormalization | null;
}

/** One physics input that fed (or could feed) a facts-based draft. */
export interface BaselineFactFieldUsage {
  field: string;
  source: 'project_fact' | 'reviewer_supplied' | 'project_fact_normalized' | string;
  value: number;
  canonical_name: string | null;
  fact_id: number | null;
  document_id: number | null;
  ai_confidence: number | null;
}

/**
 * A reviewer's explicit confirmation of a proposed unit normalization. The
 * server NEVER trusts `confirmed_value` as the value to store — it recomputes the
 * normalization from the current active fact and only applies it when its own
 * proposed value matches, the confirmation is not stale (`source_fact_id` /
 * `raw_value` match the current fact), and — for a real conversion —
 * `allow_conversion` is set.
 */
export interface NormalizationConfirmationRequest {
  confirmed_value: number;
  unit?: string | null;
  allow_conversion?: boolean;
  source_fact_id?: number | null;
  raw_value?: string | null;
}

export interface ReadinessFromFactsResponse {
  site_id: number;
  baseline_type: TelemetryBaselineType;
  ready: boolean;
  fields_used: BaselineFactFieldUsage[];
  missing_fields: string[];
  warnings: string[];
  source_fact_ids: number[];
  source_document_ids: number[];
  field_blockers: BaselineReadinessFieldStatus[];
}

export interface CreateDraftFromFactsRequest {
  baseline_type?: TelemetryBaselineType;
  baseline_name?: string | null;
  reason?: string | null;

  // Required datasheet constants (no fact source exists today).
  thermal_coefficient_pct?: number | null;
  power_tolerance_min_pct?: number | null;
  year_1_degradation_pct?: number | null;
  annual_degradation_pct?: number | null;
  cec_efficiency_pct?: number | null;

  // Optional supplemental — absence is a warning, not a blocker.
  soiling_factor?: number | null;
  dc_loss_pct?: number | null;
  ac_loss_pct?: number | null;
  medium_voltage_loss_pct?: number | null;
  mv_line_loss_pct?: number | null;
  pto_date?: string | null;

  // Reviewer-confirmed unit normalizations keyed by canonical column
  // (`module_wattage` / `inverter_wattage`). Re-verified server-side.
  normalizations?: Record<string, NormalizationConfirmationRequest>;
}

/**
 * Minimal shape of the created/reused draft baseline. The panel only needs the
 * identity; the full row carries many additional optional physics columns.
 */
export interface ExpectedBaselineSummary {
  id: number;
  company_id: number;
  site_id: number;
  baseline_name: string;
  baseline_type: TelemetryBaselineType;
  status: string;
  [key: string]: unknown;
}

export interface CreateDraftFromFactsResponse {
  site_id: number;
  baseline_type: TelemetryBaselineType;
  ready: boolean;
  status: 'draft' | 'review_required' | string;
  draft_baseline_id: number | null;
  created: boolean;
  idempotent_existing: boolean;
  fields_used: BaselineFactFieldUsage[];
  missing_fields: string[];
  warnings: string[];
  source_fact_ids: number[];
  source_document_ids: number[];
  field_blockers: BaselineReadinessFieldStatus[];
  baseline: ExpectedBaselineSummary | null;
}
