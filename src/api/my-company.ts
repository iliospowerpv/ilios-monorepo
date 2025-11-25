import type { AxiosInstance } from 'axios';
import type { Params } from './user';
import { SiteDetailedInfo } from './asset-management';

interface CompanyDetails {
  name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  company_type: string;
  id: number;
  total_sites: number;
  sites_placed_in_service: number;
  sites_under_construction: number;
  total_capacity: number;
  sites_decommissioned: number;
  sites_sold: number;
}

interface Site {
  id: number;
  name: string;
  address: string;
}
interface Sites {
  skip: number;
  limit: number;
  total: number;
  items: Site[];
}
interface CompanyUsersQueryParams {
  search?: string;
  skip?: number;
  limit?: number;
  order_by?: 'first_name' | 'last_name' | 'email' | 'role';
  order_direction?: 'asc' | 'desc';
}

interface CompanyUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string | null;
  is_registered: boolean;
  parent_company_id: number | null;
  phone: string;
}
interface CompanyUsersResponse {
  skip: number;
  limit: number;
  total: number;
  items: CompanyUser[];
}

export const buildMyCompanyApi = (httpClient: AxiosInstance) => {
  const getMyCompany = async (): Promise<CompanyDetails> => {
    const response = await httpClient.get<CompanyDetails>('/api/my-company/');
    return response.data;
  };

  const getMyCompanySites = async (params: Params): Promise<Sites> => {
    const response = await httpClient.get<Sites>('/api/my-company/sites', { params });
    return response.data;
  };

  const getMyCompanySiteById = async (siteId: number): Promise<SiteDetailedInfo> => {
    const response = await httpClient.get<SiteDetailedInfo>(`/api/my-company/sites/${siteId}`);
    return response.data;
  };

  const getMyCompanyUsers = async (params: CompanyUsersQueryParams): Promise<CompanyUsersResponse> => {
    const response = await httpClient.get<CompanyUsersResponse>('/api/my-company/users', { params });
    return response.data;
  };

  return Object.freeze({
    getMyCompany,
    getMyCompanySites,
    getMyCompanySiteById,
    getMyCompanyUsers
  });
};

export type { CompanyDetails, Sites };
