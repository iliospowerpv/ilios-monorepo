import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';

export const siteDetailsQuery = (siteId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryKey: ['site', 'details', { siteId }],
    queryFn: () => ApiClient.assetManagement.getSiteById(siteId),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const createAssetManagementSiteDetailsLoader =
  (queryClient: QueryClient) =>
  async ({ params }: LoaderFunctionArgs) => {
    const siteId = params.siteId;
    const companyId = params.companyId;

    const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
    if (!isValidId) throw new Error(`Provided site id "${siteId}" is invalid.`);

    const siteData = await queryClient.fetchQuery(siteDetailsQuery(Number.parseInt(siteId)));
    if (siteData.company.id !== Number.parseInt(companyId || '')) {
      throw new Error(`Site with id ${siteId} does not exist in company with id ${companyId}`);
    }

    return siteData;
  };
