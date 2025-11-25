import type { AxiosInstance } from 'axios';
import type { Params } from './user';

interface Site {
  id: number;
  name: string;
  address: string;
  company_name: string;
  company_id: number;
}
interface Sites {
  skip: number;
  limit: number;
  total: number;
  items: Site[];
}

export const buildSettingsApi = (httpClient: AxiosInstance) => {
  const sites = async (params: Params): Promise<Sites> => {
    const response = await httpClient.get<Sites>('/api/settings/sites/', { params });
    return response.data;
  };

  return Object.freeze({
    sites
  });
};

export type { Sites as SettingsSites };
