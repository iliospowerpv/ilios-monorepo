import axios, { AxiosInstance } from 'axios';

interface DocumentUser {
  id: number;
  first_name: string;
  last_name: string;
}

interface DocumentTaskStatus {
  name: string;
  id: number;
}

interface DocumentTask {
  id: number;
  board_id: number;
  name: string;
  priority: 'Low' | 'Medium' | 'High';
  due_date: string | null;
  assignee: DocumentUser | null;
  status: DocumentTaskStatus;
  summary_of_events: string | null;
  site_visit_added: boolean;
}

interface DocumentDetails {
  id: number;
  name: string;
  type: string | null;
  site: {
    id: number;
    name: string;
    address: string;
  };
  section: {
    id: number;
    name: string;
  };
  description: string | null;
  summary_of_events: string | null;
  approver: DocumentUser | null;
  task: DocumentTask;
  display_working_zone: boolean;
}

interface UpdateDocDescriptionResponse {
  message: string;
  code: number;
}

interface CreateDocumentCommentResponse {
  message: string;
  code: number;
}

interface GetDocumentCommentsParams {
  documentId: number;
  skip?: number;
  limit?: number;
  module?: string;
}

interface DocumentComment {
  id: number;
  entity_id: number;
  text: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
}

interface GetDocumentCommentsResponse {
  skip: number;
  limit: number;
  total: number;
  items: DocumentComment[];
}
interface DiligenceDocument {
  files_count: number;
  id: number;
  name: string;
  status: string;
  assignee: {
    id: number;
    first_name: string;
    last_name: string;
  } | null;
  ai_supported: boolean;
  custom_name?: string | null;
  display_name?: string | null;
}
interface DiligenceItem {
  name: string;
  documents_count: number;
  completed_tasks_percentage: number | null;
  documents: DiligenceDocument[];
  related_sections: DiligenceItem[];
}
interface DiligenceDetailsList {
  items: DiligenceItem[];
}

interface FileDataResponse {
  message: string;
  code: number;
}

interface ParseTriggerResponse {
  run_id: number;
  correlation_id: string;
  status: string;
  code: number;
  message: string;
}

interface ParsingStatusResponse {
  status: string;
  run_id?: number;
  correlation_id?: string;
  error_message?: string;
  char_count?: number;
  word_count?: number;
  page_count?: number;
  was_truncated?: boolean;
  truncated_char_count?: number;
}

interface FileItem {
  id: number;
  author: string;
  filename: string;
  extension: string;
  created_at: string;
  is_actual: boolean;
}

interface FileList {
  items: FileItem[];
}

interface FileDownload {
  download_url: string;
}

interface FilePreview {
  preview_url: string;
}

interface UrlUpload {
  filepath: string;
  upload_url: string;
}

interface SetDocumentKeyValueArgs {
  documentId: number;
  siteId: number;
  params: {
    name: string;
    value: string;
  };
}

interface SetDocumentKeyValueResponse {
  message: string;
  code: number;
  id: number;
}

interface BulkAcceptAIValuesArgs {
  documentId: number;
  siteId: number;
  fileId: number;
  runId: number;
  fields: Array<{ field_name: string; value: string | null }>;
  allowAcceptNonLatest?: boolean;
}

interface BulkAcceptAIValuesResponse {
  message: string;
  code: number;
  accepted_count: number;
  skipped_count: number;
  errors: string[];
}

interface ParseRunSchema {
  id: number;
  file_id: number;
  status: string;
  extraction_run_number: number | null;
  document_type_id: number | null;
  schema_version_id: number | null;
  prompt_template_id: number | null;
  is_reprocess: boolean;
  force_reprocess: boolean;
  retries: number;
  error_message: string | null;
  start_time: string | null;
  end_time: string | null;
  created_at: string | null;
  correlation_id: string | null;
  was_truncated: boolean | null;
  char_count: number | null;
  word_count: number | null;
  page_count: number | null;
  is_latest: boolean;
  extracted_fields?: Array<{
    field_name: string;
    value: string | null;
    confidence: number | null;
    evidence: {
      page: number | null;
      snippet: string | null;
      anchor_text: string | null;
    } | null;
  }>;
}

interface ParseRunHistoryResponse {
  file_id: number;
  runs: ParseRunSchema[];
  total: number;
}

interface GetParseRunHistoryArgs {
  siteId: number;
  documentId: number;
  fileId: number;
}

interface GetParseRunDetailArgs {
  siteId: number;
  documentId: number;
  fileId: number;
  runId: number;
}

interface GetFileParsingResultQueryArgs {
  siteId: number;
  documentId: number;
  fileId: number;
}

interface FileParsingTermComment {
  id: number;
  entity_id: number;
  text: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
}

interface FileParsingEvidence {
  page?: number | null;
  snippet?: string | null;
  anchor_text?: string | null;
}

interface FileParsingTermKeyResult {
  id: number | null;
  name: string;
  value: string | null;
  ai_value: string | null;
  is_poison_pill: boolean;
  poison_pill: string | null;
  poison_pill_detailed: string | null;
  updated_at: string | null;
  legal_term: string | null;
  comments: FileParsingTermComment[] | null;
  evidence?: FileParsingEvidence | null;
}

interface GetFileParsingResultQueryResponse {
  keys: FileParsingTermKeyResult[];
}

interface AgreementType {
  id: number;
  name: string;
}
interface AgreementTypes {
  items: AgreementType[];
}

interface AgreementTerm {
  name: string;
  value: string | null;
  updated_at: string | null;
}
interface AgreementTerms {
  items: AgreementTerm[];
}

interface UpdateDocumentDetailsArgs {
  siteId: number;
  documentId: number;
  attributes: UpdateDocumentDetailsAttributes;
}

interface UpdateDocumentDetailsAttributes {
  approver_id: number | null;
}

interface UpdateDocumentDetailsResponse {
  message: string;
  code: number;
}

interface UpdateFileArgs {
  siteId: number;
  fileId: number;
  documentId: number;
  attributes: UpdateFileAttributes;
}

interface UpdateFileAttributes {
  is_actual: boolean;
}

interface UpdateFileResponse {
  message: string;
  code: number;
}

interface InitCoTerminusCheckArgs {
  siteId: number;
}

interface InitCoTerminusCheckResponse {
  message: string;
  code: number;
}

type CoTerminusExecutionStatusQueryArgs = InitCoTerminusCheckArgs;
type CoTerminusCheckResultsQueryArgs = InitCoTerminusCheckArgs;

interface CoTerminusExecutionStatusQueryResponse {
  status:
    | null
    | 'Not Started'
    | 'Processing Timeout'
    | 'Processing Start Failed'
    | 'Processing'
    | 'Processing Failed'
    | 'Unprocessable File'
    | 'Completed';
  start_time: string | null;
  end_time: string | null;
  is_actual: boolean;
  duration: number | null;
  is_stuck: boolean;
}

interface TermCheckResult {
  name: string;
  status: string;
  sources: object;
}

interface CheckSummaryItem {
  status: string;
  count: number;
}

interface CoTerminusCheckResultsQueryResponse {
  items: TermCheckResult[] | null;
  summary: CheckSummaryItem[] | null;
}

interface ChatBotSessionQueryArgs {
  siteId: number;
}

interface ChatBotSessionQueryResponse {
  token: {
    access_token: string;
    token_type: string;
  };
  session_id: string;
}

interface CoTerminusStats {
  status: string | null;
  mismatches: number | null;
  last_run_at: string | null;
}

interface ProjectSummaryStatsResponse {
  documents_total: number;
  documents_with_promoted_terms: number;
  promoted_terms_total: number;
  coterminus: CoTerminusStats;
}

export const buildDueDiligenceApi = (httpClient: AxiosInstance) => {
  const docInfo = async (siteId: number, documentId: number): Promise<DocumentDetails> => {
    const response = await httpClient.get<DocumentDetails>(`/api/due-diligence/${siteId}/documents/${documentId}`);
    return response.data;
  };

  const updateDocDescription = async (
    siteId: number,
    documentId: number,
    description: string | null
  ): Promise<UpdateDocDescriptionResponse> => {
    const response = await httpClient.post<UpdateDocDescriptionResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/description`,
      {
        description
      }
    );
    return response.data;
  };

  const postDocumentComment = async (
    entityId: number,
    commentText: string,
    mentionedUsersIds: number[],
    entityType?: string,
    fileId?: number,
    permission_module?: string
  ): Promise<CreateDocumentCommentResponse> => {
    const payload: any = {
      entity_type: entityType || 'document',
      entity_id: entityId,
      text: commentText,
      mentioned_users_ids: mentionedUsersIds
    };

    if (fileId !== undefined && fileId !== null) {
      payload.extra = { file_id: fileId };
    }
    const permission = permission_module || 'Diligence';
    const response = await httpClient.post<CreateDocumentCommentResponse>(
      `/api/comments/?permission_module=${permission}`,
      payload
    );

    return response.data;
  };

  const documentComments = async (params: GetDocumentCommentsParams): Promise<GetDocumentCommentsResponse> => {
    const response = await httpClient.get(`/api/comments/?permission_module=${params?.module || 'Diligence'}`, {
      params: {
        entity_type: 'document',
        entity_id: params.documentId,
        skip: params.skip,
        limit: params.limit
      }
    });
    return response.data;
  };

  const getDocuments = async (siteId: number): Promise<DiligenceDetailsList> => {
    const response = await httpClient.get<DiligenceDetailsList>(`/api/due-diligence/${siteId}/documents/`);
    return response.data;
  };

  const getFiles = async (siteId: number, documentId: number): Promise<FileList> => {
    const response = await httpClient.get<FileList>(`/api/due-diligence/${siteId}/documents/${documentId}/files/`);
    return response.data;
  };

  const deleteFile = async (siteId: number, documentId: number, fileId: number): Promise<FileDataResponse> => {
    const response = await httpClient.delete<FileDataResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}`
    );
    return response.data;
  };

  const downloadFile = async (siteId: number, documentId: number, fileId: number): Promise<FileDownload> => {
    const response = await httpClient.get<FileDownload>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}`
    );
    return response.data;
  };

  const previewFile = async (siteId: number, documentId: number, fileId: number): Promise<FilePreview> => {
    const response = await httpClient.get<FilePreview>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/file-preview-url/`
    );
    return response.data;
  };

  const uploadUrl = async (filename: string, siteId: number, documentId: number): Promise<UrlUpload> => {
    const response = await httpClient.post<UrlUpload>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/upload-url/`,
      { filename: filename }
    );
    return response?.data;
  };

  const uploadFile = async (fileData: File, uploadUrl: string): Promise<any> => {
    const contentType =
      fileData.type.includes('pdf') || fileData.type.includes('office') || fileData.type.includes('word')
        ? 'application/octet-stream'
        : fileData.type;

    return axios.put(uploadUrl, fileData, {
      headers: {
        'Content-Type': contentType
      }
    });
  };

  const uploadConfirm = async (
    filepath: string,
    filename: string,
    siteId: number,
    documentId: number
  ): Promise<FileDataResponse> => {
    const response = await httpClient.post<FileDataResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/track-uploaded-file/`,
      { filepath: filepath, filename: filename }
    );
    return response?.data;
  };

  const uploadFileDirect = async (fileData: File, siteId: number, documentId: number): Promise<FileDataResponse> => {
    const formData = new FormData();
    formData.append('file', fileData);
    const response = await httpClient.post<FileDataResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );
    return response.data;
  };

  const downloadFileDirect = async (
    siteId: number,
    documentId: number,
    fileId: number,
    filename: string
  ): Promise<void> => {
    const response = await httpClient.get(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/download`,
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const previewFileDirect = async (siteId: number, documentId: number, fileId: number): Promise<string> => {
    const response = await httpClient.get(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/preview`,
      { responseType: 'blob' }
    );
    return window.URL.createObjectURL(new Blob([response.data]));
  };

  const setDocumentKeyValue = async (args: SetDocumentKeyValueArgs): Promise<SetDocumentKeyValueResponse> => {
    const { siteId, documentId, params } = args;
    const response = await httpClient.put<SetDocumentKeyValueResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/keys`,
      params
    );
    return response.data;
  };

  const bulkAcceptAIValues = async (args: BulkAcceptAIValuesArgs): Promise<BulkAcceptAIValuesResponse> => {
    const { siteId, documentId, fileId, runId, fields, allowAcceptNonLatest } = args;
    const response = await httpClient.post<BulkAcceptAIValuesResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/bulk-accept/`,
      {
        run_id: runId,
        fields: fields,
        allow_accept_non_latest: allowAcceptNonLatest || false
      }
    );
    return response.data;
  };

  const getParseRunHistory = async (args: GetParseRunHistoryArgs): Promise<ParseRunHistoryResponse> => {
    const { siteId, documentId, fileId } = args;
    const response = await httpClient.get<ParseRunHistoryResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/runs/`
    );
    return response.data;
  };

  const getParseRunDetail = async (args: GetParseRunDetailArgs): Promise<ParseRunSchema> => {
    const { siteId, documentId, fileId, runId } = args;
    const response = await httpClient.get<ParseRunSchema>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/runs/${runId}/`
    );
    return response.data;
  };

  const documentStartParsing = async (
    fileId: number,
    siteId: number,
    documentId: number,
    forceReprocess = false
  ): Promise<ParseTriggerResponse> => {
    const response = await httpClient.post<ParseTriggerResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/parsing/`,
      { force_reprocess: forceReprocess }
    );
    return response?.data;
  };

  const documentParsingStatus = async (
    fileId: number,
    siteId: number,
    documentId: number
  ): Promise<ParsingStatusResponse> => {
    const response = await httpClient.get<ParsingStatusResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/parsing-status/`,
      {}
    );
    return response?.data;
  };

  const getFileParsingResult = async (
    args: GetFileParsingResultQueryArgs
  ): Promise<GetFileParsingResultQueryResponse> => {
    const { siteId, documentId, fileId } = args;
    const response = await httpClient.get<GetFileParsingResultQueryResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/parsing-result/`
    );
    return response.data;
  };

  const getAgreementTypes = async (siteId: number): Promise<AgreementTypes> => {
    const response = await httpClient.get<AgreementTypes>(`/api/due-diligence/${siteId}/agreements/`);
    return response.data;
  };

  const getAgreementTerms = async (siteId: number, agreementId: number): Promise<AgreementTerms> => {
    const response = await httpClient.get<AgreementTerms>(
      `/api/due-diligence/${siteId}/agreements/${agreementId}/overview`
    );
    return response.data;
  };

  const updateDocumentDetails = async (args: UpdateDocumentDetailsArgs): Promise<UpdateDocumentDetailsResponse> => {
    const { siteId, documentId, attributes } = args;

    const response = await httpClient.post<UpdateDocumentDetailsResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/details`,
      attributes
    );
    return response.data;
  };

  const updateIsActualFile = async (args: UpdateFileArgs): Promise<UpdateFileResponse> => {
    const { siteId, fileId, documentId, attributes } = args;

    const response = await httpClient.put<UpdateFileResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/file-is-actual/`,
      attributes
    );
    return response?.data;
  };

  const initCoTerminusCheck = async (args: InitCoTerminusCheckArgs): Promise<InitCoTerminusCheckResponse> => {
    const { siteId } = args;

    const response = await httpClient.post<InitCoTerminusCheckResponse>(
      `/api/due-diligence/${siteId}/co-terminus/check`
    );
    return response?.data;
  };

  const getCoTerminusExecutionStatus = async (
    args: CoTerminusExecutionStatusQueryArgs
  ): Promise<CoTerminusExecutionStatusQueryResponse> => {
    const { siteId } = args;

    const response = await httpClient.get<CoTerminusExecutionStatusQueryResponse>(
      `/api/due-diligence/${siteId}/co-terminus/status`
    );
    return response?.data;
  };

  const getCoTerminusExecutionStop = async (
    args: CoTerminusExecutionStatusQueryArgs
  ): Promise<InitCoTerminusCheckResponse> => {
    const { siteId } = args;

    const response = await httpClient.get<InitCoTerminusCheckResponse>(`/api/due-diligence/${siteId}/co-terminus/stop`);
    return response?.data;
  };

  const getCoterminusCheckResults = async (
    args: CoTerminusCheckResultsQueryArgs
  ): Promise<CoTerminusCheckResultsQueryResponse> => {
    const { siteId } = args;

    const response = await httpClient.get<CoTerminusCheckResultsQueryResponse>(
      `/api/due-diligence/${siteId}/co-terminus/check`
    );
    return response?.data;
  };

  const getChatBotSession = async (args: ChatBotSessionQueryArgs): Promise<ChatBotSessionQueryResponse> => {
    const { siteId } = args;

    const response = await httpClient.get<ChatBotSessionQueryResponse>(
      `/api/due-diligence/chatbot/${siteId}/session-token`
    );

    return response.data;
  };

  const archiveDocument = async (siteId: number, documentId: number): Promise<{ code: number; message: string }> => {
    const response = await httpClient.post<{ code: number; message: string }>(
      `/api/due-diligence/${siteId}/documents/${documentId}/archive`
    );
    return response.data;
  };

  const reorderDocument = async (
    siteId: number,
    documentId: number,
    position: number
  ): Promise<{ code: number; message: string }> => {
    const response = await httpClient.post<{ code: number; message: string }>(
      `/api/due-diligence/${siteId}/documents/${documentId}/reorder`,
      { position }
    );
    return response.data;
  };

  const deleteDocument = async (siteId: number, documentId: number): Promise<{ code: number; message: string }> => {
    const response = await httpClient.delete<{ code: number; message: string }>(
      `/api/due-diligence/${siteId}/documents/${documentId}`
    );
    return response.data;
  };

  const createCustomDocument = async (
    siteId: number,
    sectionId: number,
    customName: string,
    description?: string
  ): Promise<{ code: number; message: string }> => {
    const response = await httpClient.post<{ code: number; message: string }>(
      `/api/due-diligence/${siteId}/documents/custom`,
      { section_id: sectionId, custom_name: customName, description }
    );
    return response.data;
  };

  const getSummaryStats = async (siteId: number): Promise<ProjectSummaryStatsResponse> => {
    const response = await httpClient.get<ProjectSummaryStatsResponse>(
      `/api/due-diligence/sites/${siteId}/summary-stats`
    );
    return response.data;
  };

  return Object.freeze({
    docInfo,
    updateDocDescription,
    postDocumentComment,
    documentComments,
    getDocuments,
    getFiles,
    deleteFile,
    downloadFile,
    previewFile,
    uploadUrl,
    uploadFile,
    uploadConfirm,
    uploadFileDirect,
    downloadFileDirect,
    previewFileDirect,
    setDocumentKeyValue,
    bulkAcceptAIValues,
    getParseRunHistory,
    getParseRunDetail,
    documentStartParsing,
    documentParsingStatus,
    getFileParsingResult,
    getAgreementTypes,
    getAgreementTerms,
    updateDocumentDetails,
    updateIsActualFile,
    initCoTerminusCheck,
    getCoTerminusExecutionStatus,
    getCoterminusCheckResults,
    getChatBotSession,
    getCoTerminusExecutionStop,
    archiveDocument,
    reorderDocument,
    deleteDocument,
    createCustomDocument,
    getSummaryStats
  });
};

export type {
  FileItem,
  FileDataResponse,
  ParseTriggerResponse,
  ParsingStatusResponse,
  UrlUpload,
  AgreementType,
  AgreementTypes,
  AgreementTerm,
  AgreementTerms,
  DiligenceDetailsList,
  DiligenceItem,
  DiligenceDocument
};
