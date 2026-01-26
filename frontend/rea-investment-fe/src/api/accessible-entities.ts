import type { AxiosInstance } from 'axios';

export interface AccessibleCompany {
  id: number;
  name: string;
}

export interface AccessibleProject {
  id: number;
  name: string;
  company_id: number;
  company_name: string;
}

export interface AccessibleEntitiesResponse {
  companies: AccessibleCompany[];
  projects: AccessibleProject[];
}

export const buildAccessibleEntitiesApi = (httpClient: AxiosInstance) => {
  const getAccessibleEntities = async (): Promise<AccessibleEntitiesResponse> => {
    const response = await httpClient.get<AccessibleEntitiesResponse>('/api/users/account/me/accessible-entities');
    return response.data;
  };

  return Object.freeze({
    getAccessibleEntities
  });
};
