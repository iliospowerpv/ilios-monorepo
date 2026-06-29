import type { AxiosInstance } from 'axios';

// Base path (httpClient baseURL already includes `/api`). The whole surface is gated behind the
// backend `native_assistant_enabled` flag — every endpoint 404s when the assistant is off, which is
// how the FE decides whether to mount the assistant at all (see `getConfig`).
const A = '/assistant';

// --- Read-only chat ------------------------------------------------------------------

export type AssistantRole = 'user' | 'assistant';
export type AssistantMode = 'read_only_advice';
export type AssistantActionCardKind = 'workflow' | 'sequence' | 'resume';

// One prior turn supplied by the client (stateless reasoning path on the server).
export interface AssistantMessage {
  role: AssistantRole;
  content: string;
}

// Optional, advisory UI context. NEVER widens authorization — the server still resolves all data
// through its authz-scoped read-only tools. `project_id` is the UI alias of `site_id` (Project == Site).
export interface AssistantContextHints {
  route?: string | null;
  company_id?: number | null;
  site_id?: number | null;
  project_id?: number | null;
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

  // Static, page-aware example prompts. Pure UI affordance — no business data is fetched.
  getSuggestedPrompts: async (
    params: { route?: string | null; siteId?: number | null; companyId?: number | null } = {}
  ): Promise<AssistantSuggestedPromptsResponse> => {
    const qs = new URLSearchParams();
    if (params.route) qs.set('route', params.route);
    if (params.siteId != null) qs.set('site_id', String(params.siteId));
    if (params.companyId != null) qs.set('company_id', String(params.companyId));
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
  }
});

export type AssistantApi = ReturnType<typeof buildAssistantApi>;
