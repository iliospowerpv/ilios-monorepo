// Local copy of the AI Assistant API type shapes (from
// frontend/rea-investment-fe/src/api/assistant.ts) so the real presentational
// components can be rendered in the mockup sandbox without pulling in the app's
// axios client / react-query / router. Type-only; erased at build time.

export type AssistantRole = 'user' | 'assistant';
export type AssistantMode = 'read_only_advice';
export type AssistantActionCardKind = 'workflow' | 'sequence' | 'resume';

export interface AssistantToolInvocation {
  name: string;
  ok: boolean;
  error?: string | null;
}

export interface AssistantSource {
  kind: 'faq' | 'tool';
  label: string;
  ref?: string | null;
  detail?: string | null;
}

export type AssistantFeedbackRating = 'up' | 'down';

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

export interface AssistantSuggestedPrompt {
  label: string;
  prompt: string;
}
