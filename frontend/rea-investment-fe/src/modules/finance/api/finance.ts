import axios from 'axios';
import type {
  FinancePortfolioResponse,
  FinanceSiteSummary,
  FinanceBudget,
  FinanceBudgetDetail,
  FinanceObligation,
  FinanceVendor,
  FinanceActual,
  FinanceApproval,
  PaginatedResponse
} from '../types';

const API_BASE = process.env.REACT_APP_URL || '';

export const financeApi = {
  getPortfolioSummary: async (companyId: number): Promise<FinancePortfolioResponse> => {
    const response = await axios.get<FinancePortfolioResponse>(
      `${API_BASE}/api/finance/companies/${companyId}/portfolio/summary`
    );
    return response.data;
  },

  getSiteSummary: async (companyId: number, siteId: number): Promise<FinanceSiteSummary> => {
    const response = await axios.get<FinanceSiteSummary>(
      `${API_BASE}/api/finance/companies/${companyId}/portfolio/sites/${siteId}/summary`
    );
    return response.data;
  },

  getBudgets: async (
    companyId: number,
    params?: { site_id?: number; skip?: number; limit?: number }
  ): Promise<PaginatedResponse<FinanceBudget>> => {
    const response = await axios.get<PaginatedResponse<FinanceBudget>>(
      `${API_BASE}/api/finance/companies/${companyId}/budgets`,
      { params }
    );
    return response.data;
  },

  getBudget: async (companyId: number, budgetId: number): Promise<FinanceBudgetDetail> => {
    const response = await axios.get<FinanceBudgetDetail>(
      `${API_BASE}/api/finance/companies/${companyId}/budgets/${budgetId}`
    );
    return response.data;
  },

  createBudget: async (companyId: number, data: Partial<FinanceBudget>): Promise<FinanceBudgetDetail> => {
    const response = await axios.post<FinanceBudgetDetail>(
      `${API_BASE}/api/finance/companies/${companyId}/budgets`,
      data
    );
    return response.data;
  },

  updateBudget: async (
    companyId: number,
    budgetId: number,
    data: Partial<FinanceBudget>
  ): Promise<FinanceBudgetDetail> => {
    const response = await axios.patch<FinanceBudgetDetail>(
      `${API_BASE}/api/finance/companies/${companyId}/budgets/${budgetId}`,
      data
    );
    return response.data;
  },

  deleteBudget: async (companyId: number, budgetId: number): Promise<void> => {
    await axios.delete(`${API_BASE}/api/finance/companies/${companyId}/budgets/${budgetId}`);
  },

  getObligations: async (
    companyId: number,
    params?: { site_id?: number; status?: string; skip?: number; limit?: number }
  ): Promise<PaginatedResponse<FinanceObligation>> => {
    const response = await axios.get<PaginatedResponse<FinanceObligation>>(
      `${API_BASE}/api/finance/companies/${companyId}/obligations`,
      { params }
    );
    return response.data;
  },

  getObligation: async (companyId: number, obligationId: number): Promise<FinanceObligation> => {
    const response = await axios.get<FinanceObligation>(
      `${API_BASE}/api/finance/companies/${companyId}/obligations/${obligationId}`
    );
    return response.data;
  },

  createObligation: async (companyId: number, data: Partial<FinanceObligation>): Promise<FinanceObligation> => {
    const response = await axios.post<FinanceObligation>(
      `${API_BASE}/api/finance/companies/${companyId}/obligations`,
      data
    );
    return response.data;
  },

  submitObligation: async (companyId: number, obligationId: number): Promise<FinanceObligation> => {
    const response = await axios.post<FinanceObligation>(
      `${API_BASE}/api/finance/companies/${companyId}/obligations/${obligationId}/submit`,
      {}
    );
    return response.data;
  },

  approveObligation: async (
    companyId: number,
    obligationId: number,
    data: { decision: string; notes?: string; override_reason?: string }
  ): Promise<FinanceApproval> => {
    const response = await axios.post<FinanceApproval>(
      `${API_BASE}/api/finance/companies/${companyId}/obligations/${obligationId}/approve`,
      data
    );
    return response.data;
  },

  getApprovals: async (companyId: number, obligationId: number): Promise<FinanceApproval[]> => {
    const response = await axios.get<FinanceApproval[]>(
      `${API_BASE}/api/finance/companies/${companyId}/obligations/${obligationId}/approvals`
    );
    return response.data;
  },

  getVendors: async (
    companyId: number,
    params?: { is_active?: boolean; skip?: number; limit?: number }
  ): Promise<PaginatedResponse<FinanceVendor>> => {
    const response = await axios.get<PaginatedResponse<FinanceVendor>>(
      `${API_BASE}/api/finance/companies/${companyId}/vendors`,
      { params }
    );
    return response.data;
  },

  createVendor: async (companyId: number, data: Partial<FinanceVendor>): Promise<FinanceVendor> => {
    const response = await axios.post<FinanceVendor>(`${API_BASE}/api/finance/companies/${companyId}/vendors`, data);
    return response.data;
  },

  updateVendor: async (companyId: number, vendorId: number, data: Partial<FinanceVendor>): Promise<FinanceVendor> => {
    const response = await axios.patch<FinanceVendor>(
      `${API_BASE}/api/finance/companies/${companyId}/vendors/${vendorId}`,
      data
    );
    return response.data;
  },

  getActuals: async (
    companyId: number,
    params?: { site_id?: number; skip?: number; limit?: number }
  ): Promise<PaginatedResponse<FinanceActual>> => {
    const response = await axios.get<PaginatedResponse<FinanceActual>>(
      `${API_BASE}/api/finance/companies/${companyId}/actuals`,
      { params }
    );
    return response.data;
  },

  createActual: async (companyId: number, data: Partial<FinanceActual>): Promise<FinanceActual> => {
    const response = await axios.post<FinanceActual>(`${API_BASE}/api/finance/companies/${companyId}/actuals`, data);
    return response.data;
  },

  downloadDataRoomPackage: async (companyId: number, siteId: number): Promise<Blob> => {
    const response = await axios.get(
      `${API_BASE}/api/finance/companies/${companyId}/portfolio/sites/${siteId}/data-room-package`,
      { responseType: 'blob' }
    );
    return response.data;
  }
};

export default financeApi;
