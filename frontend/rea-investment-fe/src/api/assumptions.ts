import { AxiosInstance } from 'axios';

/**
 * Project Assumptions API client.
 *
 * Wraps the backend promotion workflow mounted at
 * `/api/projects/{site_id}/assumptions`. `{site_id}` is the backend Site id
 * ("projects" is a URL word only — the Site entity is never renamed). These
 * endpoints power the read-only diff preview and the file-version-scoped
 * "Promote to Current Assumptions" action surfaced from the Reconciliation tab.
 *
 * Hard rules encoded by the backend (mirrored here for callers):
 * - Promotion is file-version-scoped and all-or-nothing. There is no
 *   field-level promote — promoting a version promotes every candidate fact on
 *   it and retires conflicting active facts.
 * - `removed` diff rows are informational only; promotion never retires them.
 */

export type PromotionChangeType = 'added' | 'changed' | 'removed';

export interface PromotionDiffChange {
  type: PromotionChangeType | string;
  field_name: string;
  field_id: number;
  current_value: string | null;
  new_value: string | null;
  current_source_file_id: number | null;
  new_source_file_id: number | null;
}

export interface PromotionDiffSummary {
  added: number;
  changed: number;
  removed: number;
}

export interface PromotionDiff {
  has_changes: boolean;
  changes: PromotionDiffChange[];
  summary: PromotionDiffSummary;
}

export interface ProjectFact {
  id: number;
  field_name: string | null;
  field_display_name: string | null;
  value: string | null;
  status: string;
  source_file_id: number | null;
  promoted_at: string | null;
}

export interface ActiveFactsResponse {
  site_id: number;
  facts: ProjectFact[];
  total: number;
}

export interface PromoteVersionPayload {
  document_id: number;
  file_id: number;
  notes?: string | null;
}

export interface PromoteVersionResponse {
  promoted: boolean;
  file_id: number;
  document_id: number;
  promotion_id: number;
  facts_promoted: number;
  diff: PromotionDiff;
}

export interface PromotionHistoryItem {
  id: number;
  document_id: number;
  file_id: number;
  promoted_by_id: number;
  promoted_at: string;
  notes: string | null;
  changes_summary: PromotionDiffSummary | null;
}

export interface PromotionHistoryResponse {
  site_id: number;
  promotions: PromotionHistoryItem[];
}

export const buildAssumptionsApi = (httpClient: AxiosInstance) => {
  const basePath = (siteId: number) => `/api/projects/${siteId}/assumptions`;

  /** Active project facts (current assumptions) for the site. Read-only. */
  const getActiveFacts = async (siteId: number): Promise<ActiveFactsResponse> => {
    const response = await httpClient.get<ActiveFactsResponse>(`${basePath(siteId)}/facts`);
    return response.data;
  };

  /** Candidate facts pending promotion for a specific file version. Read-only. */
  const getCandidateFacts = async (siteId: number, fileId: number): Promise<ActiveFactsResponse> => {
    const response = await httpClient.get<ActiveFactsResponse>(`${basePath(siteId)}/facts/candidates/${fileId}`);
    return response.data;
  };

  /**
   * Read-only preview of what promoting this file version would change. This is
   * the authoritative blast-radius payload and must be re-fetched at confirm
   * time (never reused stale) before a promotion is executed.
   */
  const getPromotionDiff = async (siteId: number, fileId: number): Promise<PromotionDiff> => {
    const response = await httpClient.post<PromotionDiff>(`${basePath(siteId)}/promotion/diff`, { file_id: fileId });
    return response.data;
  };

  /** Promote a file version to current assumptions. Write — atomic / all-or-nothing. */
  const promoteVersion = async (siteId: number, payload: PromoteVersionPayload): Promise<PromoteVersionResponse> => {
    const response = await httpClient.post<PromoteVersionResponse>(`${basePath(siteId)}/promote`, payload);
    return response.data;
  };

  /** Promotion audit trail for the site. Read-only. */
  const getPromotionHistory = async (siteId: number): Promise<PromotionHistoryResponse> => {
    const response = await httpClient.get<PromotionHistoryResponse>(`${basePath(siteId)}/promotions`);
    return response.data;
  };

  return Object.freeze({
    getActiveFacts,
    getCandidateFacts,
    getPromotionDiff,
    promoteVersion,
    getPromotionHistory
  });
};
