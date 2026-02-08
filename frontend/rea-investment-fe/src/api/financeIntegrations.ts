import { httpClient } from './http-client';

export interface FinanceProviderInfo {
  key: string;
  display_name: string;
  supports_budgets: boolean;
}

export interface FinanceIntegration {
  id: number;
  company_id: number;
  provider_key: string;
  provider_display_name?: string;
  config?: Record<string, unknown>;
  status: 'pending' | 'configured' | 'error' | 'disabled';
  last_tested_at?: string;
  last_test_success?: boolean;
  last_error?: string;
  created_at: string;
  updated_at: string;
}

export interface FinanceIntegrationsListResponse {
  integrations: FinanceIntegration[];
  available_providers: FinanceProviderInfo[];
}

export interface FinanceIntegrationCredentials {
  api_key?: string;
  api_secret?: string;
  base_url?: string;
  additional?: Record<string, unknown>;
}

export interface FinanceIntegrationCreatePayload {
  provider_key: string;
  credentials: FinanceIntegrationCredentials;
  config?: Record<string, unknown>;
}

export interface FinanceIntegrationUpdatePayload {
  credentials?: FinanceIntegrationCredentials;
  config?: Record<string, unknown>;
  status?: 'pending' | 'configured' | 'error' | 'disabled';
}

export interface FinanceIntegrationTestResponse {
  success: boolean;
  status: string;
  message: string;
  tested_at: string;
  details?: Record<string, unknown>;
}

export const financeIntegrations = {
  getCompanyIntegrations: async (companyId: number): Promise<FinanceIntegrationsListResponse> => {
    const response = await httpClient.get<FinanceIntegrationsListResponse>(`/api/finance/integrations/${companyId}`);
    return response.data;
  },

  createIntegration: async (
    companyId: number,
    payload: FinanceIntegrationCreatePayload
  ): Promise<FinanceIntegration> => {
    const response = await httpClient.post<FinanceIntegration>(`/api/finance/integrations/${companyId}`, payload);
    return response.data;
  },

  updateIntegration: async (
    companyId: number,
    providerKey: string,
    payload: FinanceIntegrationUpdatePayload
  ): Promise<FinanceIntegration> => {
    const response = await httpClient.patch<FinanceIntegration>(
      `/api/finance/integrations/${companyId}/${providerKey}`,
      payload
    );
    return response.data;
  },

  testIntegration: async (companyId: number, providerKey: string): Promise<FinanceIntegrationTestResponse> => {
    const response = await httpClient.post<FinanceIntegrationTestResponse>(
      `/api/finance/integrations/${companyId}/${providerKey}/test`
    );
    return response.data;
  },

  deleteIntegration: async (companyId: number, providerKey: string): Promise<void> => {
    await httpClient.delete(`/api/finance/integrations/${companyId}/${providerKey}`);
  }
};

export interface FinanceHealthSummary {
  sync_status: 'not_configured' | 'never_synced' | 'running' | 'healthy' | 'error';
  last_sync_at: string | null;
  last_sync_error: string | null;
  accounts_count: number;
  transactions_count_30d: number;
  unmapped_projects_count: number | null;
  needs_attention_reasons: string[];
}

export interface FinanceSyncTriggerResult {
  sync_run_id: number;
  correlation_id: string;
  status: string;
  message: string;
}

export const financeData = {
  getSummary: async (companyId: number): Promise<FinanceHealthSummary> => {
    const response = await httpClient.get<FinanceHealthSummary>(`/api/finance/summary?company_id=${companyId}`);
    return response.data;
  },

  triggerSync: async (companyId: number, providerKey: string): Promise<FinanceSyncTriggerResult> => {
    const response = await httpClient.post<FinanceSyncTriggerResult>(
      `/api/finance/integrations/${companyId}/${providerKey}/sync`
    );
    return response.data;
  }
};

export type FinanceIntegrationsApi = typeof financeIntegrations;
