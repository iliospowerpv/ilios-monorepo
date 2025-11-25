import type { AxiosInstance } from 'axios';

interface Connection {
  id?: number;
  provider?: string;
  name: string;
  token?: string | null;
  username?: string | null;
  password?: string | null;
  isEditing?: boolean;
  isNotSaved?: boolean;
}

interface Connections {
  items: Connection[];
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
  telemetry_site_id: number | undefined;
  telemetry_site_name: string | undefined;
}

export const buildConnectionsApi = (httpClient: AxiosInstance) => {
  const getConnections = async (companyId: number): Promise<Connections> => {
    const response = await httpClient.get<Connections>(`/api/contractors/${companyId}/connections/`);
    return response.data;
  };

  const createConnection = async (companyId: number, attributes: Connection): Promise<ConnectionResponse> => {
    const response = await httpClient.post<ConnectionResponse>(
      `/api/contractors/${companyId}/connections/`,
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
      `/api/contractors/${companyId}/connections/${connectionId}`,
      attributes
    );
    return response.data;
  };

  const deleteConnection = async (companyId: number, connectionId: number | undefined): Promise<ConnectionResponse> => {
    const response = await httpClient.delete<ConnectionResponse>(
      `/api/contractors/${companyId}/connections/${connectionId}`
    );
    return response.data;
  };

  const getSites = async (companyId: number, connectionId: number): Promise<Sites> => {
    const response = await httpClient.get<Sites>(`/api/contractors/${companyId}/connections/${connectionId}/sites`);
    return response.data;
  };

  const createSiteMapping = async (
    siteId: number | undefined,
    attributes: CreateSiteMappingAttributes
  ): Promise<ConnectionResponse> => {
    const response = await httpClient.post<ConnectionResponse>(`/api/telemetry/sites/${siteId}/mapping`, attributes);
    return response.data;
  };

  return Object.freeze({
    getConnections,
    createConnection,
    updateConnection,
    deleteConnection,
    getSites,
    createSiteMapping
  });
};

export type { Connection, Connections, ConnectionResponse, CreateSiteMappingAttributes, SiteMapping };
