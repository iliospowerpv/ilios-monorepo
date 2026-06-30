import type { AxiosInstance } from 'axios';

// Base path. The shared httpClient baseURL is the backend origin only (no `/api`), so — like every
// other API module in this codebase — the `/api` prefix is part of the path here.
const WF = '/api/workflows';

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
  // When set, this EXECUTE step expects a file part under this field name and must run via the
  // multipart execute-file route (the wizard renders a file input on the review step). null = JSON.
  multipart_file_field?: string | null;
}

// A declarative, read-only dependency advertised by a workflow. `met` is evaluated per-caller
// (user-scoped, fail-closed) and is purely informational — it powers the dashboard's "blocked"
// affordance and does NOT replace authorization (`can_start`).
export interface WorkflowPrerequisiteSchema {
  key: string;
  label: string;
  met: boolean;
  unmet_message: string;
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
  // Declarative prerequisites + the first unmet message (null when all met / none declared).
  prerequisites: WorkflowPrerequisiteSchema[];
  blocked_reason?: string | null;
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

// --- Completion metrics (read-only) --------------------------------------------------

export type WorkflowMetricsScope = 'me' | 'all';

// Per-workflow rollup. Rates are fractions in [0, 1] over CLOSED runs (completed + abandoned).
export interface WorkflowMetricsItemSchema {
  workflow_id: string;
  title: string;
  total: number;
  completed: number;
  abandoned: number;
  in_progress: number;
  completion_rate: number;
  abandonment_rate: number;
  avg_duration_seconds?: number | null;
  median_duration_seconds?: number | null;
}

export interface WorkflowMetricsResponse {
  scope: string;
  total_runs: number;
  completed_runs: number;
  abandoned_runs: number;
  in_progress_runs: number;
  completion_rate: number;
  abandonment_rate: number;
  avg_duration_seconds?: number | null;
  median_duration_seconds?: number | null;
  by_workflow: WorkflowMetricsItemSchema[];
}

// --- Sequences (orchestrator catalog) ------------------------------------------------

// A declarative, best-effort cross-step prefill hint applied by the FE sequence runner: copy the
// entity id created by an earlier step (`from_step_index` -> its produced entity) into this step's
// collect field `target_field`. Carries NO executable logic and grants NO access — the underlying
// workflow still validates + authorizes its own inputs at execute time.
export interface SequencePrefillSchema {
  target_field: string;
  from_step_index: number;
}

export interface SequenceStepSchema {
  workflow_id: string;
  title: string;
  description: string;
  can_start: boolean;
  prefill: SequencePrefillSchema[];
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

// --- Phase 3: Guided onboarding (READ-ONLY aggregation) ------------------------------
//
// Every shape below mirrors a backend read-only rollup that CALLS existing domain services and
// reads their verdicts verbatim. Nothing here computes operational truth, and none of the getters
// write, start, or advance anything — they are discovery/advice surfaces only.

export interface OnboardingStageSchema {
  key: string;
  label: string;
  done: boolean;
  available: boolean;
  detail?: string | null;
}

export interface SiteOnboardingProgressSchema {
  site_id: number;
  site_name?: string | null;
  company_id?: number | null;
  completed_stages: number;
  total_stages: number;
  completion_rate: number; // fraction in [0, 1] over EVALUABLE stages
  stages: OnboardingStageSchema[];
}

export interface OnboardingProgressResponse {
  generated_at: string;
  scope: string; // "site" | "company" | "me"
  total_sites: number;
  items: SiteOnboardingProgressSchema[];
}

// One readiness dimension. `available` is false (with a `reason`) when the caller may not see it or
// the underlying service could not be read — the section degrades, the summary never errors.
export interface ReadinessSectionSchema {
  available: boolean;
  reason?: string | null;
  status?: string | null;
  summary?: string | null;
  data?: Record<string, unknown> | null;
}

export interface SiteReadinessSchema {
  site_id: number;
  site_name?: string | null;
  company_id?: number | null;
  telemetry_health: ReadinessSectionSchema;
  reconciliation: ReadinessSectionSchema;
  device_eligibility: ReadinessSectionSchema;
  expected_baseline: ReadinessSectionSchema;
}

export interface ReadinessSummaryResponse {
  generated_at: string;
  scope: string;
  total_sites: number;
  items: SiteReadinessSchema[];
}

// A single deterministic, READ-ONLY next-action hint. It is a link/suggestion only — never
// auto-started, and it never promotes, approves, maps devices, or declares semantics.
export interface RecommendationSchema {
  kind: string; // "workflow" | "sequence"
  workflow_id?: string | null;
  sequence_id?: string | null;
  title: string;
  reason: string;
  priority: number; // lower = more important
  target_site_id?: number | null;
  target_company_id?: number | null;
  blocked: boolean;
  blocked_reason?: string | null;
  route?: string | null;
}

export interface RecommendationsResponse {
  generated_at: string;
  scope: string;
  items: RecommendationSchema[];
}

// Versioned, READ-ONLY envelope bundling every authorized onboarding signal for a future AI
// advisor to reason over WITHOUT being able to act. `mode` is always "read_only_advice" and
// `prohibited_actions` is the explicit, machine-readable non-execution contract.
export interface OrchestrationContextResponse {
  schema_version: string;
  mode: string;
  generated_at: string;
  actor_scope: string;
  available_workflows: WorkflowDefinitionSchema[];
  sequences: SequenceSchema[];
  runs_summary: WorkflowRunSummarySchema[];
  metrics: WorkflowMetricsResponse;
  progress: OnboardingProgressResponse;
  readiness: ReadinessSummaryResponse;
  recommendations: RecommendationSchema[];
  prohibited_actions: string[];
}

export interface OnboardingScopeParams {
  companyId?: number;
  siteId?: number;
  limit?: number;
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

  // --- Phase 3: read-only guided-onboarding aggregations -----------------------------
  // All four are pure GETs (no writes, no audit, never start/advance a run). They are scoped
  // owner/permission-side by the server; the optional params only narrow + cap the result set.

  getOnboardingProgress: async (params: OnboardingScopeParams = {}): Promise<OnboardingProgressResponse> => {
    const search = new URLSearchParams();
    if (params.companyId != null) search.append('company_id', String(params.companyId));
    if (params.siteId != null) search.append('site_id', String(params.siteId));
    if (params.limit != null) search.append('limit', String(params.limit));
    const qs = search.toString();
    const { data } = await httpClient.get<OnboardingProgressResponse>(
      `${WF}/onboarding/progress${qs ? `?${qs}` : ''}`
    );
    return data;
  },

  getReadiness: async (params: OnboardingScopeParams = {}): Promise<ReadinessSummaryResponse> => {
    const search = new URLSearchParams();
    if (params.companyId != null) search.append('company_id', String(params.companyId));
    if (params.siteId != null) search.append('site_id', String(params.siteId));
    if (params.limit != null) search.append('limit', String(params.limit));
    const qs = search.toString();
    const { data } = await httpClient.get<ReadinessSummaryResponse>(
      `${WF}/onboarding/readiness${qs ? `?${qs}` : ''}`
    );
    return data;
  },

  getRecommendations: async (limit?: number): Promise<RecommendationsResponse> => {
    const qs = limit != null ? `?limit=${limit}` : '';
    const { data } = await httpClient.get<RecommendationsResponse>(`${WF}/recommendations${qs}`);
    return data;
  },

  getOrchestrationContext: async (limit?: number): Promise<OrchestrationContextResponse> => {
    const qs = limit != null ? `?limit=${limit}` : '';
    const { data } = await httpClient.get<OrchestrationContextResponse>(`${WF}/orchestration/context${qs}`);
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

  // Multipart execute for steps declaring `multipart_file_field` (e.g. document upload). The
  // confirm token + optional idempotency key travel as form fields (the body is multipart); the
  // engine runs the identical perm/idempotency/reconfirm/audit pipeline before dispatching to the
  // EXISTING upload endpoint. Bytes never enter the run's JSONB state.
  executeFile: async (runId: number, stepId: string, body: ExecuteRequest, file: File): Promise<ExecuteResponse> => {
    const form = new FormData();
    form.append('confirm_token', body.confirm_token);
    if (body.idempotency_key) form.append('idempotency_key', body.idempotency_key);
    form.append('file', file);
    const { data } = await httpClient.post<ExecuteResponse>(`${WF}/runs/${runId}/steps/${stepId}/execute-file`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
  },

  // Read-only completion metrics. `scope=me` (default) is owner-scoped; `scope=all` requires a
  // platform-bypass caller server-side (otherwise 403).
  getMetrics: async (scope: WorkflowMetricsScope = 'me'): Promise<WorkflowMetricsResponse> => {
    const { data } = await httpClient.get<WorkflowMetricsResponse>(`${WF}/metrics?scope=${scope}`);
    return data;
  },

  abandon: async (runId: number): Promise<AbandonResponse> => {
    const { data } = await httpClient.post<AbandonResponse>(`${WF}/runs/${runId}/abandon`);
    return data;
  }
});

export type WorkflowsApi = ReturnType<typeof buildWorkflowsApi>;
