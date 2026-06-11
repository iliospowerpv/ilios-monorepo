import { AxiosInstance } from 'axios';

import type { ExpectedState } from '../utils/telemetry/expectedState';

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
  // null for V2-telemetry companies (actuals only, no projected baseline yet).
  total_expected_kw: number | null;
  actual_vs_expected: number | null;
  // False for V2 companies: the UI shows "N/A" instead of a misleading 0%.
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
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
  // null for V2-telemetry companies (actuals only, no projected baseline yet).
  total_expected_kw: number | null;
  total_system_size_ac: number;
  total_system_size_dc: number;
  actual_vs_expected: number | null;
  cumulative_actual_kw: number;
  cumulative_expected_kw: number | null;
  cumulative_actual_vs_expected: number;
  // False for V2 companies; the chart shows "N/A" / "Baseline not available".
  expected_baseline_available: boolean;
  // Additive V2 metadata; absent on legacy responses (see resolveExpectedState).
  expected_state?: ExpectedState;
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
