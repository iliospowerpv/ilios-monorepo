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

interface DocumentDataResponse {
  status: string;
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

  const setDocumentKeyValue = async (args: SetDocumentKeyValueArgs): Promise<SetDocumentKeyValueResponse> => {
    const { siteId, documentId, params } = args;
    const response = await httpClient.put<SetDocumentKeyValueResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/keys`,
      params
    );
    return response.data;
  };

  const documentStartParsing = async (
    fileId: number,
    siteId: number,
    documentId: number
  ): Promise<FileDataResponse> => {
    const response = await httpClient.post<FileDataResponse>(
      `/api/due-diligence/${siteId}/documents/${documentId}/files/${fileId}/parsing/`,
      {}
    );
    return response?.data;
  };

  const documentParsingStatus = async (
    fileId: number,
    siteId: number,
    documentId: number
  ): Promise<DocumentDataResponse> => {
    const response = await httpClient.get<DocumentDataResponse>(
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
    setDocumentKeyValue,
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
    getCoTerminusExecutionStop
  });
};

export type {
  FileItem,
  FileDataResponse,
  UrlUpload,
  AgreementType,
  AgreementTypes,
  AgreementTerm,
  AgreementTerms,
  DiligenceDetailsList,
  DiligenceItem,
  DiligenceDocument
};
