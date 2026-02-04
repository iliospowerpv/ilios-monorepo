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

export interface CanonicalField {
  id: number;
  name: string;
  display_name: string;
  field_type: string;
  validation_regex: string | null;
  description: string | null;
  is_active: boolean;
}

export interface DocumentType {
  id: number;
  name: string;
  display_name: string;
  category: string;
  is_parsable: boolean;
  is_active: boolean;
}

export interface SchemaVersionField {
  canonical_field_id: number;
  field_name: string;
  field_display_name: string;
  field_type: string;
  is_required: boolean;
  extraction_priority: number;
}

export interface SchemaVersion {
  id: number;
  document_type_id: number;
  version: number;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  fields: SchemaVersionField[];
}

export interface PromptTemplate {
  id: number;
  document_type_id: number;
  version: number;
  is_active: boolean;
  system_prompt: string | null;
  extraction_prompt: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  notes: string | null;
  created_at: string;
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

  const getCanonicalFields = async (activeOnly = true): Promise<CanonicalField[]> => {
    const response = await httpClient.get<CanonicalField[]>('/api/admin/extraction/canonical-fields', {
      params: { active_only: activeOnly }
    });
    return response.data;
  };

  const getDocumentTypes = async (activeOnly = true): Promise<DocumentType[]> => {
    const response = await httpClient.get<DocumentType[]>('/api/admin/extraction/document-types', {
      params: { active_only: activeOnly }
    });
    return response.data;
  };

  const createDocumentType = async (data: {
    name: string;
    display_name: string;
    category?: string;
    is_parsable?: boolean;
  }): Promise<DocumentType> => {
    const response = await httpClient.post<DocumentType>('/api/admin/extraction/document-types', data);
    return response.data;
  };

  const updateDocumentType = async (id: number, data: Partial<DocumentType>): Promise<DocumentType> => {
    const response = await httpClient.patch<DocumentType>(`/api/admin/extraction/document-types/${id}`, data);
    return response.data;
  };

  const getSchemaVersions = async (docTypeId: number): Promise<SchemaVersion[]> => {
    const response = await httpClient.get<SchemaVersion[]>(
      `/api/admin/extraction/document-types/${docTypeId}/schema-versions`
    );
    return response.data;
  };

  const createSchemaVersion = async (
    docTypeId: number,
    data: { notes?: string; clone_from_version_id?: number }
  ): Promise<SchemaVersion> => {
    const response = await httpClient.post<SchemaVersion>(
      `/api/admin/extraction/document-types/${docTypeId}/schema-versions`,
      data
    );
    return response.data;
  };

  const activateSchemaVersion = async (versionId: number): Promise<{ activated: boolean }> => {
    const response = await httpClient.post<{ activated: boolean }>(
      `/api/admin/extraction/schema-versions/${versionId}/activate`
    );
    return response.data;
  };

  const getPromptTemplates = async (docTypeId: number): Promise<PromptTemplate[]> => {
    const response = await httpClient.get<PromptTemplate[]>(
      `/api/admin/extraction/document-types/${docTypeId}/prompt-templates`
    );
    return response.data;
  };

  const createPromptTemplate = async (docTypeId: number, data: Partial<PromptTemplate>): Promise<PromptTemplate> => {
    const response = await httpClient.post<PromptTemplate>(
      `/api/admin/extraction/document-types/${docTypeId}/prompt-templates`,
      data
    );
    return response.data;
  };

  const updatePromptTemplate = async (templateId: number, data: Partial<PromptTemplate>): Promise<PromptTemplate> => {
    const response = await httpClient.patch<PromptTemplate>(
      `/api/admin/extraction/prompt-templates/${templateId}`,
      data
    );
    return response.data;
  };

  const activatePromptTemplate = async (templateId: number): Promise<{ activated: boolean }> => {
    const response = await httpClient.post<{ activated: boolean }>(
      `/api/admin/extraction/prompt-templates/${templateId}/activate`
    );
    return response.data;
  };

  return Object.freeze({
    getAccessHealth,
    repairOrphanedMemberships,
    repairInv1Violations,
    getCanonicalFields,
    getDocumentTypes,
    createDocumentType,
    updateDocumentType,
    getSchemaVersions,
    createSchemaVersion,
    activateSchemaVersion,
    getPromptTemplates,
    createPromptTemplate,
    updatePromptTemplate,
    activatePromptTemplate
  });
};
