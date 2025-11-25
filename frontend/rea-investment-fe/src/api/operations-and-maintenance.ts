import { AxiosInstance } from 'axios';

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
  total_expected_kw: number;
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
  weather: OMSiteWeather | string | null;
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
  total_expected_kw: number;
  total_system_size_ac: number;
  total_system_size_dc: number;
  actual_vs_expected: number;
  cumulative_actual_kw: number;
  cumulative_expected_kw: number;
  cumulative_actual_vs_expected: number;
}

interface OMSiteWeather {
  weather_description: string;
  weather_icon_url: string;
}

interface OMSiteDashboardProductionResponse {
  actual_kw: number;
  actual_vs_expected: number;
  expected_kw: number;
  performance_index: number;
  system_size_ac: number;
  system_size_dc: number;
  weather: OMSiteWeather | string | null;
  cumulative_actual_kw: number;
  cumulative_expected_kw: number;
  cumulative_actual_vs_expected: number;
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
}

interface OMCompanyDayLosesEntryResponse {
  cumulative: number;
  expected: number;
  loss: number;
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
}

interface OMSiteActualVsExpectedProductionEntry {
  period: string;
  actual: number;
  expected: number;
  irradiance: number;
}

interface OMSiteActualVsExpectedProductionResponse {
  data: OMSiteActualVsExpectedProductionEntry[];
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
