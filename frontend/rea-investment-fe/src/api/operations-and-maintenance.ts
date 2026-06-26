import { AxiosInstance } from 'axios';

import type { ExpectedState } from '../utils/telemetry/expectedState';
import type { ObservedCondition } from '../types/telemetryV2';

enum Ordering {
  ID = 'id',
  Name = 'name',
  TotalSites = 'total_sites',
  TotalCapacity = 'total_capacity'
}

enum Direction {
  Asc = 'asc',
  Desc = 'desc'
}

interface Params {
  skip?: number;
  limit?: number;
  search?: string;
  order_by?: Ordering;
  order_direction?: Direction;
}

interface AlertsOverview {
  total: number;
  severity?: 'warning' | 'high' | 'critical';
}

interface OMCompanyInfo {
  id: number;
  name: string;
  total_sites: number;
  total_capacity: number;
  total_actual_kw: number;
  // null for V2-telemetry companies (actuals only, no projected baseline yet).
  total_expected_kw: number | null;
  actual_vs_expected: number | null;
  // False for V2 companies: the UI shows "N/A" instead of a misleading 0%.
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
  alerts_overview: AlertsOverview | null;
}

interface OMCompaniesResponse {
  skip: number;
  limit: number;
  total: number;
  items: OMCompanyInfo[];
}

interface companyAlertsResponse {
  skip: number;
  limit: number;
  total: number;
  items: AlertInfo[];
}

interface AlertInfo {
  id: number;
  device_id: number;
  is_resolved: false;
  type: string;
  severity: string;
  error_message: string;
  alert_start: string;
}

interface OMCompanyDetails {
  id: number;
  name: string;
  actual_production_section: {
    total_sites: number;
    total_actual_kw: number;
    total_expected_kw: number;
    total_system_size_ac: number;
    total_system_size_dc: number;
    actual_vs_expected: number;
    weather: 'Sunny' | 'Cloudy' | 'Partly cloudy';
  };
  alerts_section: [
    {
      id: number;
      severity: string;
      alert_start: string;
      type: string;
    }
  ];
  alerts_summary_section: [
    {
      severity: string;
      total: number;
      unaccomplished_tasks_count: number;
    }
  ];
  actual_vs_expected_section: [
    {
      id: number;
      name: string;
      actual_kw: number;
      expected_kw: number;
      size: 1;
    }
  ];
  day_losses_section: {
    cumulative: number;
    curtailment: number;
    downtime: number;
    expected: number;
    loss: number;
    snow: number;
    soiling: number;
    unclassified: number;
  };
}

interface OMSiteDetails {
  id: number;
  name: string;
  actual_production_section: {
    actual_kw: number;
    expected_kw: number;
    actual_vs_expected: number;
    system_size_ac: number;
    system_size_dc: number;
    performance_index: number;
    weather: 'Sunny' | 'Cloudy' | 'Partly cloudy';
  };
  inverters_performance_section: [
    {
      name: string;
      performance: number;
    }
  ];
  devices_section: [
    {
      device_type: string;
      devices: number;
      critical_errors: number;
      no_respond: number;
    }
  ];
  actual_vs_expected_section: [];
  past_performance_section: object;
}

interface OMDeviceDetails {
  id: number;
  name: string;
  general_info: {
    asset_id: string;
    status: string;
    name: string;
    category: string;
    type: string;
    manufacturer: string;
    model: string;
    serial_number: string;
    warranty_effective_date: string;
    warranty_term: string;
    gateway_id: string;
    function_id: string;
    driver: string;
    install_date: string;
    decommissioned_date: string;
    last_updated_date: string | null;
  };
  performance_details: any[];
}

interface ResolveAlertResponse {
  message: string;
  code: number;
}

interface OMCompanySitesParams {
  skip?: number;
  limit?: number;
}

interface OMSiteInfo {
  id: number;
  name: string;
  actual_kw: number | null;
  expected_kw: number | null;
  // Native observed condition (dual-run). Legacy string/OMSiteWeather shapes are
  // tolerated for back-compat but are no longer produced by the backend.
  weather: ObservedCondition | OMSiteWeather | string | null;
  actual_vs_expected: number | null;
  cumulative_vs_expected: number | null;
  cumulative_7_days_vs_expected: number | null;
  cumulative_30_days_vs_expected: number | null;
  das_connection_status: 'Not Connected' | 'Connected';
  alerts_overview: {
    severity: string;
    total: number;
  } | null;
}

interface OMCompanySitesResponse {
  skip: number;
  limit: number;
  total: number;
  items: OMSiteInfo[];
}

interface OMDevicesBySiteParams {
  skip?: number;
  limit?: number;
}

interface OMDeviceInfo {
  id: number;
  asset_id: string;
  name: string;
  type:
    | 'String'
    | 'Micro Inverter'
    | 'Power Optimizers'
    | 'Canopy'
    | 'Carport'
    | 'Dual Axis'
    | 'Fixed Tilt'
    | 'Single Axis';
  category: 'Inverter' | 'Rack Mount';
  main_metric: number;
  last_reported: string;
  lifetime: number;
  warranty_period: string;
  alerts_overview: {
    severity: string;
    total: number;
  } | null;
}
interface OMDevicesBySiteResponse {
  skip: number;
  limit: number;
  total: number;
  items: OMDeviceInfo[];
}

interface SecurityCamerasResponse {
  items: [
    {
      name: string;
      uuid: string;
      location: string;
      status: string;
    }
  ];
}

interface SecurityCamerasUrlResponse {
  live_stream_url: string;
}

interface OMSiteAlert {
  alert_uuid: string;
  alert_type: string;
  camera_name: string;
  timestamp: string;
}

interface OMSiteAlertsResponse {
  skip: number;
  limit: number;
  total: number;
  items: OMSiteAlert[];
}

interface SecurityAlertCamerasUrlResponse {
  shared_clip_url: string;
}

interface OMCompanyDashboardProductionResponse {
  id: number;
  total_sites: number;
  total_actual_kw: number;
  // null for V2-telemetry companies (actuals only, no projected baseline yet).
  total_expected_kw: number | null;
  total_system_size_ac: number;
  total_system_size_dc: number;
  actual_vs_expected: number;
  // False for V2 companies; the chart shows "N/A" / "Baseline not available".
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
  cumulative_actual_kw: number;
  cumulative_expected_kw: number | null;
  cumulative_actual_vs_expected: number;
}

/** @deprecated Legacy Weatherstack icon/description shape; superseded by ObservedCondition. */
interface OMSiteWeather {
  weather_description: string;
  weather_icon_url: string;
}

interface OMSiteDashboardProductionResponse {
  actual_kw: number;
  actual_vs_expected: number;
  // null for V2 telemetry sites, which carry actual-only data (no projection).
  expected_kw: number | null;
  performance_index: number;
  system_size_ac: number;
  system_size_dc: number;
  weather: ObservedCondition | OMSiteWeather | string | null;
  cumulative_actual_kw: number;
  cumulative_expected_kw: number | null;
  cumulative_actual_vs_expected: number;
  // True when an expected/projected baseline exists (BigQuery sites); false for
  // actual-only V2 telemetry sites, where the UI shows "N/A" / "Baseline not
  // available" instead of a misleading 0% / 0 kW.
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
}

interface OMCompanyActualVsExpectedProductionEntry {
  id: number;
  name: string;
  actual_kw: number | null;
  expected_kw: number | null;
  size: number | null;
}

interface OMCompanyActualVsExpectedProductionResponse {
  items: OMCompanyActualVsExpectedProductionEntry[];
  // False for V2 companies: per-site expected is null, so the bubble chart shows
  // a "Baseline not available" note instead of misleading zero-expected points.
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
}

interface OMCompanyDayLosesEntryResponse {
  cumulative: number;
  // null for V2-telemetry companies: no expected baseline, so loss cannot be
  // computed and is returned as null rather than a misleading 0.
  expected: number | null;
  loss: number | null;
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
}

interface OMSiteInvertersPerformanceEntry {
  name: string;
  performance: number | string | null;
  actual: number | string | null;
}

interface OMSiteInvertersPerformanceResponse {
  data: OMSiteInvertersPerformanceEntry[];
}

interface OMSitePastPerformanceResponse {
  data: { [key: string]: number };
  // False for V2 sites: daily past-performance is an actual-vs-expected ratio,
  // and V2 carries no expected baseline, so the widget shows a no-baseline note.
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
}

interface OMSiteActualVsExpectedProductionEntry {
  period: string;
  actual: number;
  // V2 telemetry has no projected/"expected" baseline, so V2-driven points
  // return null here; BigQuery-driven points still return a number.
  expected: number | null;
  irradiance: number;
}

interface OMSiteActualVsExpectedProductionResponse {
  data: OMSiteActualVsExpectedProductionEntry[];
  // False for V2 sites; the chart then shows the Actual line only plus a note.
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
  // Additive (fail-closed physics validation, validated ON READ): true when the
  // active baseline EXISTS but is physically invalid, so per-point expected is
  // null and the UI shows the replacement banner (actuals stay visible). The
  // summary explains why and `invalid_baseline_id` deep-links to the replacement
  // flow. All absent / no-op on legacy + valid-baseline responses.
  baseline_invalid?: boolean;
  invalid_baseline_id?: number | null;
  baseline_validation_summary?: string | null;
  baseline_validation_policy_version?: string | null;
  required_action?: string | null;
}

interface OMSiteDevicesOverviewEntry {
  device_type: string;
  devices: number;
  critical_errors: number;
  no_respond: number;
}

interface OMSiteDevicesOverviewResponse {
  data: OMSiteDevicesOverviewEntry[];
}

export const buildOperationsAndMaintenanceApi = (httpClient: AxiosInstance) => {
  const companies = async (params: Params): Promise<OMCompaniesResponse> => {
    const response = await httpClient.get<OMCompaniesResponse>('/api/operations-and-maintenance/companies/', {
      params
    });
    return response.data;
  };

  const companyAlerts = async (companyId: number, params: Params): Promise<companyAlertsResponse> => {
    const response = await httpClient.get<companyAlertsResponse>(
      `/api/operations-and-maintenance/alerts/companies/${companyId}`,
      {
        params
      }
    );
    return response.data;
  };

  const siteAlerts = async (siteId: number, params: Params): Promise<companyAlertsResponse> => {
    const response = await httpClient.get<companyAlertsResponse>(
      `/api/operations-and-maintenance/alerts/sites/${siteId}`,
      {
        params
      }
    );
    return response.data;
  };

  const deviceAlerts = async (deviceId: number, params: Params): Promise<companyAlertsResponse> => {
    const response = await httpClient.get<companyAlertsResponse>(
      `/api/operations-and-maintenance/alerts/devices/${deviceId}`,
      {
        params
      }
    );
    return response.data;
  };

  const companyAlertResolve = async (alertId: number): Promise<ResolveAlertResponse> => {
    const response = await httpClient.put<ResolveAlertResponse>(
      `/api/operations-and-maintenance/alerts/${alertId}/resolve`,
      {}
    );
    return response.data;
  };

  const getCompanyById = async (companyId: number): Promise<OMCompanyDetails> => {
    const response = await httpClient.get<OMCompanyDetails>(`/api/operations-and-maintenance/companies/${companyId}`);
    return response.data;
  };

  const companySites = async (companyId: number, params: OMCompanySitesParams): Promise<OMCompanySitesResponse> => {
    const response = await httpClient.get<OMCompanySitesResponse>(
      `/api/operations-and-maintenance/companies/${companyId}/sites`,
      {
        params
      }
    );
    return response.data;
  };

  const getSiteById = async (siteId: number): Promise<OMSiteDetails> => {
    const response = await httpClient.get<OMSiteDetails>(`/api/operations-and-maintenance/sites/${siteId}`);
    return response.data;
  };

  const getCamerasById = async (siteId: number): Promise<SecurityCamerasResponse> => {
    const response = await httpClient.get<SecurityCamerasResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/cameras`
    );
    return response.data;
  };

  const getCamerasUrlById = async (siteId: number, camera_uuid: number): Promise<SecurityCamerasUrlResponse> => {
    const response = await httpClient.get<SecurityCamerasUrlResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/cameras/${camera_uuid}/livestream`
    );
    return response.data;
  };

  const devicesBySite = async (siteId: number, params: OMDevicesBySiteParams): Promise<OMDevicesBySiteResponse> => {
    const response = await httpClient.get<OMDevicesBySiteResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/devices`,
      {
        params
      }
    );
    return response.data;
  };

  const alertsBySite = async (siteId: number): Promise<OMSiteAlertsResponse> => {
    const response = await httpClient.get<OMSiteAlertsResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/cameras/alerts`
    );
    return response.data;
  };

  const getCamerasUrlByAlertId = async (
    siteId: number,
    alert_uuid: number
  ): Promise<SecurityAlertCamerasUrlResponse> => {
    const response = await httpClient.get<SecurityAlertCamerasUrlResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/cameras/alerts/${alert_uuid}/shared-clip`
    );
    return response.data;
  };

  const getDeviceById = async (deviceId: number): Promise<OMDeviceDetails> => {
    const response = await httpClient.get<OMDeviceDetails>(`/api/operations-and-maintenance/devices/${deviceId}`);
    return response.data;
  };

  const getCompanyDashboardProduction = async (companyId: number): Promise<OMCompanyDashboardProductionResponse> => {
    const response = await httpClient.get<OMCompanyDashboardProductionResponse>(
      `/api/operations-and-maintenance/companies/${companyId}/actual-production-chart`
    );
    return response.data;
  };

  const getSiteDashboardProduction = async (siteId: number): Promise<OMSiteDashboardProductionResponse> => {
    const response = await httpClient.get<OMSiteDashboardProductionResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/actual-production-chart`
    );
    return response.data;
  };

  const companyActualVsExpectedProductionData = async (
    companyId: number
  ): Promise<OMCompanyActualVsExpectedProductionResponse> => {
    const response = await httpClient.get<OMCompanyActualVsExpectedProductionResponse>(
      `/api/operations-and-maintenance/companies/${companyId}/actual-vs-expected-production-chart`
    );
    return response.data;
  };

  const companyLosesData = async (companyId: number): Promise<OMCompanyDayLosesEntryResponse> => {
    const response = await httpClient.get<OMCompanyDayLosesEntryResponse>(
      `/api/operations-and-maintenance/companies/${companyId}/loses-for-a-day-chart`
    );
    return response.data;
  };

  const siteInvertersPerformanceData = async (siteId: number): Promise<OMSiteInvertersPerformanceResponse> => {
    const response = await httpClient.get<OMSiteInvertersPerformanceResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/inverters-performance-chart`
    );
    return response.data;
  };

  const sitePastPerformance = async (siteId: number): Promise<OMSitePastPerformanceResponse> => {
    const response = await httpClient.get<OMSitePastPerformanceResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/past-performance-chart`
    );
    return response.data;
  };

  const siteActualVsExpectedProduction = async (siteId: number): Promise<OMSiteActualVsExpectedProductionResponse> => {
    const response = await httpClient.get<OMSiteActualVsExpectedProductionResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/actual-vs-expected-chart`
    );
    return response.data;
  };

  const siteDevicesOverviewSection = async (siteId: number): Promise<OMSiteDevicesOverviewResponse> => {
    const response = await httpClient.get<OMSiteDevicesOverviewResponse>(
      `/api/operations-and-maintenance/sites/${siteId}/devices-overview-section`
    );
    return response.data;
  };

  return Object.freeze({
    companies,
    getCompanyById,
    companyAlerts,
    companyAlertResolve,
    siteAlerts,
    companySites,
    getSiteById,
    devicesBySite,
    getDeviceById,
    deviceAlerts,
    getCamerasById,
    getCamerasUrlById,
    alertsBySite,
    getCamerasUrlByAlertId,
    getCompanyDashboardProduction,
    getSiteDashboardProduction,
    companyActualVsExpectedProductionData,
    siteInvertersPerformanceData,
    sitePastPerformance,
    siteActualVsExpectedProduction,
    companyLosesData,
    siteDevicesOverviewSection
  });
};

export type { OMCompanyDetails, OMSiteDetails, OMDeviceDetails };
