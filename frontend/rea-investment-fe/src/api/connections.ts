import type { AxiosInstance } from 'axios';

interface Connection {
  id?: number;
  provider?: string;
  name: string;
  token?: string | null;
  username?: string | null;
  password?: string | null;
  share_with_portfolio?: boolean;
  isEditing?: boolean;
  isNotSaved?: boolean;
}

interface Connections {
  items: Connection[];
}

interface AvailableConnection {
  id: number;
  name: string;
  provider: string;
  company_id: number;
  company_name: string;
  owner_type: string;
  owner_company_id: number | null;
  owner_company_name: string | null;
  last_test_at: string | null;
  last_test_status: string | null;
  last_test_message: string | null;
}

interface AvailableConnectionsResponse {
  company_connections: AvailableConnection[];
  portfolio_connections: AvailableConnection[];
}

interface ConnectionResponse {
  message: string;
  code: number;
}

interface SiteMapping {
  id: number;
  name: string;
}

interface Sites {
  items: SiteMapping[];
}

interface CreateSiteMappingAttributes {
  connection_id: number | undefined;
  telemetry_site_id: string | undefined;
  telemetry_site_name: string | undefined;
}

interface ConnectionTestPayload {
  provider: string;
  token?: string | null;
  username?: string | null;
  password?: string | null;
}

interface ConnectionTestResponse {
  success: boolean;
  message: string;
  available_sites_count: number | null;
  provider: string;
}

type TelemetryHealthStatus = 'HEALTHY' | 'WARN' | 'ERROR' | 'NO_DATA' | 'NOT_CONFIGURED';

interface TelemetryHealthResponse {
  status: TelemetryHealthStatus;
  last_data_at: string | null;
  data_delay_minutes: number | null;
  last_error: string | null;
  mapped_device_count: number;
  expected_interval_minutes: number;
  is_connected: boolean;
  is_site_mapped: boolean;
}

interface TelemetryReadinessResponse {
  is_connected: boolean;
  is_site_mapped: boolean;
  is_devices_mapped: boolean;
  is_data_flowing: boolean;
  connection_id: number | null;
  connection_name: string | null;
  provider: string | null;
  telemetry_site_id: string | null;
  telemetry_site_name: string | null;
  mapped_device_count: number;
  total_eligible_device_count: number;
}

interface TelemetryDevice {
  id: string;
  name: string;
}

interface TelemetryDevicesResponse {
  items: TelemetryDevice[];
}

interface EligibleDevice {
  id: number;
  name: string;
  category: string | null;
  serial_number: string | null;
  is_mapped: boolean;
  telemetry_device_id: string | null;
  telemetry_device_name: string | null;
}

interface EligibleDevicesResponse {
  items: EligibleDevice[];
  total: number;
}

interface DeviceMapping {
  device_id: number;
  telemetry_device_id: string;
  telemetry_device_name: string;
}

interface BulkDeviceMappingPayload {
  mappings: DeviceMapping[];
}

interface BulkDeviceMappingResponse {
  code: number;
  message: string;
  successful_count: number;
  failed_count: number;
  errors: string[] | null;
}

interface CompanyProvider {
  provider: string;
  provider_display: string;
  connection_count?: number;
}

interface CompanyProvidersResponse {
  items: CompanyProvider[];
}

export const buildConnectionsApi = (httpClient: AxiosInstance) => {
  const getConnections = async (companyId: number): Promise<Connections> => {
    // Returns connections grouped by ownership; flatten into a single list for the wizard.
    const response = await httpClient.get<AvailableConnectionsResponse>(
      `/api/telemetry/connections/available?company_id=${companyId}`
    );
    const grouped = response.data;
    const items: Connection[] = [
      ...grouped.company_connections.map(c => ({ id: c.id, name: c.name, provider: c.provider })),
      ...grouped.portfolio_connections.map(c => ({ id: c.id, name: c.name, provider: c.provider }))
    ];
    return { items };
  };

  const getAvailableConnections = async (companyId: number): Promise<AvailableConnectionsResponse> => {
    const response = await httpClient.get<AvailableConnectionsResponse>(
      `/api/telemetry/connections/available?company_id=${companyId}`
    );
    return response.data;
  };

  const createConnection = async (companyId: number, attributes: Connection): Promise<ConnectionResponse> => {
    const response = await httpClient.post<ConnectionResponse>(
      `/api/telemetry/companies/${companyId}/connections`,
      attributes
    );
    return response.data;
  };

  const updateConnection = async (
    companyId: number,
    connectionId: number | undefined,
    attributes: Connection
  ): Promise<ConnectionResponse> => {
    const response = await httpClient.put<ConnectionResponse>(
      `/api/telemetry/companies/${companyId}/connections/${connectionId}`,
      attributes
    );
    return response.data;
  };

  const deleteConnection = async (companyId: number, connectionId: number | undefined): Promise<ConnectionResponse> => {
    const response = await httpClient.delete<ConnectionResponse>(
      `/api/telemetry/companies/${companyId}/connections/${connectionId}`
    );
    return response.data;
  };

  const getSites = async (companyId: number, connectionId: number): Promise<Sites> => {
    const response = await httpClient.get<Sites>(
      `/api/telemetry/companies/${companyId}/connections/${connectionId}/sites`
    );
    return response.data;
  };

  const createSiteMapping = async (
    siteId: number | undefined,
    attributes: CreateSiteMappingAttributes
  ): Promise<ConnectionResponse> => {
    const response = await httpClient.post<ConnectionResponse>(`/api/telemetry/sites/${siteId}/mapping`, attributes);
    return response.data;
  };

  const testConnection = async (payload: ConnectionTestPayload): Promise<ConnectionTestResponse> => {
    const response = await httpClient.post<ConnectionTestResponse>('/api/telemetry/connections/test', payload);
    return response.data;
  };

  const getTelemetryHealth = async (siteId: number): Promise<TelemetryHealthResponse> => {
    const response = await httpClient.get<TelemetryHealthResponse>(`/api/telemetry/sites/${siteId}/health`);
    return response.data;
  };

  const getTelemetryReadiness = async (siteId: number): Promise<TelemetryReadinessResponse> => {
    const response = await httpClient.get<TelemetryReadinessResponse>(`/api/telemetry/sites/${siteId}/readiness`);
    return response.data;
  };

  const getTelemetryDevices = async (siteId: number): Promise<TelemetryDevicesResponse> => {
    const response = await httpClient.get<TelemetryDevicesResponse>(`/api/telemetry/sites/${siteId}/devices`);
    return response.data;
  };

  const getEligibleDevices = async (siteId: number): Promise<EligibleDevicesResponse> => {
    const response = await httpClient.get<EligibleDevicesResponse>(`/api/telemetry/sites/${siteId}/eligible-devices`);
    return response.data;
  };

  const updateSiteMapping = async (
    siteId: number,
    attributes: CreateSiteMappingAttributes
  ): Promise<ConnectionResponse> => {
    const response = await httpClient.put<ConnectionResponse>(`/api/telemetry/sites/${siteId}/mapping`, attributes);
    return response.data;
  };

  const deleteSiteMapping = async (siteId: number): Promise<ConnectionResponse> => {
    const response = await httpClient.delete<ConnectionResponse>(`/api/telemetry/sites/${siteId}/mapping`);
    return response.data;
  };

  const bulkMapDevices = async (
    siteId: number,
    payload: BulkDeviceMappingPayload
  ): Promise<BulkDeviceMappingResponse> => {
    const response = await httpClient.post<BulkDeviceMappingResponse>(
      `/api/telemetry/sites/${siteId}/devices/bulk-mapping`,
      payload
    );
    return response.data;
  };

  const deleteDeviceMapping = async (deviceId: number): Promise<ConnectionResponse> => {
    const response = await httpClient.delete<ConnectionResponse>(`/api/telemetry/devices/${deviceId}/mapping`);
    return response.data;
  };

  const getCompanyProviders = async (companyId: number): Promise<CompanyProvidersResponse> => {
    const response = await httpClient.get<CompanyProvidersResponse>(`/api/telemetry/companies/${companyId}/providers`);
    return response.data;
  };

  const assignCompanyProvider = async (companyId: number, provider: string): Promise<ConnectionResponse> => {
    const response = await httpClient.post<ConnectionResponse>(`/api/telemetry/companies/${companyId}/providers`, {
      provider
    });
    return response.data;
  };

  const removeCompanyProvider = async (companyId: number, provider: string): Promise<ConnectionResponse> => {
    const url = `/api/telemetry/companies/${companyId}/providers/${provider}`;
    const response = await httpClient.delete<ConnectionResponse>(url);
    return response.data;
  };

  return Object.freeze({
    getConnections,
    getAvailableConnections,
    createConnection,
    updateConnection,
    deleteConnection,
    getSites,
    createSiteMapping,
    testConnection,
    getTelemetryHealth,
    getTelemetryReadiness,
    getTelemetryDevices,
    getEligibleDevices,
    updateSiteMapping,
    deleteSiteMapping,
    bulkMapDevices,
    deleteDeviceMapping,
    getCompanyProviders,
    assignCompanyProvider,
    removeCompanyProvider
  });
};

export type {
  Connection,
  Connections,
  ConnectionResponse,
  CreateSiteMappingAttributes,
  SiteMapping,
  ConnectionTestPayload,
  ConnectionTestResponse,
  TelemetryHealthStatus,
  TelemetryHealthResponse,
  TelemetryReadinessResponse,
  TelemetryDevice,
  TelemetryDevicesResponse,
  EligibleDevice,
  EligibleDevicesResponse,
  DeviceMapping,
  BulkDeviceMappingPayload,
  BulkDeviceMappingResponse,
  CompanyProvider,
  CompanyProvidersResponse
};
