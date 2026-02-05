import type { AxiosInstance } from 'axios';

export type ContactScopeType = 'portfolio' | 'company' | 'project';

export interface Contact {
  id: number;
  scope_type: ContactScopeType;
  portfolio_id: number | null;
  company_id: number | null;
  project_id: number | null;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  title: string | null;
  organization: string | null;
  notes: string | null;
  tags: string[] | null;
  is_archived: boolean;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
  is_user: boolean;
}

export interface ContactCreate {
  scope_type: ContactScopeType;
  portfolio_id?: number | null;
  company_id?: number | null;
  project_id?: number | null;
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  title?: string | null;
  organization?: string | null;
  notes?: string | null;
  tags?: string[] | null;
}

export interface ContactUpdate {
  first_name?: string;
  last_name?: string;
  email?: string | null;
  phone?: string | null;
  title?: string | null;
  organization?: string | null;
  notes?: string | null;
  tags?: string[] | null;
  is_archived?: boolean;
}

export interface ContactListResponse {
  items: Contact[];
  total: number;
  skip: number;
  limit: number;
}

export interface ContactsQueryParams {
  scope_type: ContactScopeType;
  portfolio_id?: number;
  company_id?: number;
  project_id?: number;
  search?: string;
  include_archived?: boolean;
  skip?: number;
  limit?: number;
}

function buildQueryString(params: ContactsQueryParams): string {
  const queryParams = new URLSearchParams();
  queryParams.append('scope_type', params.scope_type);
  
  if (params.portfolio_id !== undefined) {
    queryParams.append('portfolio_id', String(params.portfolio_id));
  }
  if (params.company_id !== undefined) {
    queryParams.append('company_id', String(params.company_id));
  }
  if (params.project_id !== undefined) {
    queryParams.append('project_id', String(params.project_id));
  }
  if (params.search) {
    queryParams.append('search', params.search);
  }
  if (params.include_archived !== undefined) {
    queryParams.append('include_archived', String(params.include_archived));
  }
  if (params.skip !== undefined) {
    queryParams.append('skip', String(params.skip));
  }
  if (params.limit !== undefined) {
    queryParams.append('limit', String(params.limit));
  }
  
  return queryParams.toString();
}

export const createContactsApi = (httpClient: AxiosInstance) => ({
  list: async (params: ContactsQueryParams): Promise<ContactListResponse> => {
    const queryString = buildQueryString(params);
    const response = await httpClient.get<ContactListResponse>(`/contacts?${queryString}`);
    return response.data;
  },

  get: async (id: number): Promise<Contact> => {
    const response = await httpClient.get<Contact>(`/contacts/${id}`);
    return response.data;
  },

  create: async (data: ContactCreate): Promise<Contact> => {
    const response = await httpClient.post<Contact>('/contacts', data);
    return response.data;
  },

  update: async (id: number, data: ContactUpdate): Promise<Contact> => {
    const response = await httpClient.patch<Contact>(`/contacts/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await httpClient.delete(`/contacts/${id}`);
  },

  archive: async (id: number): Promise<Contact> => {
    const response = await httpClient.patch<Contact>(`/contacts/${id}`, { is_archived: true });
    return response.data;
  },

  unarchive: async (id: number): Promise<Contact> => {
    const response = await httpClient.patch<Contact>(`/contacts/${id}`, { is_archived: false });
    return response.data;
  },
});

export type ContactsApi = ReturnType<typeof createContactsApi>;
