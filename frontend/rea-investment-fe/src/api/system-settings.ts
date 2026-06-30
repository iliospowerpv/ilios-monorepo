import type { AxiosInstance } from 'axios';

export interface ServiceStatus {
  key: string;
  name: string;
  purpose: string;
  category: string;
  required: boolean;
  configured: boolean;
  config_source: string[];
  reachable: boolean | null;
  last_checked: string | null;
  error_summary: string | null;
  notes: string | null;
}

export interface ServiceHealthResponse {
  services: ServiceStatus[];
  generated_at: string;
  total_count: number;
  configured_count: number;
  probed_count: number;
}

export interface ColumnInfo {
  name: string;
  data_type: string;
  is_nullable: boolean;
}

export interface TableInfo {
  name: string;
  column_count: number;
  columns: ColumnInfo[];
}

export interface DatabaseStructureResponse {
  schema_name: string;
  table_count: number;
  tables: TableInfo[];
}

export interface DocSummary {
  key: string;
  title: string;
  path: string;
  size_bytes: number;
}

export interface DocListResponse {
  documents: DocSummary[];
}

export interface DocContentResponse {
  key: string;
  title: string;
  path: string;
  content: string;
  truncated: boolean;
}

export const buildSystemSettingsApi = (httpClient: AxiosInstance) => {
  const getServiceHealth = async (): Promise<ServiceHealthResponse> => {
    const response = await httpClient.get<ServiceHealthResponse>('/api/settings/service-health/');
    return response.data;
  };

  const getDatabaseStructure = async (): Promise<DatabaseStructureResponse> => {
    const response = await httpClient.get<DatabaseStructureResponse>('/api/settings/architecture/database');
    return response.data;
  };

  const listArchitectureDocs = async (): Promise<DocListResponse> => {
    const response = await httpClient.get<DocListResponse>('/api/settings/architecture/docs');
    return response.data;
  };

  const getArchitectureDoc = async (docKey: string): Promise<DocContentResponse> => {
    const response = await httpClient.get<DocContentResponse>(`/api/settings/architecture/docs/${docKey}`);
    return response.data;
  };

  return Object.freeze({
    getServiceHealth,
    getDatabaseStructure,
    listArchitectureDocs,
    getArchitectureDoc
  });
};
