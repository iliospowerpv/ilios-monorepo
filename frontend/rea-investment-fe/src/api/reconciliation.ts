import { AxiosInstance } from 'axios';

export type ReconciliationValue = string | number | boolean | null;

export type ReconciliationStatus =
  | 'missing'
  | 'candidate_only'
  | 'active_fact'
  | 'in_draft_baseline'
  | 'in_active_baseline';

export type ReconciliationCategory =
  | 'baseline_physics'
  | 'design_estimate'
  | 'weather'
  | 'legal_commercial'
  | 'equipment'
  | 'warranty_permit_insurance'
  | 'other';

export type ReconciliationBaselineTarget = 'header_column' | 'points_monthly' | 'points_annual' | 'metadata' | 'none';

export type ReconciliationWarning =
  | 'missing_required_for_baseline'
  | 'fact_differs_from_legacy'
  | 'draft_differs_from_active'
  | 'active_baseline_outdated'
  | 'design_points_missing'
  | 'needs_review';

// Unions stay open (`| string`) so backend enum additions never break the build.
export interface ReconciliationRow {
  canonical_field: string;
  display_label: string;
  category: ReconciliationCategory | string;
  baseline_target: ReconciliationBaselineTarget | string;
  status: ReconciliationStatus | string;

  ai_extracted_value: ReconciliationValue;
  accepted_value: ReconciliationValue;
  active_fact_value: ReconciliationValue;
  draft_baseline_value: ReconciliationValue;
  active_baseline_value: ReconciliationValue;
  legacy_value: ReconciliationValue;

  fact_id: number | null;
  source_file_id: number | null;
  source_document_type: string | null;
  source_run_id: number | null;
  evidence_page: number | null;
  evidence_snippet: string | null;
  confidence: number | null;
  effective_from: string | null;
  effective_to: string | null;

  supersedes_fact_id: number | null;
  candidate_count: number;
  required_for_baseline: boolean;

  warnings: (ReconciliationWarning | string)[];
}

export interface ReconciliationReadiness {
  facts_to_draft_ready: boolean;
  missing_required_physics_fields: string[];
  facts_to_draft_warnings: string[];

  active_baseline_available: boolean;
  active_baseline_id: number | null;
  active_baseline_created_at: string | null;

  design_estimate_baseline_id: number | null;
  design_estimate_baseline_status: string | null;
  design_points_ready: boolean | null;
  design_points_present_months: number[];
  design_points_missing: string[];
  design_points_parse_errors: string[];
}

export interface TelemetryReality {
  available: boolean;
  note: string;
  last_reading_at: string | null;
}

export interface SiteReconciliationResponse {
  site_id: number;
  generated_at: string;
  rows: ReconciliationRow[];
  readiness: ReconciliationReadiness;
  telemetry_reality: TelemetryReality;
  help_targets: Record<string, string>;
  schema_expansion_recommended: boolean;
}

export const buildReconciliationApi = (httpClient: AxiosInstance) => {
  const getSiteReconciliation = async (siteId: number): Promise<SiteReconciliationResponse> => {
    const response = await httpClient.get<SiteReconciliationResponse>(
      `/api/due-diligence/sites/${siteId}/reconciliation`
    );
    return response.data;
  };

  return Object.freeze({
    getSiteReconciliation
  });
};
