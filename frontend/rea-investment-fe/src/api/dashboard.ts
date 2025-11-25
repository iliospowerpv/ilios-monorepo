import type { AxiosInstance } from 'axios';

interface DashboardTasks {
  skip: number;
  limit: number;
  total: number;
  items: DashboardTask[];
}

interface User {
  id: number;
  first_name: string;
  last_name: string;
}

interface Status {
  id: number;
  name: string;
}

interface DashboardTask {
  name: string;
  priority: string;
  due_date: string;
  id: number;
  creator: User;
  assignee: User;
  status: Status;
  module: string;
}

interface Params {
  skip?: number;
  limit?: number;
}

interface Notification {
  id: number;
  created_at: string;
  kind: string;
  seen: boolean;
  extra?: {
    new_assignee?: string;
    previous_assignee?: string;
    status?: string;
    file_id?: number;
    document_id?: number;
  };
  site: {
    id: number;
    name: string;
  };
  task: {
    id: number;
    external_id: string;
    module?: string;
  };
  actor: {
    id: number;
    first_name: string;
    last_name: string;
  };
  company: {
    id: number;
    name: string;
  };
  comment?: {
    entity_id: number;
    entity_type: string;
    text: string;
  };
}
interface Notifications {
  skip: number;
  limit: number;
  total: number;
  unread_count: number;
  items: Notification[];
}

interface NotificationResponse {
  message: string;
  code: number;
}

export const buildDashboardApi = (httpClient: AxiosInstance) => {
  const getDashboardTasks = async (params: Params): Promise<DashboardTasks> => {
    const response = await httpClient.get<DashboardTasks>('/api/account/dashboard/tasks', { params });
    return response.data;
  };

  const getDashboardNotifications = async (params: Params): Promise<Notifications> => {
    const response = await httpClient.get<Notifications>('/api/account/dashboard/notifications', { params });
    return response.data;
  };

  const deleteNotification = async (notificationId: number): Promise<NotificationResponse> => {
    const response = await httpClient.delete<NotificationResponse>(
      `/api/account/dashboard/notifications/${notificationId}`
    );
    return response.data;
  };

  const markAsReadNotification = async (notificationId: number): Promise<NotificationResponse> => {
    const response = await httpClient.patch<NotificationResponse>(
      `/api/account/dashboard/notifications/${notificationId}/seen`
    );
    return response.data;
  };

  return Object.freeze({
    getDashboardTasks,
    getDashboardNotifications,
    deleteNotification,
    markAsReadNotification
  });
};

export type { DashboardTasks, DashboardTask, Notification, Notifications };
