import type { ProjectHubTab } from '../../components/common/ProjectPicker/useProjectNavigation';

export type FocusType = 'document' | 'alert' | 'device' | 'task' | 'obligation' | 'budget' | null;

export interface TaskDestination {
  siteId: number | null;
  tab: ProjectHubTab;
  focusType: FocusType;
  focusId: number | null;
}

export interface AlertDestination {
  siteId: number | null;
  tab: ProjectHubTab;
  focusType: FocusType;
  focusId: number | null;
}

interface TaskData {
  id: number;
  module?: string;
  alert_id?: number | null;
  affected_device?: { id: number; name?: string } | null;
  affected_device_id?: number | null;
  document?: { id: number; site_id?: number; company_id?: number } | null;
  document_id?: number | null;
  site?: { id: number; company_id?: number; name?: string } | null;
  site_id?: number | null;
  company?: { id: number; name?: string } | null;
  extra?: {
    document_id?: number;
    file_id?: number;
    obligation_id?: number;
    budget_id?: number;
  } | null;
}

interface AlertData {
  id: number;
  site_id?: number | null;
  site?: { id: number; company_id?: number } | null;
  device_id?: number | null;
  device?: { id: number; name?: string } | null;
}

interface NotificationData {
  id: number;
  kind: string;
  task?: TaskData | null;
  site?: { id: number; name?: string } | null;
  company?: { id: number; name?: string } | null;
  comment?: {
    entity_type?: string;
    entity_id?: number;
    text?: string;
  } | null;
  extra?: {
    document_id?: number;
    file_id?: number;
  } | null;
}

export function resolveTaskDestination(task: TaskData): TaskDestination {
  const result: TaskDestination = {
    siteId: null,
    tab: 'tasks',
    focusType: 'task',
    focusId: task.id
  };

  if (task.site?.id) {
    result.siteId = task.site.id;
  } else if (task.site_id) {
    result.siteId = task.site_id;
  } else if (task.document?.site_id) {
    result.siteId = task.document.site_id;
  }

  if (task.document_id || task.document?.id) {
    result.tab = 'data-room';
    result.focusType = 'document';
    result.focusId = task.document_id || task.document?.id || null;
    return result;
  }

  if (task.alert_id) {
    result.tab = 'om';
    result.focusType = 'alert';
    result.focusId = task.alert_id;
    return result;
  }

  const deviceId = task.affected_device_id || task.affected_device?.id;
  if (deviceId) {
    result.tab = 'om';
    result.focusType = 'device';
    result.focusId = deviceId;
    return result;
  }

  if (task.extra?.obligation_id) {
    result.tab = 'finance';
    result.focusType = 'obligation';
    result.focusId = task.extra.obligation_id;
    return result;
  }

  if (task.extra?.budget_id) {
    result.tab = 'finance';
    result.focusType = 'budget';
    result.focusId = task.extra.budget_id;
    return result;
  }

  if (task.module === 'O&M') {
    result.tab = 'om';
  } else if (task.module === 'Diligence') {
    result.tab = 'data-room';
  } else if (task.module === 'Finance') {
    result.tab = 'finance';
  }

  return result;
}

export function resolveAlertDestination(alert: AlertData): AlertDestination {
  const result: AlertDestination = {
    siteId: null,
    tab: 'om',
    focusType: 'alert',
    focusId: alert.id
  };

  if (alert.site?.id) {
    result.siteId = alert.site.id;
  } else if (alert.site_id) {
    result.siteId = alert.site_id;
  }

  return result;
}

export function resolveNotificationDestination(notification: NotificationData): TaskDestination | AlertDestination {
  if (notification.kind === 'comment_mention' && notification.comment) {
    const siteId = notification.site?.id || null;

    if (notification.comment.entity_type === 'document_key' || notification.comment.entity_type === 'document') {
      const docId = notification.extra?.document_id || notification.comment.entity_id || null;
      return {
        siteId,
        tab: 'data-room',
        focusType: 'document',
        focusId: docId
      };
    }
  }

  if (notification.task) {
    const taskDest = resolveTaskDestination(notification.task);

    if (!taskDest.siteId && notification.site?.id) {
      taskDest.siteId = notification.site.id;
    }

    return taskDest;
  }

  return {
    siteId: notification.site?.id || null,
    tab: 'tasks',
    focusType: null,
    focusId: null
  };
}

export function buildProjectHubUrl(
  destination: TaskDestination | AlertDestination,
  baseTab?: ProjectHubTab
): string | null {
  if (!destination.siteId) {
    return null;
  }

  const tab = baseTab || destination.tab;
  const tabPath = tab === 'overview' ? '' : `/${tab}`;
  let url = `/project-hub/projects/${destination.siteId}${tabPath}`;

  if (destination.focusType && destination.focusId) {
    url += `?focusType=${destination.focusType}&focusId=${destination.focusId}`;
  }

  return url;
}
