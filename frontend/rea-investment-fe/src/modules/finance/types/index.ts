export enum FinanceVendorType {
  EPC = 'epc',
  OM = 'om',
  Insurance = 'insurance',
  Utility = 'utility',
  Engineering = 'engineering',
  Legal = 'legal',
  Accounting = 'accounting',
  Other = 'other'
}

export enum FinanceObligationType {
  Milestone = 'milestone',
  Invoice = 'invoice',
  Retainer = 'retainer',
  ChangeOrder = 'change_order',
  ServiceCall = 'service_call',
  Other = 'other'
}

export enum FinanceObligationStatus {
  Draft = 'draft',
  Submitted = 'submitted',
  Approved = 'approved',
  Rejected = 'rejected',
  PaidExternal = 'paid_external',
  Canceled = 'canceled'
}

export enum FinanceBudgetStatus {
  Draft = 'draft',
  Active = 'active',
  Closed = 'closed'
}

export enum FinanceBudgetCategory {
  Development = 'development',
  Construction = 'construction',
  Interconnection = 'interconnection',
  Permitting = 'permitting',
  Equipment = 'equipment',
  Labor = 'labor',
  Engineering = 'engineering',
  Legal = 'legal',
  Insurance = 'insurance',
  OM = 'om',
  Administrative = 'administrative',
  Contingency = 'contingency',
  Other = 'other'
}

export enum FinanceApprovalDecision {
  Approved = 'approved',
  Rejected = 'rejected',
  Override = 'override'
}

export enum FinanceActualSource {
  Manual = 'manual',
  QuickBooks = 'quickbooks',
  Gravity = 'gravity',
  Other = 'other'
}

export interface FinanceVendor {
  id: number;
  company_id: number;
  name: string;
  vendor_type: FinanceVendorType;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FinanceBudgetLineItem {
  id: number;
  budget_id: number;
  vendor_id?: number;
  category: FinanceBudgetCategory;
  description?: string;
  amount_planned: number;
  amount_authorized: number;
  amount_actual: number;
  start_date?: string;
  end_date?: string;
  created_at: string;
  updated_at: string;
  vendor_name?: string;
}

export interface FinanceBudget {
  id: number;
  company_id: number;
  site_id?: number;
  deal_id?: number;
  name: string;
  description?: string;
  period_start?: string;
  period_end?: string;
  status: FinanceBudgetStatus;
  created_at: string;
  updated_at: string;
  created_by_id?: number;
  total_planned: number;
  total_authorized: number;
  total_actual: number;
  variance: number;
}

export interface FinanceBudgetDetail extends FinanceBudget {
  line_items: FinanceBudgetLineItem[];
  site_name?: string;
}

export interface FinanceObligation {
  id: number;
  company_id: number;
  site_id?: number;
  vendor_id?: number;
  budget_line_item_id?: number;
  obligation_type: FinanceObligationType;
  description?: string;
  amount_requested: number;
  requested_date: string;
  due_date?: string;
  status: FinanceObligationStatus;
  prerequisite_snapshot?: Record<string, unknown>;
  reference_number?: string;
  created_at: string;
  updated_at: string;
  created_by_id?: number;
  vendor_name?: string;
  site_name?: string;
}

export interface FinanceApproval {
  id: number;
  obligation_id: number;
  approved_by_id?: number;
  decision: FinanceApprovalDecision;
  notes?: string;
  override_reason?: string;
  approved_at: string;
  approved_by_name?: string;
}

export interface FinanceActual {
  id: number;
  company_id: number;
  site_id?: number;
  vendor_id?: number;
  category: FinanceBudgetCategory;
  description?: string;
  amount: number;
  transaction_date: string;
  reference_id?: string;
  source_system: FinanceActualSource;
  created_at: string;
  updated_at: string;
  created_by_id?: number;
  vendor_name?: string;
  site_name?: string;
}

export interface FinanceSiteSummary {
  site_id: number;
  site_name: string;
  total_budget_planned: number;
  total_budget_authorized: number;
  total_budget_actual: number;
  budget_variance: number;
  pending_obligations: number;
  pending_obligations_amount: number;
  finance_ready: boolean;
  missing_prerequisites: string[];
}

export interface FinancePortfolioSummary {
  total_budget_planned: number;
  total_budget_authorized: number;
  total_budget_actual: number;
  total_variance: number;
  sites_finance_ready: number;
  sites_not_ready: number;
  total_pending_obligations: number;
  total_pending_amount: number;
}

export interface FinancePortfolioResponse {
  summary: FinancePortfolioSummary;
  sites: FinanceSiteSummary[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}
