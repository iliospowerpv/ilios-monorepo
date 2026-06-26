import { AxiosInstance } from 'axios';

export type ReconciliationValue = string | number | boolean | null;

export type ReconciliationStatus =
  | 'missing'
  | 'ai_extracted_only'
  | 'accepted_document_value'
  | 'candidate_only'
  | 'accepted_not_promoted'
  | 'active_fact'
  | 'in_draft_baseline'
  | 'in_active_baseline'
  | 'superseded';

export type ReconciliationBlockingLevel =
  | 'blocks_baseline'
  | 'blocks_expected'
  | 'blocks_reporting'
  | 'lowers_confidence'
  | 'informational';

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

  status_label: string | null;
  status_explanation: string | null;
  required_action: string | null;
  blocking_level: ReconciliationBlockingLevel | string | null;
  missing_dependencies: string[];

  ai_extracted_value: ReconciliationValue;
  accepted_value: ReconciliationValue;
  active_fact_value: ReconciliationValue;
  draft_baseline_value: ReconciliationValue;
  active_baseline_value: ReconciliationValue;
  legacy_value: ReconciliationValue;

  fact_id: number | null;
  project_fact_id: number | null;
  source_file_id: number | null;
  source_document_type: string | null;
  source_run_id: number | null;
  evidence_page: number | null;
  evidence_snippet: string | null;
  confidence: number | null;
  effective_from: string | null;
  effective_to: string | null;

  // Navigation handles (read-only deep links the UI can resolve to existing routes).
  document_id: number | null;
  document_version_id: number | null;
  ai_run_id: number | null;
  document_key_id: number | null;
  baseline_id: number | null;
  baseline_point_id: number | null;
  aliases_matched: string[];

  supersedes_fact_id: number | null;
  candidate_count: number;
  required_for_baseline: boolean;

  warnings: (ReconciliationWarning | string)[];

  // Additive, read-only parse-state indicators for the source document version.
  // Null when the row has no source file or the signal does not apply. These are
  // purely informational and never drive status/blocking/needs_review/baseline.
  source_document_uploaded_not_parsed: boolean | null;
  parse_failed: boolean | null;
  parsed_no_usable_fields: boolean | null;
  source_document_not_current_version: boolean | null;
  source_document_type_lacks_operational_schema: boolean | null;
}

export type SourceBasisDriftState = 'up_to_date' | 'drifted' | 'basis_unknown' | 'source_retired';

export interface SourceBasisDriftField {
  field: string;
  basis_value: ReconciliationValue;
  current_value: ReconciliationValue;
  current_fact_id: number | null;
}

export interface SourceBasisDrift {
  /** Backend may add states later; keep the union open. */
  state: SourceBasisDriftState | string;
  baseline_id: number | null;
  basis_captured_at: string | null;
  unknown_basis: boolean;
  drifted_fields: SourceBasisDriftField[];
  no_fact_lineage_fields: string[];
  note: string;
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

  /** Read-only value-based source-basis verdict (Phase B4). Additive, nullable. */
  source_basis_drift: SourceBasisDrift | null;
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
