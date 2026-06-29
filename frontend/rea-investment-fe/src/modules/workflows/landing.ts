import dayjs from 'dayjs';

/**
 * Resolve a workflow definition's landing-route template (e.g. `/project-hub/companies/{entity_id}`)
 * against a produced entity id. Returns null when either is missing so callers can hide dead links
 * rather than navigating to a broken URL.
 */
export function resolveLandingRoute(
  template: string | null | undefined,
  entityId: number | null | undefined
): string | null {
  if (!template || entityId == null) return null;
  return template.replace('{entity_id}', String(entityId));
}

/**
 * Workflow run timestamps are stored naive-UTC. Append `Z` when no timezone marker is present so the
 * browser renders them in local time instead of treating the naive value as already-local.
 */
export function formatRunTimestamp(value?: string | null): string {
  if (!value) return '—';
  const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`;
  const parsed = dayjs(normalized);
  return parsed.isValid() ? parsed.format('MMM D, YYYY h:mm A') : '—';
}

/**
 * Known single-workflow entry routes for the dashboard "Available" cards. The server remains the
 * authoritative permission boundary; this map only decides where a click navigates.
 */
export const WORKFLOW_START_ROUTES: Record<string, string> = {
  add_company: '/workflows/add-company',
  add_site: '/workflows/add-site',
  // Phase 2 workflows run through the generic start page, which wires multipart upload + cascading
  // option refresh (project -> documents -> files) that the bespoke add_* pages don't need.
  invite_user: '/workflows/start/invite_user',
  document_upload: '/workflows/start/document_upload',
  parse_document: '/workflows/start/parse_document'
};

/**
 * Bespoke entry routes for specific sequences. `onboarding` keeps its hand-built two-step
 * orchestrator page; any sequence NOT listed here falls back to the generic SequenceRunnerPage.
 */
export const SEQUENCE_START_ROUTES: Record<string, string> = {
  onboarding: '/workflows/onboarding'
};

/**
 * Resolve where a "Suggested" sequence card navigates. Bespoke pages win when registered; all other
 * sequences (e.g. site_diligence, portfolio_setup) run through the generic runner.
 */
export function resolveSequenceRoute(sequenceId: string): string {
  return SEQUENCE_START_ROUTES[sequenceId] ?? `/workflows/sequences/${sequenceId}`;
}
