import type { AxiosInstance } from 'axios';

export interface ValidationIssue {
  issue_type: string;
  table: string;
  record_id: number;
  details: string;
}

export interface ValidationResult {
  check_name: string;
  description: string;
  passed: boolean;
  issue_count: number;
  issues: ValidationIssue[];
}

export interface RepairResult {
  repair_type: string;
  records_fixed: number;
  success: boolean;
  message: string;
}

export interface AccessHealthResponse {
  validations: ValidationResult[];
  overall_healthy: boolean;
  total_issues: number;
}

export const buildAdminApi = (httpClient: AxiosInstance) => {
  const getAccessHealth = async (): Promise<AccessHealthResponse> => {
    const response = await httpClient.get<AccessHealthResponse>('/api/admin/access-health');
    return response.data;
  };

  const repairOrphanedMemberships = async (): Promise<RepairResult> => {
    const response = await httpClient.post<RepairResult>('/api/admin/access-health/repair/orphaned');
    return response.data;
  };

  const repairInv1Violations = async (): Promise<RepairResult> => {
    const response = await httpClient.post<RepairResult>('/api/admin/access-health/repair/inv1');
    return response.data;
  };

  return Object.freeze({
    getAccessHealth,
    repairOrphanedMemberships,
    repairInv1Violations
  });
};
