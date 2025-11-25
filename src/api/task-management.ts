import axios, { AxiosInstance } from 'axios';
import type { Params } from './user';

interface SiteUser {
  id: number;
  first_name: string;
  last_name: string;
}

interface SiteUsersQueryResponse {
  items: SiteUser[];
}

interface SiteUsersQueryParams {
  search?: string;
}

interface GetBoardsQueryParams {
  skip?: number;
  limit?: number;
  module?: string;
}

interface BoardData {
  id: number;
  name: string | null;
  description: string | null;
  is_active: boolean;
}

interface GetBoardsQueryResponse {
  skip: number;
  limit: number;
  total: number;
  items: BoardData[];
}

interface TaskStatus {
  name: string;
  id: number;
}

interface CreateTaskAttributes {
  name: string;
  description: string | null;
  priority: string;
  due_date: string | null;
  assignee_id: number | null;
  affected_device_id?: number | null;
  status_id: number;
  alert_id?: number | null;
  alertSeverity?: string | null;
}

type UpdateTaskDetailsAttributes = Omit<CreateTaskAttributes, 'description'>;

interface CreateTaskResponse {
  message: string;
  code: number;
  entity_id: number;
}

interface GetSiteVisitsResponse {
  service_date: string;
  technician_assignee: string;
  reasons: string;
  scope_of_work: string;
  status: string;
  resolution: string;
  next_steps: string;
  pending_work: string;
  recommendations: string;
}

interface UpdateSiteVisitsResponse {
  service_date: string | null;
  technician_assignee: string | null;
  reasons: string | null;
  scope_of_work: string | null;
  status: string | null;
  resolution: string | null;
  next_steps: string | null;
  pending_work: string | null;
  recommendations: string | null;
}

type UpdateTaskDetailsResponse = Omit<CreateTaskResponse, 'entity_id'>;
type UpdateTaskDescriptionResponse = Omit<CreateTaskResponse, 'entity_id'>;

interface AffectedDevice {
  name: string;
  id: number;
}

interface SiteDeviceQueryResponse {
  items: AffectedDevice[];
}

interface Task {
  name: string;
  description: string | null;
  priority: 'Low' | 'Medium' | 'High';
  due_date: string | null;
  id: number;
  external_id: string;
  creator: SiteUser;
  assignee: SiteUser | null;
  status: TaskStatus;
  affected_device: AffectedDevice | null;
  alert_id?: number | null;
  summary_of_events: string | null;
  site_visit_added: boolean;
}

interface Status {
  id: number;
  name: string;
}
interface Statuses {
  items: Status[];
}

interface Assignee {
  id: number;
  first_name: string;
  last_name: string;
}

interface Creator {
  id: number;
  first_name: string;
  last_name: string;
}

interface TaskType {
  name: string;
  description: string;
  priority: string;
  due_date: string;
  id: number;
  external_id: string;
  creator: Creator;
  assignee: Assignee;
  status: Status;
  summary_of_events: string;
}

interface Tasks {
  skip: number;
  limit: number;
  total: number;
  items: TaskType[];
}

interface Board {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
}

interface Boards {
  skip: number;
  limit: number;
  total: number;
  items: Board[];
}

type TaskEntityTypeLinking = 'site' | 'company';
interface GetBoardParams {
  entityType: TaskEntityTypeLinking;
  entityId: number;
  module?: string;
  skip?: number;
  limit?: number;
}
interface GetTaskCommentsParams {
  module?: string;
  skip?: number;
  limit?: number;
}

interface TaskComment {
  id: number;
  entity_id: number;
  text: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
}

interface GetTaskCommentsResponse {
  skip: number;
  limit: number;
  total: number;
  items: TaskComment[];
}

interface PostTaskCommentResponse {
  message: string;
  code: number;
}

interface FileDataResponse {
  message: string;
  code: number;
}

interface FileItem {
  id: number;
  author: string;
  filename: string;
  extension: string;
  created_at: string;
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

interface PotentialTaskAssigneesQueryParams {
  search?: string;
  task_id?: number;
}

interface PotentialTaskAssigneesQueryResponse {
  items: Assignee[] | null;
}

export const buildTaskManagementApi = (httpClient: AxiosInstance) => {
  const getBoard = async (params: GetBoardParams): Promise<Boards> => {
    const response = await httpClient.get<Boards>(`/api/task-tracker/boards/`, {
      params: {
        entity_type: params.entityType,
        entity_id: params.entityId,
        module: params.module || 'Asset',
        skip: params.skip,
        limit: params.limit
      }
    });
    return response.data;
  };

  const getTasks = async (boardId: number, params: Params): Promise<Tasks> => {
    const response = await httpClient.get<Tasks>(`/api/task-tracker/boards/${boardId}/tasks/`, { params });
    return response.data;
  };

  const getStatuses = async (boardId: number): Promise<Statuses> => {
    const response = await httpClient.get<Statuses>(`/api/task-tracker/boards/${boardId}/statuses/`);
    return response.data;
  };

  const siteUsers = async (siteId: number, params: SiteUsersQueryParams): Promise<SiteUsersQueryResponse> => {
    const response = await httpClient.get<SiteUsersQueryResponse>(`/api/sites/${siteId}/users`, { params });
    return response.data;
  };

  const siteDevice = async (siteId: number, params: SiteUsersQueryParams): Promise<SiteDeviceQueryResponse> => {
    const response = await httpClient.get<SiteDeviceQueryResponse>(`/api/sites/${siteId}/affected-devices`, { params });
    return response.data;
  };

  const boards = async (
    entityType: TaskEntityTypeLinking,
    entityId: number,
    params?: GetBoardsQueryParams
  ): Promise<GetBoardsQueryResponse> => {
    const response = await httpClient.get<GetBoardsQueryResponse>(`/api/task-tracker/boards/`, {
      params: {
        entity_type: entityType,
        entity_id: entityId,
        ...params
      }
    });
    return response.data;
  };

  const potentialTaskAssignees = async (
    boardId: number,
    params: PotentialTaskAssigneesQueryParams
  ): Promise<PotentialTaskAssigneesQueryResponse> => {
    const response = await httpClient.get(`/api/task-tracker/boards/${boardId}/assignees`, { params });
    return response.data;
  };

  const createTask = async (boardId: number, data: CreateTaskAttributes): Promise<CreateTaskResponse> => {
    const response = await httpClient.post<CreateTaskResponse>(`/api/task-tracker/boards/${boardId}/tasks/`, data);
    return response.data;
  };

  const getTaskById = async (boardId: number, taskId: number): Promise<Task> => {
    const response = await httpClient.get<Task>(`/api/task-tracker/boards/${boardId}/tasks/${taskId}`);
    return response.data;
  };

  const updateTask = async (
    boardId: number,
    taskId: number,
    data: UpdateTaskDetailsAttributes
  ): Promise<UpdateTaskDetailsResponse> => {
    const response = await httpClient.put<UpdateTaskDetailsResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/details`,
      data
    );
    return response.data;
  };

  const updateTaskDescription = async (
    boardId: number,
    taskId: number,
    description: string | null
  ): Promise<UpdateTaskDescriptionResponse> => {
    const response = await httpClient.put<UpdateTaskDescriptionResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/description`,
      {
        description
      }
    );
    return response.data;
  };

  const createSiteVisit = async (boardId: number, taskId: string): Promise<CreateTaskResponse> => {
    const response = await httpClient.post<CreateTaskResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits`,
      {}
    );
    return response.data;
  };

  const getSiteVisit = async (boardId: number, taskId: string): Promise<GetSiteVisitsResponse> => {
    const response = await httpClient.get<GetSiteVisitsResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits`
    );
    return response.data;
  };

  const updateSiteVisit = async (
    boardId: number,
    taskId: number,
    data: UpdateSiteVisitsResponse
  ): Promise<CreateTaskResponse> => {
    const response = await httpClient.put<CreateTaskResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits`,
      data
    );
    return response.data;
  };

  const updateSummaryOfEvents = async (
    boardId: number,
    taskId: number,
    summary_of_events: string | null
  ): Promise<UpdateTaskDescriptionResponse> => {
    const response = await httpClient.put<UpdateTaskDescriptionResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/summary-of-events`,
      {
        summary_of_events
      }
    );
    return response.data;
  };

  const taskComments = async (taskId: number, params: GetTaskCommentsParams): Promise<GetTaskCommentsResponse> => {
    const response = await httpClient.get<GetTaskCommentsResponse>(
      `/api/comments/?permission_module=${params?.module || 'Asset Management'}`,
      {
        params: {
          entity_type: 'task',
          entity_id: taskId,
          skip: params.skip,
          limit: params.limit
        }
      }
    );
    return response.data;
  };

  const postTaskComment = async (
    taskId: number,
    commentText: string,
    mentions: number[],
    permission_module?: string
  ): Promise<PostTaskCommentResponse> => {
    const response = await httpClient.post<PostTaskCommentResponse>(
      `/api/comments/?permission_module=${permission_module || 'Asset Management'}`,
      {
        entity_type: 'task',
        entity_id: taskId,
        text: commentText,
        mentioned_users_ids: mentions
      }
    );
    return response.data;
  };

  const getFiles = async (boardId: number, taskId: number): Promise<FileList> => {
    const response = await httpClient.get<FileList>(`/api/task-tracker/boards/${boardId}/tasks/${taskId}/attachments/`);
    return response.data;
  };

  const deleteFile = async (boardId: number, taskId: number, fileId: number): Promise<FileDataResponse> => {
    const response = await httpClient.delete<FileDataResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/attachments/${fileId}`
    );
    return response.data;
  };

  const downloadFile = async (boardId: number, taskId: number, fileId: number): Promise<FileDownload> => {
    const response = await httpClient.get<FileDownload>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/attachments/${fileId}`
    );
    return response.data;
  };

  const previewFile = async (boardId: number, taskId: number, fileId: number): Promise<FilePreview> => {
    const response = await httpClient.get<FilePreview>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/attachments/${fileId}/file-preview-url/`
    );
    return response.data;
  };

  const uploadUrl = async (filename: string, boardId: number, taskId: number): Promise<UrlUpload> => {
    const response = await httpClient.post<UrlUpload>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/attachments/upload-url`,
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
    boardId: number,
    taskId: number
  ): Promise<FileDataResponse> => {
    const response = await httpClient.post<FileDataResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/attachments/track-uploaded-attachment`,
      { filepath: filepath, filename: filename }
    );
    return response?.data;
  };

  const getSiteConditions = async (boardId: number, taskId: number): Promise<FileList> => {
    const response = await httpClient.get<FileList>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/site-conditions`
    );
    return response.data;
  };

  const deleteSiteConditions = async (boardId: number, taskId: number, fileId: number): Promise<FileDataResponse> => {
    const response = await httpClient.delete<FileDataResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/site-conditions/${fileId}`
    );
    return response.data;
  };

  const downloadSiteConditions = async (boardId: number, taskId: number, fileId: number): Promise<FileDownload> => {
    const response = await httpClient.get<FileDownload>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/site-conditions/${fileId}`
    );
    return response.data;
  };

  const previewSiteConditions = async (boardId: number, taskId: number, fileId: number): Promise<FilePreview> => {
    const response = await httpClient.get<FilePreview>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/site-conditions/${fileId}/file-preview-url`
    );
    return response.data;
  };

  const uploadSiteConditions = async (filename: string, boardId: number, taskId: number): Promise<UrlUpload> => {
    const response = await httpClient.post<UrlUpload>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/site-conditions/upload-url`,
      { filename: filename }
    );
    return response?.data;
  };

  const uploadSiteConditionsConfirm = async (
    filepath: string,
    filename: string,
    boardId: number,
    taskId: number
  ): Promise<FileDataResponse> => {
    const response = await httpClient.post<FileDataResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/site-conditions/track-uploaded-attachment`,
      { filepath: filepath, filename: filename }
    );
    return response?.data;
  };

  const getFieldDiscovery = async (boardId: number, taskId: number): Promise<FileList> => {
    const response = await httpClient.get<FileList>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/field-discovery`
    );
    return response.data;
  };

  const deleteFieldDiscovery = async (boardId: number, taskId: number, fileId: number): Promise<FileDataResponse> => {
    const response = await httpClient.delete<FileDataResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/field-discovery/${fileId}`
    );
    return response.data;
  };

  const downloadFieldDiscovery = async (boardId: number, taskId: number, fileId: number): Promise<FileDownload> => {
    const response = await httpClient.get<FileDownload>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/field-discovery/${fileId}`
    );
    return response.data;
  };

  const previewFieldDiscovery = async (boardId: number, taskId: number, fileId: number): Promise<FilePreview> => {
    const response = await httpClient.get<FilePreview>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/field-discovery/${fileId}/file-preview-url`
    );
    return response.data;
  };

  const uploadFieldDiscovery = async (filename: string, boardId: number, taskId: number): Promise<UrlUpload> => {
    const response = await httpClient.post<UrlUpload>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/field-discovery/upload-url`,
      { filename: filename }
    );
    return response?.data;
  };

  const uploadFieldDiscoveryConfirm = async (
    filepath: string,
    filename: string,
    boardId: number,
    taskId: number
  ): Promise<FileDataResponse> => {
    const response = await httpClient.post<FileDataResponse>(
      `/api/task-tracker/boards/${boardId}/tasks/${taskId}/site-visits/field-discovery/track-uploaded-attachment`,
      { filepath: filepath, filename: filename }
    );
    return response?.data;
  };

  return Object.freeze({
    getTasks,
    getBoard,
    getStatuses,
    updateTask,
    siteUsers,
    boards,
    createTask,
    getTaskById,
    updateTaskDescription,
    taskComments,
    postTaskComment,
    getFiles,
    deleteFile,
    downloadFile,
    previewFile,
    uploadUrl,
    uploadFile,
    uploadConfirm,
    siteDevice,
    potentialTaskAssignees,
    updateSummaryOfEvents,
    createSiteVisit,
    getSiteVisit,
    updateSiteVisit,
    getSiteConditions,
    deleteSiteConditions,
    downloadSiteConditions,
    previewSiteConditions,
    uploadSiteConditionsConfirm,
    uploadSiteConditions,
    getFieldDiscovery,
    deleteFieldDiscovery,
    downloadFieldDiscovery,
    previewFieldDiscovery,
    uploadFieldDiscoveryConfirm,
    uploadFieldDiscovery
  });
};

export type { Tasks, Boards, Status, Statuses, TaskType, Assignee, Creator };
