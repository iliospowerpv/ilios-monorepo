import { AxiosInstance } from 'axios';

import type {
  WeatherDeviceMapping,
  WeatherDeclareRequest,
  WeatherActivateRequest,
  WeatherReReviewRequest,
  WeatherUpstreamReEvaluateResponse,
  WeatherSemanticsReconciliationResponse,
  WeatherProviderList,
  WeatherProviderAccountList,
  WeatherProviderAccountResponse,
  WeatherProviderAccountCreate,
  WeatherProviderAccountUpdate,
  WeatherProviderTestResponse,
  ProviderImportRequest,
  ProviderImportPreviewResponse,
  ProviderImportResponse,
  ExternalWeatherContextResponse
} from '../types/weather';

/**
 * Governed weather-semantics declaration API (Task #65, WS.1–WS.4).
 *
 * Thin client over the additive `/api/weather` Layer-1 governance surface. All
 * write endpoints are telemetry-admin gated server-side; the read endpoints are
 * asset-view + company-visibility scoped. Nothing here infers or converts
 * semantics — it only declares what an operator explicitly states, and reads
 * back what the governance layer already recorded.
 */
export const buildWeatherApi = (httpClient: AxiosInstance) => {
  const base = (siteId: number) => `/api/weather/sites/${siteId}`;

  // List the current (latest) governed declarations for a site.
  const listDeviceMappings = async (siteId: number): Promise<WeatherDeviceMapping[]> => {
    const response = await httpClient.get<WeatherDeviceMapping[]>(`${base(siteId)}/device-mappings`);
    return response.data;
  };

  // Append a new declaration (always draft unless `activate: true`).
  const declareDeviceMapping = async (
    siteId: number,
    payload: WeatherDeclareRequest
  ): Promise<WeatherDeviceMapping> => {
    const response = await httpClient.post<WeatherDeviceMapping>(`${base(siteId)}/device-mappings`, payload);
    return response.data;
  };

  // Activate an existing draft declaration (atomic supersede when applicable).
  const activateDeviceMapping = async (
    siteId: number,
    mappingId: number,
    payload: WeatherActivateRequest = {}
  ): Promise<WeatherDeviceMapping> => {
    const response = await httpClient.post<WeatherDeviceMapping>(
      `${base(siteId)}/device-mappings/${mappingId}/activate`,
      payload
    );
    return response.data;
  };

  // Manually flag an active declaration as needing re-review (monotonic boolean).
  const flagReReview = async (
    siteId: number,
    mappingId: number,
    payload: WeatherReReviewRequest
  ): Promise<WeatherDeviceMapping> => {
    const response = await httpClient.post<WeatherDeviceMapping>(
      `${base(siteId)}/device-mappings/${mappingId}/re-review`,
      payload
    );
    return response.data;
  };

  // Append-only declaration history for a single device (oldest first).
  const listDeviceMappingHistory = async (siteId: number, deviceId: number): Promise<WeatherDeviceMapping[]> => {
    const response = await httpClient.get<WeatherDeviceMapping[]>(
      `${base(siteId)}/devices/${deviceId}/device-mappings`
    );
    return response.data;
  };

  // Read-only preview of upstream-identity drift across active declarations.
  const previewUpstreamChanges = async (siteId: number): Promise<WeatherUpstreamReEvaluateResponse> => {
    const response = await httpClient.get<WeatherUpstreamReEvaluateResponse>(
      `${base(siteId)}/device-mappings/upstream-changes`
    );
    return response.data;
  };

  // Admin action: raise monotonic re-review flags on diverged active declarations.
  const reEvaluateUpstreamChanges = async (siteId: number): Promise<WeatherUpstreamReEvaluateResponse> => {
    const response = await httpClient.post<WeatherUpstreamReEvaluateResponse>(
      `${base(siteId)}/device-mappings/re-evaluate`
    );
    return response.data;
  };

  // Read-only 8-state governed-semantics reconciliation rollup.
  const getSemanticsReconciliation = async (siteId: number): Promise<WeatherSemanticsReconciliationResponse> => {
    const response = await httpClient.get<WeatherSemanticsReconciliationResponse>(
      `${base(siteId)}/semantics-reconciliation`
    );
    return response.data;
  };

  // -------------------------------------------------------------------------
  // Third-party weather provider framework (Phases A–D) — CONTEXT-ONLY.
  // External weather is provenance/context only: it is NEVER expected-eligible,
  // never converted to POA/cell, and never fabricated. These thin clients only
  // read the catalog/context and trigger explicitly-bounded, idempotent pulls.
  // -------------------------------------------------------------------------

  // Read-only catalog of registered providers + capabilities + licensing.
  const listProviders = async (includeDisabled = false): Promise<WeatherProviderList> => {
    const response = await httpClient.get<WeatherProviderList>('/api/weather/providers', {
      params: includeDisabled ? { include_disabled: true } : undefined
    });
    return response.data;
  };

  // Read-only list of a company's weather provider accounts.
  const listProviderAccounts = async (
    companyId: number,
    includeArchived = false
  ): Promise<WeatherProviderAccountList> => {
    const response = await httpClient.get<WeatherProviderAccountList>(
      `/api/weather/companies/${companyId}/weather-provider-accounts`,
      { params: includeArchived ? { include_archived: true } : undefined }
    );
    return response.data;
  };

  // Create a keyed/keyless provider account (credentials stored write-only).
  const createProviderAccount = async (
    companyId: number,
    payload: WeatherProviderAccountCreate
  ): Promise<WeatherProviderAccountResponse> => {
    const response = await httpClient.post<WeatherProviderAccountResponse>(
      `/api/weather/companies/${companyId}/weather-provider-accounts`,
      payload
    );
    return response.data;
  };

  // Rename / pause / archive / rotate credentials (no hard delete).
  const updateProviderAccount = async (
    companyId: number,
    accountId: number,
    payload: WeatherProviderAccountUpdate
  ): Promise<WeatherProviderAccountResponse> => {
    const response = await httpClient.patch<WeatherProviderAccountResponse>(
      `/api/weather/companies/${companyId}/weather-provider-accounts/${accountId}`,
      payload
    );
    return response.data;
  };

  // Verify stored credentials against the provider; updates credential_status.
  const testProviderAccount = async (companyId: number, accountId: number): Promise<WeatherProviderTestResponse> => {
    const response = await httpClient.post<WeatherProviderTestResponse>(
      `/api/weather/companies/${companyId}/weather-provider-accounts/${accountId}/test`
    );
    return response.data;
  };

  // Dry-run a bounded pull: row plan, semantics, context-only verdict. No writes.
  const previewProviderImport = async (
    siteId: number,
    payload: ProviderImportRequest
  ): Promise<ProviderImportPreviewResponse> => {
    const response = await httpClient.post<ProviderImportPreviewResponse>(
      `${base(siteId)}/provider-import/preview`,
      payload
    );
    return response.data;
  };

  // Execute a bounded, gap-only, idempotent pull into a provider_pull batch.
  const runProviderImport = async (siteId: number, payload: ProviderImportRequest): Promise<ProviderImportResponse> => {
    const response = await httpClient.post<ProviderImportResponse>(`${base(siteId)}/provider-import`, payload);
    return response.data;
  };

  // Read-only external-weather context for a site (sources, coverage, pulls).
  const getExternalWeatherContext = async (siteId: number): Promise<ExternalWeatherContextResponse> => {
    const response = await httpClient.get<ExternalWeatherContextResponse>(`${base(siteId)}/external-weather-context`);
    return response.data;
  };

  return Object.freeze({
    listDeviceMappings,
    declareDeviceMapping,
    activateDeviceMapping,
    flagReReview,
    listDeviceMappingHistory,
    previewUpstreamChanges,
    reEvaluateUpstreamChanges,
    getSemanticsReconciliation,
    listProviders,
    listProviderAccounts,
    createProviderAccount,
    updateProviderAccount,
    testProviderAccount,
    previewProviderImport,
    runProviderImport,
    getExternalWeatherContext
  });
};
