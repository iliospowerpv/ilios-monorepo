import type { AxiosInstance } from 'axios';

export interface WorkspaceSummary {
  companies_count: number;
  projects_count: number;
  pending_tasks_count: number;
  needs_attention_count: number;
}

export interface WorkspaceCompany {
  company_id: number;
  company_name: string;
  role: string | null;
  access_source: 'membership' | 'project' | 'legacy';
  project_count: number;
}

export interface WorkspaceResponse {
  summary: WorkspaceSummary;
  companies: WorkspaceCompany[];
}

export interface CompanyMember {
  membership_id: number;
  user_id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'company_admin' | 'contributor' | 'read_only';
  status: 'active' | 'invited' | 'disabled';
  access_source: string;
}

export interface PortfolioMember {
  access_id: number;
  user_id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'company_admin' | 'contributor' | 'read_only';
  status: 'active' | 'invited' | 'disabled';
  portfolio_hub_company_id: number | null;
  portfolio_hub_company_name: string | null;
}

export interface PortfolioMembersResponse {
  members: PortfolioMember[];
  total: number;
}

export interface PortfolioHub {
  hub_company_id: number;
  hub_company_name: string;
  companies_count: number;
}

export interface PortfolioHubsResponse {
  hubs: PortfolioHub[];
}

export interface AddPortfolioMemberRequest {
  user_id: number;
  portfolio_hub_company_id: number;
  role: 'company_admin' | 'contributor' | 'read_only';
}

export interface ProjectMember {
  membership_id: number | null;
  user_id: number;
  email: string;
  first_name: string;
  last_name: string;
  resolved_role: 'project_admin' | 'contributor' | 'read_only';
  resolved_status: 'active' | 'invited' | 'disabled';
  access_source: 'direct_project' | 'inherited_company' | 'inherited_portfolio';
  direct_role?: 'project_admin' | 'contributor' | 'read_only' | null;
  inherited_role?: 'project_admin' | 'contributor' | 'read_only' | null;
  has_access: boolean;
}

export interface ProjectMembersResponse {
  members: ProjectMember[];
  total: number;
}

export interface AddProjectMemberRequest {
  user_id: number;
  role: 'project_admin' | 'contributor' | 'read_only';
}

export interface AddMemberRequest {
  user_id: number;
  company_id: number;
  role: 'company_admin' | 'contributor' | 'read_only';
}

export interface UpdateMemberRequest {
  role?: 'company_admin' | 'contributor' | 'read_only';
  status?: 'active' | 'invited' | 'disabled';
}

export const buildWorkspaceApi = (httpClient: AxiosInstance) => {
  const getWorkspace = async (): Promise<WorkspaceResponse> => {
    const response = await httpClient.get<WorkspaceResponse>('/api/workspace');
    return response.data;
  };

  const getCompanyMembers = async (companyId: number): Promise<CompanyMember[]> => {
    const response = await httpClient.get<CompanyMember[]>(`/api/workspace/companies/${companyId}/members`);
    return response.data;
  };

  const addCompanyMember = async (companyId: number, request: AddMemberRequest): Promise<CompanyMember> => {
    const response = await httpClient.post<CompanyMember>(`/api/workspace/companies/${companyId}/members`, request);
    return response.data;
  };

  const updateCompanyMember = async (
    companyId: number,
    membershipId: number,
    request: UpdateMemberRequest
  ): Promise<CompanyMember> => {
    const response = await httpClient.patch<CompanyMember>(
      `/api/workspace/companies/${companyId}/members/${membershipId}`,
      request
    );
    return response.data;
  };

  const removeCompanyMember = async (companyId: number, membershipId: number): Promise<void> => {
    await httpClient.delete(`/api/workspace/companies/${companyId}/members/${membershipId}`);
  };

  const getPortfolioMembers = async (): Promise<PortfolioMembersResponse> => {
    const response = await httpClient.get<PortfolioMembersResponse>('/api/workspace/portfolio/members');
    return response.data;
  };

  const getPortfolioHubs = async (): Promise<PortfolioHubsResponse> => {
    const response = await httpClient.get<PortfolioHubsResponse>('/api/workspace/portfolio/hubs');
    return response.data;
  };

  const addPortfolioMember = async (request: AddPortfolioMemberRequest): Promise<PortfolioMember> => {
    const response = await httpClient.post<PortfolioMember>('/api/workspace/portfolio/members', request);
    return response.data;
  };

  const removePortfolioMember = async (accessId: number): Promise<void> => {
    await httpClient.delete(`/api/workspace/portfolio/members/${accessId}`);
  };

  const getProjectMembers = async (projectId: number): Promise<ProjectMembersResponse> => {
    const response = await httpClient.get<ProjectMembersResponse>(`/api/workspace/projects/${projectId}/members`);
    return response.data;
  };

  const addProjectMember = async (projectId: number, request: AddProjectMemberRequest): Promise<ProjectMember> => {
    const response = await httpClient.post<ProjectMember>(`/api/workspace/projects/${projectId}/members`, request);
    return response.data;
  };

  const removeProjectMember = async (projectId: number, membershipId: number): Promise<void> => {
    await httpClient.delete(`/api/workspace/projects/${projectId}/members/${membershipId}`);
  };

  return Object.freeze({
    getWorkspace,
    getCompanyMembers,
    addCompanyMember,
    updateCompanyMember,
    removeCompanyMember,
    getPortfolioMembers,
    getPortfolioHubs,
    addPortfolioMember,
    removePortfolioMember,
    getProjectMembers,
    addProjectMember,
    removeProjectMember
  });
};
