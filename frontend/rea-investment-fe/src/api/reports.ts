import type { AxiosInstance, AxiosResponse } from 'axios';

interface Item {
  id: string;
  name: string;
}
interface ReportCompanies {
  skip: number;
  limit: number;
  total: number;
  items: Item[];
}

interface PowerBIOptions {
  id: string;
  name: string;
  web_url: string;
  embed_url: string;
}

interface PowerBIResponse {
  items: PowerBIOptions[];
}

interface PowerBITokenResponse {
  embed_token: string;
}

interface Pages {
  name: string;
}

interface PowerBIPagesResponse {
  value: Pages[];
}

interface PowerBIFileExportResponse {
  id: string;
}

interface PowerBIFileExportStatusResponse {
  id: string;
  status: string;
}

export interface PerformanceReportDailyEntry {
  date: string;
  actual_kwh: number;
  expected_kwh: number;
  performance_ratio: number;
}

export interface PerformanceReportMonthlyEntry {
  month: string;
  actual_kwh: number;
  expected_kwh: number;
  performance_ratio: number;
  days: number;
}

export interface PerformanceReportSummary {
  total_actual_kwh: number;
  total_expected_kwh: number;
  total_actual_mwh: number;
  total_expected_mwh: number;
  performance_ratio: number;
  capacity_factor: number;
  avg_daily_generation_kwh: number;
  num_days: number;
  system_capacity_kw: number;
  availability: number;
}

export interface PerformanceReportResponse {
  available: boolean;
  site_id?: number;
  site_name?: string;
  start_date?: string;
  end_date?: string;
  summary?: PerformanceReportSummary;
  daily?: PerformanceReportDailyEntry[];
  monthly?: PerformanceReportMonthlyEntry[];
  message?: string;
}

export interface PerformanceReportAvailability {
  available: boolean;
  site_id: number;
}

export const buildReportsApi = (httpClient: AxiosInstance) => {
  const getCompanyList = async (
    search?: string,
    skip?: number,
    limit?: number,
    order_by?: string,
    order_direction?: string
  ): Promise<ReportCompanies> => {
    const payload: any = {
      skip: skip ? skip : 0,
      limit: limit ? limit : 1000,
      order_by: order_by ? order_by : 'name',
      order_direction: order_direction ? order_direction : 'asc',
      search: search ? search : ''
    };
    const response = await httpClient.get<ReportCompanies>(
      `/api/reporting/companies?skip=${payload.skip}&limit=${payload.limit}&order_by=${payload.order_by}&order_direction=${payload.order_direction}&search=${payload.search}`,
      payload
    );
    return response.data;
  };

  const getSiteList = async (
    companyId: string,
    search?: string,
    skip?: number,
    limit?: number,
    order_by?: string,
    order_direction?: string
  ): Promise<ReportCompanies> => {
    const payload: any = {
      skip: skip ? skip : 0,
      limit: limit ? limit : 1000,
      order_by: order_by ? order_by : 'name',
      order_direction: order_direction ? order_direction : 'asc',
      search: search ? search : ''
    };
    const response = await httpClient.get<ReportCompanies>(
      `/api/reporting/companies/${companyId}/sites?skip=${payload.skip}&limit=${payload.limit}&order_by=${payload.order_by}&order_direction=${payload.order_direction}&search=${payload.search}`
    );
    return response.data;
  };

  const getReportsOption = async (): Promise<PowerBIResponse> => {
    const response = await httpClient.get<PowerBIResponse>('/api/reporting/reports');
    return response.data;
  };

  const getReportToken = async (reportId: string): Promise<PowerBITokenResponse> => {
    const response = await httpClient.get<PowerBITokenResponse>(
      `/api/reporting/reports/${reportId}/generate-embedding-token`
    );
    return response.data;
  };

  const getPages = async (reportId: string): Promise<PowerBIPagesResponse> => {
    const response = await httpClient.get<PowerBIPagesResponse>(`/api/reporting/reports/${reportId}/pages`);
    return response.data;
  };

  const exportToFile = async (reportId: string, body: any): Promise<PowerBIFileExportResponse> => {
    const response = await httpClient.post<PowerBIFileExportResponse>(
      `/api/reporting/reports/${reportId}/export-to-file`,
      body
    );
    return response.data;
  };

  const getStatus = async (reportId: string, exportId: string): Promise<PowerBIFileExportStatusResponse> => {
    const response = await httpClient.get<PowerBIFileExportStatusResponse>(
      `/api/reporting/reports/${reportId}/exports/${exportId}/status`
    );
    return response.data;
  };

  const getFile = async (reportId: string, exportId: string): Promise<Blob> => {
    const response: AxiosResponse<ArrayBuffer> = await httpClient.get(
      `/api/reporting/reports/${reportId}/exports/${exportId}/file`,
      { responseType: 'arraybuffer' }
    );
    return new Blob([response.data], { type: 'application/pdf' });
  };

  const getPerformanceReport = async (
    siteId: number,
    startDate: string,
    endDate: string
  ): Promise<PerformanceReportResponse> => {
    const response = await httpClient.get<PerformanceReportResponse>(
      `/api/reporting/sites/${siteId}/performance-report/`,
      { params: { start_date: startDate, end_date: endDate } }
    );
    return response.data;
  };

  const checkPerformanceReportAvailability = async (siteId: number): Promise<PerformanceReportAvailability> => {
    const response = await httpClient.get<PerformanceReportAvailability>(
      `/api/reporting/sites/${siteId}/performance-report/check/`
    );
    return response.data;
  };

  return Object.freeze({
    getCompanyList,
    getSiteList,
    getReportsOption,
    getReportToken,
    getPages,
    exportToFile,
    getStatus,
    getFile,
    getPerformanceReport,
    checkPerformanceReportAvailability
  });
};

export type { ReportCompanies, PowerBIPagesResponse, PowerBIFileExportResponse };
