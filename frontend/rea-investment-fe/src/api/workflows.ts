import type { AxiosInstance } from 'axios';

// Base path (httpClient baseURL already includes `/api`).
const WF = '/workflows';

export type WorkflowRunStatus = 'active' | 'paused' | 'completed' | 'abandoned';
export type WorkflowStepStatus = 'pending' | 'valid' | 'invalid';
export type WorkflowStepKind = 'collect' | 'execute';
export type WorkflowConfirmation = 'none' | 'standard' | 'governed';

// --- Serialized definition (the Wizard shell consumes this) --------------------------

export interface WorkflowFieldOption {
  label: string;
  value: string;
}

export interface WorkflowFieldSchema {
  name: string;
  label: string;
  type: string;
  required: boolean;
  options?: WorkflowFieldOption[] | null;
  placeholder?: string | null;
  help?: string | null;
  max_length?: number | null;
  pattern?: string | null;
}

export interface WorkflowStepSchema {
  id: string;
  title: string;
  kind: WorkflowStepKind;
  confirmation: WorkflowConfirmation;
  governed: boolean;
  help?: string | null;
  inputs: WorkflowFieldSchema[];
}

export interface WorkflowDefinitionSchema {
  id: string;
  version: string;
  title: string;
  description: string;
  can_start: boolean;
  // Additive discovery metadata (powers the dashboard + orchestrator). Presentational only.
  category: string;
  icon?: string | null;
  suggested_next: string[];
  landing_route_template?: string | null;
  sequence_eligible: boolean;
  steps: WorkflowStepSchema[];
}

export interface WorkflowListResponse {
  items: WorkflowDefinitionSchema[];
}

// --- Runs / step states --------------------------------------------------------------

export interface WorkflowStepStateSchema {
  step_id: string;
  inputs?: Record<string, unknown> | null;
  validation_status: WorkflowStepStatus;
  validation_errors?: Record<string, string> | null;
  executed: boolean;
  result_entity_type?: string | null;
  result_entity_id?: number | null;
}

export interface WorkflowRunSchema {
  id: number;
  workflow_id: string;
  workflow_version: string;
  status: WorkflowRunStatus;
  current_step?: string | null;
  company_id?: number | null;
  site_id?: number | null;
  step_states: WorkflowStepStateSchema[];
}

export interface WorkflowRunDetailResponse {
  run: WorkflowRunSchema;
  definition: WorkflowDefinitionSchema;
}

// --- Dashboard run summaries ---------------------------------------------------------

// Compact, owner-scoped run row for the Workflow Dashboard. Never carries another user's
// collected inputs — only enough to render a card and resume/cancel/land.
export interface WorkflowRunSummarySchema {
  id: number;
  workflow_id: string;
  workflow_version: string;
  workflow_title?: string | null;
  status: WorkflowRunStatus;
  current_step?: string | null;
  company_id?: number | null;
  site_id?: number | null;
  parent_run_id?: number | null;
  sequence_id?: string | null;
  sequence_step_index?: number | null;
  result_entity_type?: string | null;
  result_entity_id?: number | null;
  landing_route_template?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface WorkflowRunListResponse {
  items: WorkflowRunSummarySchema[];
}

// --- Sequences (orchestrator catalog) ------------------------------------------------

export interface SequenceStepSchema {
  workflow_id: string;
  title: string;
  description: string;
  can_start: boolean;
}

export interface SequenceSchema {
  id: string;
  title: string;
  description: string;
  category: string;
  icon?: string | null;
  can_start: boolean;
  steps: SequenceStepSchema[];
}

export interface SequenceListResponse {
  items: SequenceSchema[];
}

// --- Requests ------------------------------------------------------------------------

export interface StartRunRequest {
  company_id?: number | null;
  site_id?: number | null;
  // Orchestration lineage (optional). Set by the onboarding orchestrator to chain this run to
  // the prior one; the engine validates parent ownership + sequence/step integrity server-side.
  parent_run_id?: number | null;
  sequence_id?: string | null;
  sequence_step_index?: number | null;
}

export interface ListRunsParams {
  statuses?: WorkflowRunStatus[];
  workflowId?: string;
  sequenceId?: string;
  limit?: number;
}

export interface SaveStepRequest {
  inputs: Record<string, unknown>;
}

export interface ExecuteRequest {
  confirm_token: string;
  idempotency_key?: string | null;
}

// --- Responses -----------------------------------------------------------------------

export interface PreviewItem {
  label: string;
  value?: string | null;
}

export interface PreviewResponse {
  step_id: string;
  confirmation: WorkflowConfirmation;
  summary: PreviewItem[];
  warnings: string[];
  confirm_token: string;
}

export interface ExecuteResponse {
  step_id: string;
  executed: boolean;
  entity_type?: string | null;
  entity_id?: number | null;
  run_status: WorkflowRunStatus;
  message: string;
}

export interface AbandonResponse {
  run_id: number;
  run_status: WorkflowRunStatus;
  message: string;
}

// Structured engine error payload. The backend renders preview/execute engine errors as a
// JSONResponse (per-field validation, blast-radius re-confirm), surfaced via the thrown
// axios error's `response.data`.
export interface WorkflowErrorPayload {
  message?: string;
  code?: string;
  errors?: Record<string, string>;
}

export const buildWorkflowsApi = (httpClient: AxiosInstance) => ({
  list: async (): Promise<WorkflowListResponse> => {
    const { data } = await httpClient.get<WorkflowListResponse>(WF);
    return data;
  },

  // Owner-scoped run listing for the dashboard. `statuses` is sent as repeated `status=` query
  // params (matches the backend's repeatable alias); unknown values are ignored server-side.
  listRuns: async (params: ListRunsParams = {}): Promise<WorkflowRunListResponse> => {
    const search = new URLSearchParams();
    (params.statuses ?? []).forEach(s => search.append('status', s));
    if (params.workflowId) search.append('workflow_id', params.workflowId);
    if (params.sequenceId) search.append('sequence_id', params.sequenceId);
    if (params.limit != null) search.append('limit', String(params.limit));
    const qs = search.toString();
    const { data } = await httpClient.get<WorkflowRunListResponse>(`${WF}/runs${qs ? `?${qs}` : ''}`);
    return data;
  },

  listSequences: async (): Promise<SequenceListResponse> => {
    const { data } = await httpClient.get<SequenceListResponse>(`${WF}/sequences`);
    return data;
  },

  startRun: async (workflowId: string, body: StartRunRequest = {}): Promise<WorkflowRunDetailResponse> => {
    const { data } = await httpClient.post<WorkflowRunDetailResponse>(`${WF}/${workflowId}/runs`, body);
    return data;
  },

  getRun: async (runId: number): Promise<WorkflowRunDetailResponse> => {
    const { data } = await httpClient.get<WorkflowRunDetailResponse>(`${WF}/runs/${runId}`);
    return data;
  },

  saveStep: async (
    runId: number,
    stepId: string,
    inputs: Record<string, unknown>
  ): Promise<WorkflowStepStateSchema> => {
    const { data } = await httpClient.patch<WorkflowStepStateSchema>(`${WF}/runs/${runId}/steps/${stepId}`, {
      inputs
    });
    return data;
  },

  preview: async (runId: number, stepId: string): Promise<PreviewResponse> => {
    const { data } = await httpClient.post<PreviewResponse>(`${WF}/runs/${runId}/steps/${stepId}/preview`);
    return data;
  },

  execute: async (runId: number, stepId: string, body: ExecuteRequest): Promise<ExecuteResponse> => {
    const { data } = await httpClient.post<ExecuteResponse>(`${WF}/runs/${runId}/steps/${stepId}/execute`, body);
    return data;
  },

  abandon: async (runId: number): Promise<AbandonResponse> => {
    const { data } = await httpClient.post<AbandonResponse>(`${WF}/runs/${runId}/abandon`);
    return data;
  }
});

export type WorkflowsApi = ReturnType<typeof buildWorkflowsApi>;
