export enum SalesStage {
  Discovery = 'discovery',
  Qualified = 'qualified',
  LOITermSheet = 'loi_term_sheet',
  UnderContract = 'under_contract',
  HandoffToDiligence = 'handoff_to_diligence'
}

export enum LifecycleState {
  SalesPreDiligence = 'sales_pre_diligence',
  DueDiligence = 'due_diligence',
  Implementation = 'implementation',
  PlacedInService = 'placed_in_service',
  Operations = 'operations'
}

export enum SalesSource {
  Broker = 'broker',
  Inbound = 'inbound',
  Developer = 'developer',
  Outreach = 'outreach',
  Referral = 'referral',
  Other = 'other'
}

export interface UserSummary {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export interface CompanySummary {
  id: number;
  name: string;
}

export interface SalesProject {
  id: number;
  name: string;
  address: string;
  city: string;
  state: string;
  system_size_ac: number;
  system_size_dc: number;
  company: CompanySummary;
  sales_stage?: SalesStage;
  lifecycle_state?: LifecycleState;
  sales_source?: SalesSource;
  target_close_date?: string;
  probability?: number;
  pipeline_value?: number;
  assigned_owner?: UserSummary;
  next_action_date?: string;
  next_action_notes?: string;
  sales_notes?: string;
  handoff_checklist_completed?: boolean;
  created_at: string;
  updated_at: string;
}

export interface SalesPipelineSummary {
  id: number;
  name: string;
  company_name: string;
  sales_stage?: SalesStage;
  lifecycle_state?: LifecycleState;
  pipeline_value?: number;
  probability?: number;
  target_close_date?: string;
  next_action_date?: string;
  assigned_owner?: UserSummary;
  system_size_ac: number;
}

export interface SalesPipelineResponse {
  discovery: SalesPipelineSummary[];
  qualified: SalesPipelineSummary[];
  loi_term_sheet: SalesPipelineSummary[];
  under_contract: SalesPipelineSummary[];
  handoff_to_diligence: SalesPipelineSummary[];
}

export interface HandoffChecklistItem {
  field: string;
  label: string;
  completed: boolean;
  value?: string;
}

export interface HandoffChecklistResponse {
  site_id: number;
  all_complete: boolean;
  items: HandoffChecklistItem[];
}

export interface SalesStateTransition {
  id: number;
  site_id: number;
  transition_type: string;
  from_state?: string;
  to_state: string;
  notes?: string;
  changed_by?: UserSummary;
  created_at: string;
}

export interface SalesProjectUpdate {
  sales_stage?: SalesStage;
  lifecycle_state?: LifecycleState;
  sales_source?: SalesSource;
  target_close_date?: string;
  probability?: number;
  pipeline_value?: number;
  assigned_owner_id?: number;
  next_action_date?: string;
  next_action_notes?: string;
  sales_notes?: string;
}

export interface SalesListFilters {
  company_id?: number;
  sales_stage?: SalesStage;
  lifecycle_state?: LifecycleState;
  assigned_owner_id?: number;
  needs_action?: boolean;
  skip?: number;
  limit?: number;
}

export const SALES_STAGE_LABELS: Record<SalesStage, string> = {
  [SalesStage.Discovery]: 'Discovery',
  [SalesStage.Qualified]: 'Qualified',
  [SalesStage.LOITermSheet]: 'LOI / Term Sheet',
  [SalesStage.UnderContract]: 'Under Contract',
  [SalesStage.HandoffToDiligence]: 'Handoff to Diligence'
};

export const LIFECYCLE_STATE_LABELS: Record<LifecycleState, string> = {
  [LifecycleState.SalesPreDiligence]: 'Pre-Diligence',
  [LifecycleState.DueDiligence]: 'Due Diligence',
  [LifecycleState.Implementation]: 'Implementation',
  [LifecycleState.PlacedInService]: 'Placed in Service',
  [LifecycleState.Operations]: 'Operations'
};

export const SALES_SOURCE_LABELS: Record<SalesSource, string> = {
  [SalesSource.Broker]: 'Broker',
  [SalesSource.Inbound]: 'Inbound',
  [SalesSource.Developer]: 'Developer',
  [SalesSource.Outreach]: 'Outreach',
  [SalesSource.Referral]: 'Referral',
  [SalesSource.Other]: 'Other'
};

export const SALES_STAGE_COLORS: Record<SalesStage, string> = {
  [SalesStage.Discovery]: '#90CAF9',
  [SalesStage.Qualified]: '#81C784',
  [SalesStage.LOITermSheet]: '#FFB74D',
  [SalesStage.UnderContract]: '#9575CD',
  [SalesStage.HandoffToDiligence]: '#4CAF50'
};
