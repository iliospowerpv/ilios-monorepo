export enum SalesStage {
  Prospect = 'prospect',
  NDASigned = 'nda_signed',
  InputsReceived = 'inputs_received',
  Modeling = 'modeling',
  ModelReview = 'model_review',
  ModelApproved = 'model_approved',
  Quoted = 'quoted',
  TermSheetNeg = 'term_sheet_neg',
  TermSheetSigned = 'term_sheet_signed',
  Phase1Diligence = 'phase_1_diligence',
  MIPANegotiating = 'mipa_negotiating',
  MIPASigned = 'mipa_signed',
  Passed = 'passed',
  Dead = 'dead'
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

export enum NextActionStatus {
  None = 'none',
  Pending = 'pending',
  InProgress = 'in_progress',
  Blocked = 'blocked',
  Overdue = 'overdue'
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

export interface Deal {
  id: number;
  name: string;
  company_id: number;
  company_name?: string;
  sales_stage: SalesStage;
  is_converted: boolean;
  converted_project_id?: number;
  developer_name?: string;
  quoted_by?: string;
  address?: string;
  city?: string;
  state?: string;
  latitude?: number;
  longitude?: number;
  system_size_ac?: number;
  system_size_dc?: number;
  ownership_structure?: string;
  offtaker_name?: string;
  offtaker_legal_name?: string;
  utility_rate?: string;
  utility_zone?: string;
  project_company?: string;
  mipa_per_watt?: number;
  itc_percent?: number;
  itc_amount?: number;
  fmv?: number;
  grant_amount?: number;
  tax_equity?: number;
  target_close_date?: string;
  probability?: number;
  pipeline_value?: number;
  assigned_owner_id?: number;
  assigned_owner?: UserSummary;
  last_action?: string;
  next_action?: string;
  next_action_date?: string;
  next_action_status?: NextActionStatus;
  notice_to_proceed_date?: string;
  mechanical_completion_date?: string;
  permission_to_operate_date?: string;
  substantial_completion_date?: string;
  sales_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface DealCreate {
  name: string;
  company_id: number;
  sales_stage?: SalesStage;
  developer_name?: string;
  quoted_by?: string;
  address?: string;
  city?: string;
  state?: string;
  latitude?: number;
  longitude?: number;
  system_size_ac?: number;
  system_size_dc?: number;
  ownership_structure?: string;
  offtaker_name?: string;
  offtaker_legal_name?: string;
  utility_rate?: string;
  utility_zone?: string;
  project_company?: string;
  mipa_per_watt?: number;
  itc_percent?: number;
  itc_amount?: number;
  fmv?: number;
  grant_amount?: number;
  tax_equity?: number;
  target_close_date?: string;
  probability?: number;
  pipeline_value?: number;
  assigned_owner_id?: number;
  last_action?: string;
  next_action?: string;
  next_action_date?: string;
  next_action_status?: NextActionStatus;
  notice_to_proceed_date?: string;
  mechanical_completion_date?: string;
  permission_to_operate_date?: string;
  substantial_completion_date?: string;
  sales_notes?: string;
}

export interface DealUpdate extends Partial<DealCreate> {
  sales_stage?: SalesStage;
}

export interface DealPipelineResponse {
  prospect: Deal[];
  nda_signed: Deal[];
  inputs_received: Deal[];
  modeling: Deal[];
  model_review: Deal[];
  model_approved: Deal[];
  quoted: Deal[];
  term_sheet_neg: Deal[];
  term_sheet_signed: Deal[];
  phase_1_diligence: Deal[];
  mipa_negotiating: Deal[];
  mipa_signed: Deal[];
  passed: Deal[];
  dead: Deal[];
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
  site_id?: number;
  deal_id?: number;
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

export interface ConvertToProjectRequest {
  notes?: string;
}

export interface ConvertToProjectResponse {
  deal_id: number;
  project_id: number;
  message: string;
}

export const SALES_STAGE_LABELS: Record<SalesStage, string> = {
  [SalesStage.Prospect]: 'Prospect',
  [SalesStage.NDASigned]: 'NDA Signed',
  [SalesStage.InputsReceived]: 'Inputs Received',
  [SalesStage.Modeling]: 'Modeling',
  [SalesStage.ModelReview]: 'Model Review',
  [SalesStage.ModelApproved]: 'Model Approved',
  [SalesStage.Quoted]: 'Quoted',
  [SalesStage.TermSheetNeg]: 'Term Sheet Neg',
  [SalesStage.TermSheetSigned]: 'Term Sheet Signed',
  [SalesStage.Phase1Diligence]: 'Phase 1 Diligence',
  [SalesStage.MIPANegotiating]: 'MIPA Negotiating',
  [SalesStage.MIPASigned]: 'MIPA Signed',
  [SalesStage.Passed]: 'Passed',
  [SalesStage.Dead]: 'Dead'
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

export const NEXT_ACTION_STATUS_LABELS: Record<NextActionStatus, string> = {
  [NextActionStatus.None]: 'None',
  [NextActionStatus.Pending]: 'Pending',
  [NextActionStatus.InProgress]: 'In Progress',
  [NextActionStatus.Blocked]: 'Blocked',
  [NextActionStatus.Overdue]: 'Overdue'
};

export const SALES_STAGE_COLORS: Record<SalesStage, string> = {
  [SalesStage.Prospect]: '#E3F2FD',
  [SalesStage.NDASigned]: '#BBDEFB',
  [SalesStage.InputsReceived]: '#90CAF9',
  [SalesStage.Modeling]: '#64B5F6',
  [SalesStage.ModelReview]: '#42A5F5',
  [SalesStage.ModelApproved]: '#81C784',
  [SalesStage.Quoted]: '#A5D6A7',
  [SalesStage.TermSheetNeg]: '#FFE082',
  [SalesStage.TermSheetSigned]: '#FFD54F',
  [SalesStage.Phase1Diligence]: '#FFCA28',
  [SalesStage.MIPANegotiating]: '#CE93D8',
  [SalesStage.MIPASigned]: '#4CAF50',
  [SalesStage.Passed]: '#BDBDBD',
  [SalesStage.Dead]: '#EF5350'
};

export const ACTIVE_PIPELINE_STAGES: SalesStage[] = [
  SalesStage.Prospect,
  SalesStage.NDASigned,
  SalesStage.InputsReceived,
  SalesStage.Modeling,
  SalesStage.ModelReview,
  SalesStage.ModelApproved,
  SalesStage.Quoted,
  SalesStage.TermSheetNeg,
  SalesStage.TermSheetSigned,
  SalesStage.Phase1Diligence,
  SalesStage.MIPANegotiating,
  SalesStage.MIPASigned
];

export const CLOSED_STAGES: SalesStage[] = [SalesStage.Passed, SalesStage.Dead];
