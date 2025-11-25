import { AxiosInstance } from 'axios';

interface InvestorDashboardCompaniesQueryParams {
  skip: number;
  limit: number;
  order_by: 'id' | 'name' | 'total_sites' | 'total_capacity';
  order_direction: 'asc' | 'desc';
}

interface InvestorDashboardCompany {
  id: number;
  name: string;
  total_sites: number;
  total_capacity: number;
  total_actual_kw: number;
  total_expected_kw: number;
  actual_vs_expected: number | null;
}

interface InvestorDashboardCompaniesQueryResponse {
  skip: number;
  limit: number;
  total: number;
  items: InvestorDashboardCompany[];
}

interface InvestorDashboardCompanyAggregatedPerformanceQueryResponse {
  id: number;
  total_sites: number;
  total_actual_kw: number;
  total_expected_kw: number;
  total_system_size_ac: number;
  total_system_size_dc: number;
  actual_vs_expected: number | null;
  cumulative_actual_kw: number;
  cumulative_expected_kw: number;
  cumulative_actual_vs_expected: number;
}

interface InvestorDashboardSitesQueryParams {
  skip: number;
  limit: number;
}

interface InvestorDashboardSite {
  id: number;
  name: string;
  actual_kw: number | null;
  expected_kw: number | null;
  weather: string | null;
  actual_vs_expected: number | null;
  cumulative_vs_expected: number | null;
  cumulative_7_days_vs_expected: number | null;
  cumulative_30_days_vs_expected: number | null;
  das_connection_status: string;
}

interface InvestorDashboardSitesQueryResponse {
  skip: number;
  limit: number;
  total: number;
  items: InvestorDashboardSite[];
}

export const buildInvestorDashboardApi = (httpClient: AxiosInstance) => {
  const companies = async (
    params: InvestorDashboardCompaniesQueryParams
  ): Promise<InvestorDashboardCompaniesQueryResponse> => {
    const response = await httpClient.get<InvestorDashboardCompaniesQueryResponse>(
      '/api/investor-dashboard/companies',
      { params }
    );
    return response.data;
  };

  const companyAggregatedPerformance = async (
    companyId: number
  ): Promise<InvestorDashboardCompanyAggregatedPerformanceQueryResponse> => {
    const response = await httpClient.get<InvestorDashboardCompanyAggregatedPerformanceQueryResponse>(
      `/api/investor-dashboard/companies/${companyId}/actual-production`
    );
    return response.data;
  };

  const sites = async (params: InvestorDashboardSitesQueryParams): Promise<InvestorDashboardSitesQueryResponse> => {
    const response = await httpClient.get<InvestorDashboardSitesQueryResponse>(`/api/investor-dashboard/sites`, {
      params
    });
    return response.data;
  };

  return Object.freeze({
    sites,
    companies,
    companyAggregatedPerformance
  });
};
