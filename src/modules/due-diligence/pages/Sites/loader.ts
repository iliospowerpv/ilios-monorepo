import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';

export const companyCrumbsQuery = (companyId: number, enabled = true) =>
  queryOptions({
    queryKey: ['company', 'crumbs', 'Diligence', { companyId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: companyId,
        entity_type: 'company',
        permission_module: 'Diligence'
      }),
    enabled: enabled
  });

export const createDiligenceCompanyDetailsLoader =
  (queryClient: QueryClient) =>
  async ({ params }: LoaderFunctionArgs) => {
    const companyId = params.companyId;
    const isValidId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
    if (!isValidId) {
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    }
    const data = await queryClient.fetchQuery(companyCrumbsQuery(Number.parseInt(companyId)));
    return data;
  };
