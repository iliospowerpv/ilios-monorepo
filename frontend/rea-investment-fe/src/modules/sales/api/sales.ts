import { httpClient } from '../../../api/http-client';
import type {
  SalesPipelineResponse,
  SalesProject,
  SalesProjectUpdate,
  HandoffChecklistResponse,
  SalesStateTransition,
  SalesListFilters,
  SalesStage,
  LifecycleState,
  Deal,
  DealCreate,
  DealUpdate,
  DealPipelineResponse,
  ConvertToProjectRequest,
  ConvertToProjectResponse
} from '../types';

export const salesApi = {
  getPipeline: async (companyId?: number): Promise<SalesPipelineResponse> => {
    const response = await httpClient.get<SalesPipelineResponse>('/api/sales/pipeline', {
      params: companyId ? { company_id: companyId } : undefined
    });
    return response.data;
  },

  getList: async (filters?: SalesListFilters): Promise<SalesProject[]> => {
    const response = await httpClient.get<SalesProject[]>('/api/sales/list', {
      params: filters
    });
    return response.data;
  },

  getProject: async (siteId: number): Promise<SalesProject> => {
    const response = await httpClient.get<SalesProject>(`/api/sales/projects/${siteId}`);
    return response.data;
  },

  updateProject: async (siteId: number, data: SalesProjectUpdate): Promise<SalesProject> => {
    const response = await httpClient.patch<SalesProject>(`/api/sales/projects/${siteId}`, data);
    return response.data;
  },

  transitionStage: async (siteId: number, newStage: SalesStage, notes?: string): Promise<SalesProject> => {
    const response = await httpClient.post<SalesProject>(`/api/sales/projects/${siteId}/stage-transition`, {
      new_stage: newStage,
      notes
    });
    return response.data;
  },

  transitionLifecycle: async (siteId: number, newState: LifecycleState, notes?: string): Promise<SalesProject> => {
    const response = await httpClient.post<SalesProject>(`/api/sales/projects/${siteId}/lifecycle-transition`, {
      new_state: newState,
      notes
    });
    return response.data;
  },

  getHandoffChecklist: async (siteId: number): Promise<HandoffChecklistResponse> => {
    const response = await httpClient.get<HandoffChecklistResponse>(`/api/sales/projects/${siteId}/handoff-checklist`);
    return response.data;
  },

  getTransitions: async (siteId: number): Promise<SalesStateTransition[]> => {
    const response = await httpClient.get<SalesStateTransition[]>(`/api/sales/projects/${siteId}/transitions`);
    return response.data;
  }
};

export const dealsApi = {
  getPipeline: async (companyId?: number): Promise<DealPipelineResponse> => {
    const response = await httpClient.get<DealPipelineResponse>('/api/sales/deals/pipeline', {
      params: companyId ? { company_id: companyId } : undefined
    });
    return response.data;
  },

  getList: async (companyId?: number, stage?: SalesStage, skip?: number, limit?: number): Promise<Deal[]> => {
    const response = await httpClient.get<Deal[]>('/api/sales/deals', {
      params: { company_id: companyId, stage, skip, limit }
    });
    return response.data;
  },

  getDeal: async (dealId: number): Promise<Deal> => {
    const response = await httpClient.get<Deal>(`/api/sales/deals/${dealId}`);
    return response.data;
  },

  createDeal: async (data: DealCreate): Promise<Deal> => {
    const response = await httpClient.post<Deal>('/api/sales/deals', data);
    return response.data;
  },

  updateDeal: async (dealId: number, data: DealUpdate): Promise<Deal> => {
    const response = await httpClient.patch<Deal>(`/api/sales/deals/${dealId}`, data);
    return response.data;
  },

  transitionStage: async (dealId: number, newStage: SalesStage, notes?: string): Promise<Deal> => {
    const response = await httpClient.post<Deal>(`/api/sales/deals/${dealId}/stage-transition`, {
      new_stage: newStage,
      notes
    });
    return response.data;
  },

  getTransitions: async (dealId: number): Promise<SalesStateTransition[]> => {
    const response = await httpClient.get<SalesStateTransition[]>(`/api/sales/deals/${dealId}/transitions`);
    return response.data;
  },

  convertToProject: async (dealId: number, data?: ConvertToProjectRequest): Promise<ConvertToProjectResponse> => {
    const response = await httpClient.post<ConvertToProjectResponse>(
      `/api/sales/deals/${dealId}/convert-to-project`,
      data || {}
    );
    return response.data;
  }
};

export default salesApi;
