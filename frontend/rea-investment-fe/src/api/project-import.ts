import type { AxiosInstance } from 'axios';

export interface ColumnMapping {
  source_column: string;
  target_field: string;
}

export interface RowError {
  row: number;
  field: string;
  message: string;
}

export interface ImportRowResult {
  row: number;
  status: string;
  project_id?: number;
  project_name?: string;
  errors: RowError[];
}

export interface ParsedFileResponse {
  headers: string[];
  sample_rows: Record<string, any>[];
  total_rows: number;
  suggested_mappings: Record<string, string>;
}

export interface ValidateResponse {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  row_results: ImportRowResult[];
}

export interface ImportResultResponse {
  batch_id: string;
  total_rows: number;
  imported: number;
  skipped: number;
  failed: number;
  results: ImportRowResult[];
  source_file?: string;
}

export const TARGET_FIELDS = [
  { value: 'project_name', label: 'Project Name' },
  { value: 'address', label: 'Address' },
  { value: 'city', label: 'City' },
  { value: 'state', label: 'State' },
  { value: 'zip_code', label: 'ZIP Code' },
  { value: 'county', label: 'County' },
  { value: 'system_size_ac', label: 'System Size AC (kW)' },
  { value: 'system_size_dc', label: 'System Size DC (kW)' },
  { value: 'latitude', label: 'Latitude' },
  { value: 'longitude', label: 'Longitude' },
  { value: 'coordinates', label: 'Coordinates' },
  { value: 'lon_lat_url', label: 'Coordinates URL' },
  { value: 'status', label: 'Status' },
  { value: 'notes', label: 'Notes' }
];

export const buildProjectImportApi = (httpClient: AxiosInstance) => ({
  parseFile: async (companyId: number, file: File): Promise<ParsedFileResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await httpClient.post(`/api/projects/import/parse?company_id=${companyId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
  },

  validateImport: async (companyId: number, file: File, mappings: ColumnMapping[]): Promise<ValidateResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const mappingsJson = JSON.stringify(mappings);
    const { data } = await httpClient.post(
      `/api/projects/import/validate?company_id=${companyId}&mappings_json=${encodeURIComponent(mappingsJson)}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  },

  executeImport: async (
    companyId: number,
    file: File,
    mappings: ColumnMapping[],
    skipDuplicates = true
  ): Promise<ImportResultResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const mappingsJson = JSON.stringify(mappings);
    const { data } = await httpClient.post(
      `/api/projects/import/execute?company_id=${companyId}&mappings_json=${encodeURIComponent(mappingsJson)}&skip_duplicates=${skipDuplicates}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  }
});
