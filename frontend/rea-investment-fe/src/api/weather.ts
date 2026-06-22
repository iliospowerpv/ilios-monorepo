import { AxiosInstance } from 'axios';

import type {
  WeatherDeviceMapping,
  WeatherDeclareRequest,
  WeatherActivateRequest,
  WeatherReReviewRequest,
  WeatherUpstreamReEvaluateResponse,
  WeatherSemanticsReconciliationResponse
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
  const listDeviceMappingHistory = async (
    siteId: number,
    deviceId: number
  ): Promise<WeatherDeviceMapping[]> => {
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
  const getSemanticsReconciliation = async (
    siteId: number
  ): Promise<WeatherSemanticsReconciliationResponse> => {
    const response = await httpClient.get<WeatherSemanticsReconciliationResponse>(
      `${base(siteId)}/semantics-reconciliation`
    );
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
    getSemanticsReconciliation
  });
};
