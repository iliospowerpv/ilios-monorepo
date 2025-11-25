import type { AxiosInstance } from 'axios';

interface Site {
  id: number;
  name: string;
}

interface CompanySites {
  id: number;
  name: string;
  sites: Site[];
}

interface CompaniesSitesData {
  data: CompanySites[];
}

interface CreateCompanyAttributes {
  company_type: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
}

interface EditCompanyAttributes {
  name: string;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
}

type CompanyAttributes = CreateCompanyAttributes | EditCompanyAttributes;

interface CreateCompanyResponse {
  message: string;
  code: number;
}

enum OrderBy {
  Name = 'name',
  CompanyType = 'company_type',
  Address = 'address',
  Email = 'email'
}

enum OrderDirection {
  ASC = 'asc',
  DESC = 'desc'
}

interface ContractorsQueryArgs {
  search?: string;
  skip?: number;
  limit?: number;
  order_by?: OrderBy;
  order_direction?: OrderDirection;
}

interface Company {
  name: string;
  email: string;
  phone: string;
  address: string;
  company_type: string;
  id: number;
}

interface GetContractorsResponse {
  skip: number;
  limit: number;
  total: number;
  items: Company[];
}

interface Role {
  id: number;
  name: string;
}

interface RoleWithCompanyType {
  company_type: string;
  role: Role;
}

interface GetRolesWithCompanyTypeResponse {
  data: RoleWithCompanyType[];
}

export const buildCompaniesApi = (httpClient: AxiosInstance) => {
  const sites = async (): Promise<CompaniesSitesData> => {
    const response = await httpClient.get<CompaniesSitesData>('/api/companies/sites');
    return response.data;
  };

  const company = async (id: number): Promise<Company> => {
    const response = await httpClient.get<Company>(`/api/companies/${id}`);
    return response.data;
  };

  const create = async (attributes: CompanyAttributes): Promise<CreateCompanyResponse> => {
    const response = await httpClient.post<CreateCompanyResponse>('/api/contractors/', attributes);
    return response.data;
  };

  const update = async (id: number | undefined, attributes: CompanyAttributes): Promise<CreateCompanyResponse> => {
    const response = await httpClient.put<CreateCompanyResponse>(`/api/contractors/${id}`, attributes);
    return response.data;
  };

  const contractors = async (args: ContractorsQueryArgs): Promise<GetContractorsResponse> => {
    const response = await httpClient.get<GetContractorsResponse>('/api/contractors/', { params: args });
    return response.data;
  };

  const rolesWithCompanyType = async (): Promise<GetRolesWithCompanyTypeResponse> => {
    const response = await httpClient.get<GetRolesWithCompanyTypeResponse>('/api/roles/with-company-type');
    return response.data;
  };

  return Object.freeze({
    sites,
    create,
    update,
    company,
    contractors,
    rolesWithCompanyType
  });
};

export type { Site as CompanySite, CompanySites, CompanyAttributes, Company as ContractorCompany };
