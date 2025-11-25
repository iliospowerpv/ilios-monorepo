import type { AxiosInstance } from 'axios';

interface GetBreadcrumbsParams {
  entity_type: string;
  entity_id: number;
  permission_module: string;
}

interface GetBreadcrumbsResponse {
  id: number;
  name: string;
  parent_id: number;
  parent_entity_type: string;
}

export const buildBreadcrumbsApi = (httpClient: AxiosInstance) => {
  const breadcrumbs = async (params: GetBreadcrumbsParams): Promise<GetBreadcrumbsResponse> => {
    const response = await httpClient.get(`/api/breadcrumbs/`, {
      params: {
        entity_type: params.entity_type,
        entity_id: params.entity_id,
        permission_module: params.permission_module
      }
    });
    return response.data;
  };

  return Object.freeze({
    breadcrumbs
  });
};

export type { GetBreadcrumbsParams, GetBreadcrumbsResponse };
