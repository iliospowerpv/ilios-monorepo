import type { AxiosInstance } from 'axios';
import type { Params } from './user';

interface AuditLog {
  id: number;
  user_name: string;
  user_email: string;
  source: string;
  action: string;
  is_success: boolean;
  details: string;
  created_at: string;
}
interface AuditLogs {
  skip: number;
  limit: number;
  total: number;
  items: AuditLog[];
}

export const buildAuditLogApi = (httpClient: AxiosInstance) => {
  const getAuditLogs = async (params: Params): Promise<AuditLogs> => {
    const response = await httpClient.get<AuditLogs>('/api/settings/audit-logs/', { params });
    return response.data;
  };

  return Object.freeze({
    getAuditLogs
  });
};

export type { AuditLog, AuditLogs };
