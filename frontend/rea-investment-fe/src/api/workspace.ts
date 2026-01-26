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

  return Object.freeze({
    getWorkspace,
    getCompanyMembers,
    addCompanyMember,
    updateCompanyMember,
    removeCompanyMember
  });
};
