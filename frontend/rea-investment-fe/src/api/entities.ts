import type { AxiosInstance } from 'axios';

export type EntityType =
  | 'epc_contractor'
  | 'om_provider'
  | 'utility'
  | 'insurance'
  | 'engineering'
  | 'legal'
  | 'accounting'
  | 'bank'
  | 'investor'
  | 'developer'
  | 'offtaker'
  | 'subscriber_manager'
  | 'vegetation'
  | 'community_solar'
  | 'tax_equity'
  | 'other';

export type EntityRelationshipRole =
  | 'epc_contractor'
  | 'om_provider'
  | 'interconnection_utility'
  | 'insurance_provider'
  | 'community_solar_manager'
  | 'vegetation_vendor'
  | 'offtaker'
  | 'tax_equity_provider'
  | 'developer'
  | 'compliance_entity'
  | 'compliance_bank'
  | 'hold_co'
  | 'project_co'
  | 'landlord'
  | 'tenant';

export type DealEntityRole = 'developer' | 'project_company' | 'offtaker' | 'offtaker_legal';

export interface ProjectEntity {
  id: number;
  portfolio_id: number;
  name: string;
  entity_type: EntityType;
  address: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  notes: string | null;
  is_active: boolean;
  linked_company_id: number | null;
  linked_company_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectEntityCreate {
  name: string;
  entity_type: EntityType;
  portfolio_id: number;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  zip_code?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  notes?: string | null;
  linked_company_id?: number | null;
}

export interface ProjectEntityUpdate {
  name?: string;
  entity_type?: EntityType;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  zip_code?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  notes?: string | null;
  linked_company_id?: number | null;
  is_active?: boolean;
}

export interface ProjectEntityListResponse {
  items: ProjectEntity[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface EntityRelationship {
  id: number;
  site_id: number;
  entity_id: number;
  role: EntityRelationshipRole;
  contact_id: number | null;
  effective_date: string | null;
  termination_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  entity_name: string | null;
  entity_type: EntityType | null;
  contact_name: string | null;
}

export interface EntityRelationshipCreate {
  entity_id: number;
  role: EntityRelationshipRole;
  contact_id?: number | null;
  effective_date?: string | null;
  termination_date?: string | null;
  notes?: string | null;
}

export interface EntityRelationshipUpdate {
  entity_id?: number;
  role?: EntityRelationshipRole;
  contact_id?: number | null;
  effective_date?: string | null;
  termination_date?: string | null;
  notes?: string | null;
}

export interface EntityRelationshipListResponse {
  items: EntityRelationship[];
  total: number;
}

export interface DealEntityAssignment {
  id: number;
  deal_id: number;
  entity_id: number;
  role: DealEntityRole;
  contact_id: number | null;
  created_at: string;
  updated_at: string;
  entity_name: string | null;
  entity_type: EntityType | null;
  contact_name: string | null;
}

export interface DealEntityAssignmentCreate {
  entity_id: number;
  role: DealEntityRole;
  contact_id?: number | null;
}

export interface DealEntityAssignmentUpdate {
  entity_id?: number;
  role?: DealEntityRole;
  contact_id?: number | null;
}

export interface DealEntityAssignmentListResponse {
  items: DealEntityAssignment[];
  total: number;
}

export interface EntityAssignmentSummary {
  relationship_id: number;
  site_id: number;
  site_name: string;
  role: EntityRelationshipRole;
  effective_date: string | null;
  termination_date: string | null;
}

export interface EntityAssignmentsSummaryResponse {
  items: EntityAssignmentSummary[];
  total: number;
}

export interface EntityListParams {
  portfolio_id: number;
  search?: string;
  entity_type?: EntityType;
  include_inactive?: boolean;
  page?: number;
  page_size?: number;
}

function buildEntityQueryString(params: EntityListParams): string {
  const queryParams = new URLSearchParams();
  queryParams.append('portfolio_id', String(params.portfolio_id));
  if (params.search) {
    queryParams.append('search', params.search);
  }
  if (params.entity_type) {
    queryParams.append('entity_type', params.entity_type);
  }
  if (params.include_inactive) {
    queryParams.append('include_inactive', 'true');
  }
  if (params.page !== undefined) {
    queryParams.append('page', String(params.page));
  }
  if (params.page_size !== undefined) {
    queryParams.append('page_size', String(params.page_size));
  }
  return queryParams.toString();
}

export const createEntitiesApi = (httpClient: AxiosInstance) => ({
  entities: {
    list: async (params: EntityListParams): Promise<ProjectEntityListResponse> => {
      const queryString = buildEntityQueryString(params);
      const response = await httpClient.get<ProjectEntityListResponse>(`/entities?${queryString}`);
      return response.data;
    },

    create: async (data: ProjectEntityCreate): Promise<ProjectEntity> => {
      const response = await httpClient.post<ProjectEntity>('/entities', data);
      return response.data;
    },

    get: async (id: number): Promise<ProjectEntity> => {
      const response = await httpClient.get<ProjectEntity>(`/entities/${id}`);
      return response.data;
    },

    update: async (id: number, data: ProjectEntityUpdate): Promise<ProjectEntity> => {
      const response = await httpClient.put<ProjectEntity>(`/entities/${id}`, data);
      return response.data;
    },

    delete: async (id: number): Promise<void> => {
      await httpClient.delete(`/entities/${id}`);
    },

    getAssignments: async (id: number): Promise<EntityAssignmentsSummaryResponse> => {
      const response = await httpClient.get<EntityAssignmentsSummaryResponse>(`/entities/${id}/assignments`);
      return response.data;
    }
  },

  entityRelationships: {
    list: async (siteId: number): Promise<EntityRelationshipListResponse> => {
      const response = await httpClient.get<EntityRelationshipListResponse>(`/projects/${siteId}/entity-relationships`);
      return response.data;
    },

    create: async (siteId: number, data: EntityRelationshipCreate): Promise<EntityRelationship> => {
      const response = await httpClient.post<EntityRelationship>(`/projects/${siteId}/entity-relationships`, data);
      return response.data;
    },

    update: async (siteId: number, id: number, data: EntityRelationshipUpdate): Promise<EntityRelationship> => {
      const response = await httpClient.put<EntityRelationship>(`/projects/${siteId}/entity-relationships/${id}`, data);
      return response.data;
    },

    delete: async (siteId: number, id: number): Promise<void> => {
      await httpClient.delete(`/projects/${siteId}/entity-relationships/${id}`);
    }
  },

  dealEntityAssignments: {
    list: async (dealId: number): Promise<DealEntityAssignmentListResponse> => {
      const response = await httpClient.get<DealEntityAssignmentListResponse>(`/deals/${dealId}/entity-assignments`);
      return response.data;
    },

    create: async (dealId: number, data: DealEntityAssignmentCreate): Promise<DealEntityAssignment> => {
      const response = await httpClient.post<DealEntityAssignment>(`/deals/${dealId}/entity-assignments`, data);
      return response.data;
    },

    update: async (dealId: number, id: number, data: DealEntityAssignmentUpdate): Promise<DealEntityAssignment> => {
      const response = await httpClient.put<DealEntityAssignment>(`/deals/${dealId}/entity-assignments/${id}`, data);
      return response.data;
    },

    delete: async (dealId: number, id: number): Promise<void> => {
      await httpClient.delete(`/deals/${dealId}/entity-assignments/${id}`);
    }
  }
});

export type EntitiesApi = ReturnType<typeof createEntitiesApi>;
