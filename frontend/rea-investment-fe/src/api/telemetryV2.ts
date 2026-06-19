import type { AxiosInstance } from 'axios';

import type {
  BackfillReadingsPayload,
  BackfillReadingsResponse,
  CompanySchedulerStatusList,
  CreateDraftFromFactsRequest,
  CreateDraftFromFactsResponse,
  DeviceEligibilityDiagnosticsResponse,
  DeviceMappingBulkPayload,
  DeviceMappingBulkResponse,
  ExpectedBaselineListResponse,
  ExpectedBaselineResponse,
  ExternalDeviceListResponse,
  ExternalSiteListResponse,
  LicenseCreatePayload,
  LicensedProvider,
  LicensedProviderList,
  ProviderAccount,
  ProviderAccountCreatePayload,
  ProviderAccountList,
  ProviderAccountUpdatePayload,
  ProviderCatalogList,
  ReadinessFromFactsResponse,
  RefreshReadingsPayload,
  RefreshReadingsResponse,
  SchedulerState,
  SchedulerUpdatePayload,
  SiteMappingResponse,
  SiteMappingSavePayload,
  SyncDevicesResponse,
  SyncSitesResponse,
  TelemetryDeviceSeriesQuery,
  TelemetryDeviceSeriesResponse,
  TelemetryLatestResponse,
  TelemetrySeriesQuery,
  TelemetrySeriesResponse,
  TelemetrySyncJobListResponse,
  TestAccountResponse
} from '../types/telemetryV2';

const V2 = '/api/telemetry/v2';

// A bounded historical backfill runs up to thirty sequential 24h provider pulls
// in one request, which easily exceeds the default 30s axios timeout. Give this
// one call a generous per-request override so the client waits for the server
// instead of aborting mid-run (which would strand the lease and show a false
// error while the server keeps working).
const BACKFILL_TIMEOUT_MS = 10 * 60 * 1000;

export const buildTelemetryV2Api = (httpClient: AxiosInstance) => {
  const getCatalog = async (): Promise<ProviderCatalogList> => {
    const { data } = await httpClient.get<ProviderCatalogList>(`${V2}/catalog`);
    return data;
  };

  const listLicensedProviders = async (companyId: number): Promise<LicensedProviderList> => {
    const { data } = await httpClient.get<LicensedProviderList>(`${V2}/companies/${companyId}/licensed-providers`);
    return data;
  };

  const grantLicense = async (companyId: number, payload: LicenseCreatePayload): Promise<LicensedProvider> => {
    const { data } = await httpClient.post<LicensedProvider>(
      `${V2}/companies/${companyId}/licensed-providers`,
      payload
    );
    return data;
  };

  const revokeLicense = async (companyId: number, licenseId: number): Promise<void> => {
    await httpClient.delete(`${V2}/companies/${companyId}/licensed-providers/${licenseId}`);
  };

  const listProviderAccounts = async (
    companyId: number,
    options: { includeArchived?: boolean } = {}
  ): Promise<ProviderAccountList> => {
    const params = options.includeArchived ? '?include_archived=true' : '';
    const { data } = await httpClient.get<ProviderAccountList>(
      `${V2}/companies/${companyId}/provider-accounts${params}`
    );
    return data;
  };

  const getProviderAccount = async (companyId: number, accountId: number): Promise<ProviderAccount> => {
    const { data } = await httpClient.get<ProviderAccount>(
      `${V2}/companies/${companyId}/provider-accounts/${accountId}`
    );
    return data;
  };

  /**
   * Creates a provider account and persists the credentials write-only.
   * The server intentionally does NOT call the external provider here;
   * the new account appears with credential_status=unverified and
   * last_sync_status=never. The UI must prompt the user to test next.
   */
  const createProviderAccount = async (
    companyId: number,
    payload: ProviderAccountCreatePayload
  ): Promise<ProviderAccount> => {
    const { data } = await httpClient.post<ProviderAccount>(`${V2}/companies/${companyId}/provider-accounts`, payload);
    return data;
  };

  /**
   * PATCH supports renaming, status changes, and credential rotation. When
   * `credentials` is provided the server adds a new secret version (or
   * mints a fresh secret in legacy fallback) and resets credential_status
   * to unverified. Credential values are never returned in the response.
   */
  const updateProviderAccount = async (
    companyId: number,
    accountId: number,
    payload: ProviderAccountUpdatePayload
  ): Promise<ProviderAccount> => {
    const { data } = await httpClient.patch<ProviderAccount>(
      `${V2}/companies/${companyId}/provider-accounts/${accountId}`,
      payload
    );
    return data;
  };

  const archiveProviderAccount = async (companyId: number, accountId: number): Promise<void> => {
    await httpClient.delete(`${V2}/companies/${companyId}/provider-accounts/${accountId}`);
  };

  const testProviderAccount = async (accountId: number): Promise<TestAccountResponse> => {
    const { data } = await httpClient.post<TestAccountResponse>(`${V2}/provider-accounts/${accountId}/test`);
    return data;
  };

  const syncProviderAccountSites = async (accountId: number): Promise<SyncSitesResponse> => {
    const { data } = await httpClient.post<SyncSitesResponse>(`${V2}/provider-accounts/${accountId}/sync-sites`);
    return data;
  };

  const listExternalSites = async (accountId: number): Promise<ExternalSiteListResponse> => {
    const { data } = await httpClient.get<ExternalSiteListResponse>(
      `${V2}/provider-accounts/${accountId}/external-sites`
    );
    return data;
  };

  /**
   * Create or update the project/site -> external-site mapping in the iliOS DB.
   * This is the V2 (DB-only) save path: it does not require a live provider call
   * or any GCP/Firestore sync. The selected external site must already exist in
   * the synced cache for the connection.
   */
  const saveSiteMapping = async (siteId: number, payload: SiteMappingSavePayload): Promise<SiteMappingResponse> => {
    const { data } = await httpClient.put<SiteMappingResponse>(`${V2}/sites/${siteId}/mapping`, payload);
    return data;
  };

  /**
   * Read the synced device cache for one external site. This is cache-only: it
   * never triggers a live provider call, so opening Device Mapping is safe even
   * when the provider is unreachable.
   */
  const listExternalDevices = async (
    accountId: number,
    externalSiteId: string
  ): Promise<ExternalDeviceListResponse> => {
    const { data } = await httpClient.get<ExternalDeviceListResponse>(
      `${V2}/provider-accounts/${accountId}/external-sites/${encodeURIComponent(externalSiteId)}/devices`
    );
    return data;
  };

  /**
   * Explicitly refresh the device cache for one external site by calling the
   * provider once. Never wipes existing cache/mappings on failure.
   */
  const syncProviderAccountDevices = async (
    accountId: number,
    externalSiteId: string
  ): Promise<SyncDevicesResponse> => {
    const { data } = await httpClient.post<SyncDevicesResponse>(
      `${V2}/provider-accounts/${accountId}/external-sites/${encodeURIComponent(externalSiteId)}/sync-devices`
    );
    return data;
  };

  /**
   * Persist iliOS device -> external device mappings in the iliOS DB. V2
   * (DB-only) path: no live provider call, no GCP/Firestore sync. Each external
   * device must already exist in the synced device cache.
   */
  const saveDeviceMappings = async (
    siteId: number,
    payload: DeviceMappingBulkPayload
  ): Promise<DeviceMappingBulkResponse> => {
    const { data } = await httpClient.post<DeviceMappingBulkResponse>(`${V2}/sites/${siteId}/device-mappings`, payload);
    return data;
  };

  /**
   * Trigger a native V2 telemetry pull for one mapped project/site. Pulls the
   * site's mapped devices over a bounded window (default: most recent 24h) and
   * upserts readings idempotently. Never wipes existing data on failure; always
   * resolves with a structured summary (including for provider failures).
   */
  const refreshSiteReadings = async (
    siteId: number,
    payload: RefreshReadingsPayload = {}
  ): Promise<RefreshReadingsResponse> => {
    const { data } = await httpClient.post<RefreshReadingsResponse>(`${V2}/sites/${siteId}/refresh-readings`, payload);
    return data;
  };

  /**
   * Read a site-level V2 rollup series for one normalized metric. Read-only:
   * never triggers a provider/credential call or BigQuery query. Returns an
   * empty `points` list (still HTTP 200) when the site has no matching rollups.
   */
  const getSiteRollupSeries = async (siteId: number, query: TelemetrySeriesQuery): Promise<TelemetrySeriesResponse> => {
    const params = new URLSearchParams({ metric: query.metric });
    if (query.bucketSize) params.set('bucket_size', query.bucketSize);
    if (query.from) params.set('from', query.from);
    if (query.to) params.set('to', query.to);
    const { data } = await httpClient.get<TelemetrySeriesResponse>(`${V2}/sites/${siteId}/series?${params.toString()}`);
    return data;
  };

  /** Read per-device V2 rollup series for one metric, grouped by device. */
  const getSiteDeviceRollupSeries = async (
    siteId: number,
    query: TelemetryDeviceSeriesQuery
  ): Promise<TelemetryDeviceSeriesResponse> => {
    const params = new URLSearchParams({ metric: query.metric });
    if (query.bucketSize) params.set('bucket_size', query.bucketSize);
    if (query.deviceId != null) params.set('device_id', String(query.deviceId));
    if (query.from) params.set('from', query.from);
    if (query.to) params.set('to', query.to);
    const { data } = await httpClient.get<TelemetryDeviceSeriesResponse>(
      `${V2}/sites/${siteId}/device-series?${params.toString()}`
    );
    return data;
  };

  /**
   * Read the freshness snapshot for a site: newest reading/rollup timestamps
   * plus the latest value per normalized metric. Used to show a "data as of"
   * caption on the O&M charts. Empty (all-null) for non-V2 sites.
   */
  const getSiteLatestTelemetry = async (siteId: number): Promise<TelemetryLatestResponse> => {
    const { data } = await httpClient.get<TelemetryLatestResponse>(`${V2}/sites/${siteId}/latest`);
    return data;
  };

  /** Read most-recent-first V2 ingestion attempts for a site. */
  const listSiteSyncJobs = async (siteId: number, limit = 20): Promise<TelemetrySyncJobListResponse> => {
    const { data } = await httpClient.get<TelemetrySyncJobListResponse>(
      `${V2}/sites/${siteId}/sync-jobs?limit=${limit}`
    );
    return data;
  };

  /**
   * Read the native telemetry scheduler state for one mapped site. Returns
   * synthesized disabled defaults (HTTP 200) when no scheduler row exists yet,
   * so the admin control can render without a separate "configured?" probe.
   * Admin-gated server-side (telemetry_admin_required).
   */
  const getSiteScheduler = async (siteId: number): Promise<SchedulerState> => {
    const { data } = await httpClient.get<SchedulerState>(`${V2}/sites/${siteId}/scheduler`);
    return data;
  };

  /**
   * Enable/disable or change cadence for one site's scheduler. Either field may
   * be sent alone. Cadence is validated against the server whitelist (422 on an
   * unknown value); a 400 is returned when the site is not yet mapped.
   */
  const updateSiteScheduler = async (siteId: number, payload: SchedulerUpdatePayload): Promise<SchedulerState> => {
    const { data } = await httpClient.put<SchedulerState>(`${V2}/sites/${siteId}/scheduler`, payload);
    return data;
  };

  /**
   * Read strictly READ-ONLY Path-B eligibility diagnostics for a site. Discloses
   * where each device sits in the eligibility -> mapping -> weather-semantics
   * chain plus a deduped site-level rollup of "why" indicators. Never triggers a
   * provider/credential call and changes no eligibility, mapping, semantics,
   * resolver, or expected math.
   */
  const getSiteEligibilityDiagnostics = async (siteId: number): Promise<DeviceEligibilityDiagnosticsResponse> => {
    const { data } = await httpClient.get<DeviceEligibilityDiagnosticsResponse>(
      `${V2}/sites/${siteId}/eligibility-diagnostics`
    );
    return data;
  };

  /** List per-site scheduler status across a company's mapped telemetry sites. */
  const getCompanySchedulerStatus = async (companyId: number): Promise<CompanySchedulerStatusList> => {
    const { data } = await httpClient.get<CompanySchedulerStatusList>(`${V2}/companies/${companyId}/scheduler/status`);
    return data;
  };

  /**
   * Run a bounded historical backfill for one mapped site (preset or explicit
   * window, capped at 30 days). Claims the same per-site lease lock as the
   * scheduler, so a concurrent run returns HTTP 409. Never wipes existing data
   * and never advances the live scheduled cursor. Uses an extended per-request
   * timeout because the run is synchronous and chunked.
   */
  const backfillSiteReadings = async (
    siteId: number,
    payload: BackfillReadingsPayload
  ): Promise<BackfillReadingsResponse> => {
    const { data } = await httpClient.post<BackfillReadingsResponse>(
      `${V2}/sites/${siteId}/backfill-readings`,
      payload,
      { timeout: BACKFILL_TIMEOUT_MS }
    );
    return data;
  };

  /**
   * Read-only readiness for building a weather-adjusted DRAFT baseline from a
   * site's PROMOTED `project_facts`. Never writes and never fabricates: the
   * reviewer-only datasheet constants are always reported as `missing_fields`
   * here (they are supplied on the create request), and `field_blockers` carries
   * the per-input readiness ladder for the panel.
   */
  const getReadinessFromFacts = async (siteId: number, baselineType?: string): Promise<ReadinessFromFactsResponse> => {
    const { data } = await httpClient.get<ReadinessFromFactsResponse>(
      `${V2}/sites/${siteId}/expected-baseline/readiness-from-facts`,
      baselineType ? { params: { baseline_type: baselineType } } : undefined
    );
    return data;
  };

  /**
   * Create a `draft` baseline from promoted facts ∪ reviewer-supplied constants.
   * 201 = newly created, 200 = idempotent reuse, 422 = `review_required` (nothing
   * created). The draft is NEVER auto-approved/activated and `project_facts` are
   * NEVER mutated. A 422 surfaces as an axios error whose `response.data` is the
   * `CreateDraftFromFactsResponse` body, so callers can read `field_blockers`.
   */
  const createDraftFromFacts = async (
    siteId: number,
    payload: CreateDraftFromFactsRequest
  ): Promise<CreateDraftFromFactsResponse> => {
    const { data } = await httpClient.post<CreateDraftFromFactsResponse>(
      `${V2}/sites/${siteId}/expected-baseline/create-draft-from-facts`,
      payload
    );
    return data;
  };

  /**
   * READ-ONLY: list every expected-performance baseline for a site, newest
   * first (any status/type). Never triggers a provider/credential call and
   * never mutates. Consumed by the read-only Draft Baseline Review panel to
   * render draft / approved-not-active / active baselines with provenance.
   */
  const listExpectedBaselines = async (siteId: number): Promise<ExpectedBaselineListResponse> => {
    const { data } = await httpClient.get<ExpectedBaselineListResponse>(`${V2}/sites/${siteId}/expected-baselines`);
    return data;
  };

  /**
   * READ-ONLY: the single active baseline of a type (defaults to
   * `weather_adjusted_model`), or `null` when none is active. Read-only audit
   * surface only — it never approves or activates anything.
   */
  const getActiveExpectedBaseline = async (
    siteId: number,
    baselineType?: string
  ): Promise<ExpectedBaselineResponse | null> => {
    const { data } = await httpClient.get<ExpectedBaselineResponse | null>(
      `${V2}/sites/${siteId}/expected-baselines/active`,
      baselineType ? { params: { baseline_type: baselineType } } : undefined
    );
    return data;
  };

  /**
   * Stamp reviewer/approver and move a `draft`/`in_review` baseline to
   * `approved`. Explicit and separate from activation — approval NEVER makes a
   * baseline active and NEVER mutates project_facts / accepted values. The
   * backend gate is stricter than draft creation (telemetry_admin + company-admin
   * + company visibility): 403 = no permission, 404 = baseline gone, 409 = the
   * baseline is not in an approvable state.
   */
  const approveExpectedBaseline = async (baselineId: number): Promise<ExpectedBaselineResponse> => {
    const { data } = await httpClient.post<ExpectedBaselineResponse>(`${V2}/expected-baselines/${baselineId}/approve`);
    return data;
  };

  /**
   * Make an `approved` baseline the single `active` weather-adjusted baseline for
   * its site, superseding the prior active one (kept for audit). Explicit and
   * separate from approval — it triggers NO historical backfill and regenerates
   * NO expected values: from its activation boundary forward O&M reads this
   * baseline, while historical periods stay period-effective. 409 when the
   * baseline is not `approved`.
   */
  const activateExpectedBaseline = async (baselineId: number): Promise<ExpectedBaselineResponse> => {
    const { data } = await httpClient.post<ExpectedBaselineResponse>(`${V2}/expected-baselines/${baselineId}/activate`);
    return data;
  };

  return {
    getCatalog,
    listLicensedProviders,
    grantLicense,
    revokeLicense,
    listProviderAccounts,
    getProviderAccount,
    createProviderAccount,
    updateProviderAccount,
    archiveProviderAccount,
    testProviderAccount,
    syncProviderAccountSites,
    listExternalSites,
    saveSiteMapping,
    listExternalDevices,
    syncProviderAccountDevices,
    saveDeviceMappings,
    refreshSiteReadings,
    getSiteRollupSeries,
    getSiteDeviceRollupSeries,
    getSiteLatestTelemetry,
    listSiteSyncJobs,
    getSiteScheduler,
    updateSiteScheduler,
    getCompanySchedulerStatus,
    getSiteEligibilityDiagnostics,
    backfillSiteReadings,
    getReadinessFromFacts,
    createDraftFromFacts,
    listExpectedBaselines,
    getActiveExpectedBaseline,
    approveExpectedBaseline,
    activateExpectedBaseline
  };
};

export type TelemetryV2Api = ReturnType<typeof buildTelemetryV2Api>;
