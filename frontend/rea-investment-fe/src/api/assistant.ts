import type { AxiosInstance } from 'axios';

// Base path. The shared httpClient baseURL is the backend origin only (no `/api`), so — like every
// other API module in this codebase — the `/api` prefix is part of the path here. The whole surface
// is gated behind the backend `native_assistant_enabled` flag — every endpoint 404s when the
// assistant is off, which is how the FE decides whether to mount the assistant at all (see `getConfig`).
const A = '/api/assistant';

// --- Read-only chat ------------------------------------------------------------------

export type AssistantRole = 'user' | 'assistant';
export type AssistantMode = 'read_only_advice';
// `open` deep-links an EXISTING read view (route derived server-side from `target_view`); `explain`
// re-submits its `prompt` into the read-only chat (it never navigates). Both stay propose-only.
export type AssistantActionCardKind = 'workflow' | 'sequence' | 'resume' | 'open' | 'explain';

// One prior turn supplied by the client (stateless reasoning path on the server).
export interface AssistantMessage {
  role: AssistantRole;
  content: string;
}

// Optional, advisory UI context. NEVER widens authorization — the server still resolves all data
// through its authz-scoped read-only tools. `project_id` is the UI alias of `site_id` (Project == Site).
// The workflow fields (set only while inside a guided wizard) let the assistant enter read-only
// "Workflow Companion Mode" by reading the run server-side — they carry NO form values/files/tokens.
export interface AssistantContextHints {
  route?: string | null;
  company_id?: number | null;
  site_id?: number | null;
  project_id?: number | null;
  run_id?: number | null;
  workflow_id?: string | null;
  step_id?: string | null;
}

// Transparency record of a single read-only tool the assistant invoked for a turn.
export interface AssistantToolInvocation {
  name: string;
  ok: boolean;
  error?: string | null;
}

// A LABELS-ONLY disclosure of a knowledge source backing a turn (curated FAQ entry / read-only data
// tool). Never carries raw tool payloads — just a stable label/identifier for transparency.
export interface AssistantSource {
  kind: 'faq' | 'tool';
  label: string;
  ref?: string | null;
  detail?: string | null;
}

export type AssistantFeedbackRating = 'up' | 'down';

// A PROPOSE-ONLY next step. It is a validated deep link into the EXISTING workflow UI — the assistant
// NEVER starts/executes it. The USER clicks it to navigate to the wizard/run where THEY perform the
// governed handshake. `requires_user_action` is always true.
export interface AssistantActionCard {
  kind: AssistantActionCardKind;
  title: string;
  reason: string;
  route: string;
  workflow_id?: string | null;
  sequence_id?: string | null;
  run_id?: number | null;
  // `open` cards carry the server-resolved destination enum (route is derived from it server-side).
  target_view?: string | null;
  // `explain` cards carry the read-only chat prompt the USER submits — they never navigate.
  prompt?: string | null;
  target_site_id?: number | null;
  target_company_id?: number | null;
  requires_user_action: boolean;
}

export interface AssistantChatRequest {
  message: string;
  history?: AssistantMessage[];
  context?: AssistantContextHints | null;
  // When set (or `persist` true) the turn is recorded in the isolated assistant conversation store
  // and the resolved conversation id is echoed back on the response.
  conversation_id?: string | null;
  persist?: boolean;
}

export interface AssistantChatResponse {
  schema_version: string;
  mode: AssistantMode;
  generated_at: string;
  conversation_id?: string | null;
  model: string;
  reply: string;
  used_tools: AssistantToolInvocation[];
  sources: AssistantSource[];
  action_cards: AssistantActionCard[];
  // Persisted assistant-turn id (only when the turn was stored), so feedback can attach to the
  // just-sent reply. Null for non-persisted chats.
  message_id?: number | null;
}

// --- Conversation persistence (isolated assistant store) -----------------------------

export interface AssistantPersistedMessage {
  id: number;
  role: AssistantRole;
  content: string;
  used_tools: AssistantToolInvocation[];
  sources: AssistantSource[];
  action_cards: AssistantActionCard[];
  model?: string | null;
  feedback?: AssistantFeedbackRating | null;
  feedback_note?: string | null;
  created_at: string;
}

// --- Suggested prompts / feedback / usage (Slice 3) ----------------------------------

export interface AssistantSuggestedPrompt {
  label: string;
  prompt: string;
}

export interface AssistantSuggestedPromptsResponse {
  context_label?: string | null;
  prompts: AssistantSuggestedPrompt[];
  // Proactive, route-aware navigator cards (Open existing read views / Explain this page). Always
  // permission-gated server-side; empty when nothing is offered for the caller's scope.
  action_cards: AssistantActionCard[];
}

export interface AssistantFeedbackRequest {
  rating: AssistantFeedbackRating | null;
  note?: string | null;
}

export interface AssistantFeedbackResponse {
  message_id: number;
  feedback?: AssistantFeedbackRating | null;
  feedback_note?: string | null;
}

export interface AssistantToolUsageStat {
  name: string;
  count: number;
}

export interface AssistantActionCardClickStat {
  kind: string;
  count: number;
}

// Aggregate UI-interaction counts over ONLY the isolated assistant_ui_events table. Pure adoption
// telemetry — no message/reply content, no business value, and no per-user data.
export interface AssistantInteractionStats {
  opens: number;
  dismissals: number;
  prompt_submissions: number;
  companion_prompt_submissions: number;
  suggested_prompt_clicks: number;
  sources_disclosures_opened: number;
  first_run_shown: number;
  first_run_dismissed: number;
  first_run_opened: number;
  proactive_hint_shown: number;
  proactive_hint_dismissed: number;
  proactive_hint_opened: number;
  discoverability_entry_clicks: number;
  action_card_clicks: AssistantActionCardClickStat[];
  events_total: number;
}

export interface AssistantUsageResponse {
  conversations_total: number;
  conversations_active: number;
  conversations_archived: number;
  messages_total: number;
  user_messages: number;
  assistant_messages: number;
  distinct_users: number;
  feedback_up: number;
  feedback_down: number;
  feedback_none: number;
  top_tools: AssistantToolUsageStat[];
  // First-party UI-interaction analytics (additive; default-empty for back-compat).
  interactions: AssistantInteractionStats;
}

// --- First-party UI-interaction analytics ingest (Task #89) --------------------------
// Privacy-bounded product telemetry the FE emits on user interactions. The payload carries ONLY a
// bounded event name + a coarse route (the SERVER normalizes it to a non-identifying bucket, with
// entity ids discarded) + a small allowlisted detail token + an in-companion flag. It NEVER includes
// prompt/reply content or any business/operational value. The assistant never writes it — only
// explicit human UI actions do. Kept in lockstep with the backend AssistantUiEventName enum.
export type AssistantUiEventName =
  | 'assistant_opened'
  | 'assistant_dismissed'
  | 'prompt_submitted'
  | 'suggested_prompt_clicked'
  | 'action_card_clicked'
  | 'sources_disclosure_opened'
  | 'first_run_shown'
  | 'first_run_dismissed'
  | 'first_run_opened'
  | 'proactive_hint_shown'
  | 'proactive_hint_dismissed'
  | 'proactive_hint_opened'
  | 'discoverability_entry_clicked';

export interface AssistantUiEventIn {
  event: AssistantUiEventName;
  // Raw client route; the server reduces it to a coarse bucket (entity ids discarded).
  route?: string | null;
  // Small, per-event allowlisted qualifier (e.g. an action card's kind); ignored otherwise.
  detail?: string | null;
  // Whether the interaction happened inside a guided workflow wizard (companion mode).
  in_companion?: boolean;
}

export interface AssistantUiEventBatchResponse {
  accepted: number;
}

export interface AssistantConversationSummary {
  id: number;
  title?: string | null;
  company_id?: number | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface AssistantConversationListResponse {
  items: AssistantConversationSummary[];
}

export interface AssistantConversationDetailResponse {
  id: number;
  title?: string | null;
  company_id?: number | null;
  created_at: string;
  updated_at: string;
  messages: AssistantPersistedMessage[];
}

export interface AssistantConfigResponse {
  enabled: boolean;
  model: string;
  mode: AssistantMode;
  available_tools: string[];
  prohibited_actions: string[];
}

export const buildAssistantApi = (httpClient: AxiosInstance) => ({
  // Probe + capability payload. Reachable ONLY when the flag is on (404 otherwise), so the FE treats
  // a successful fetch as "assistant available".
  getConfig: async (): Promise<AssistantConfigResponse> => {
    const { data } = await httpClient.get<AssistantConfigResponse>(`${A}/config`);
    return data;
  },

  // One read-only chat turn. The assistant can answer, cite the read-only tools it used, and propose
  // (never execute) inert deep-link action cards. It NEVER starts/executes/mutates anything.
  chat: async (body: AssistantChatRequest): Promise<AssistantChatResponse> => {
    const { data } = await httpClient.post<AssistantChatResponse>(`${A}/chat`, body);
    return data;
  },

  listConversations: async (limit?: number): Promise<AssistantConversationListResponse> => {
    const qs = limit != null ? `?limit=${limit}` : '';
    const { data } = await httpClient.get<AssistantConversationListResponse>(`${A}/conversations${qs}`);
    return data;
  },

  getConversation: async (conversationId: number): Promise<AssistantConversationDetailResponse> => {
    const { data } = await httpClient.get<AssistantConversationDetailResponse>(`${A}/conversations/${conversationId}`);
    return data;
  },

  // Soft-archive (owner-scoped). 204 on success; 404 when the thread isn't the caller's.
  deleteConversation: async (conversationId: number): Promise<void> => {
    await httpClient.delete(`${A}/conversations/${conversationId}`);
  },

  // Static, page-aware example prompts (+ proactive navigator cards). Pure UI affordance — no
  // business data is fetched. When a workflow run is supplied (the user is inside a wizard) the
  // server returns step-aware Workflow Companion prompts/cards instead. Identifiers only.
  getSuggestedPrompts: async (
    params: {
      route?: string | null;
      siteId?: number | null;
      companyId?: number | null;
      runId?: number | null;
      workflowId?: string | null;
      stepId?: string | null;
    } = {}
  ): Promise<AssistantSuggestedPromptsResponse> => {
    const qs = new URLSearchParams();
    if (params.route) qs.set('route', params.route);
    if (params.siteId != null) qs.set('site_id', String(params.siteId));
    if (params.companyId != null) qs.set('company_id', String(params.companyId));
    if (params.runId != null) qs.set('run_id', String(params.runId));
    if (params.workflowId) qs.set('workflow_id', params.workflowId);
    if (params.stepId) qs.set('step_id', params.stepId);
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    const { data } = await httpClient.get<AssistantSuggestedPromptsResponse>(`${A}/suggested-prompts${suffix}`);
    return data;
  },

  // Owner-scoped thumbs feedback on a persisted ASSISTANT message. `rating: null` clears it.
  setMessageFeedback: async (
    conversationId: number,
    messageId: number,
    body: AssistantFeedbackRequest
  ): Promise<AssistantFeedbackResponse> => {
    const { data } = await httpClient.post<AssistantFeedbackResponse>(
      `${A}/conversations/${conversationId}/messages/${messageId}/feedback`,
      body
    );
    return data;
  },

  // Admin-only read-only usage aggregate over the isolated assistant tables (403 for non-admins).
  getAdminUsage: async (): Promise<AssistantUsageResponse> => {
    const { data } = await httpClient.get<AssistantUsageResponse>(`${A}/admin/usage`);
    return data;
  },

  // Fire-and-forget, best-effort UI-interaction telemetry. Bounded enum payloads ONLY — never
  // message/reply content or business data (the server re-validates the allowlist and 404s when the
  // flag is off). Swallows every error so analytics can never disrupt the user. The 202 response
  // body ({ accepted }) is intentionally ignored by callers.
  trackEvents: async (events: AssistantUiEventIn[]): Promise<void> => {
    if (!events || events.length === 0) return;
    try {
      await httpClient.post(`${A}/events`, { events: events.slice(0, 50) });
    } catch {
      // best-effort: ignore network/HTTP failures (e.g. flag off → 404, offline, rate limit)
    }
  }
});

export type AssistantApi = ReturnType<typeof buildAssistantApi>;
