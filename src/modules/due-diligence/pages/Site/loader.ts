import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';

export const siteDiligenceQuery = (siteId: number, enabled = true) =>
  queryOptions({
    queryKey: ['site', 'diligence', { siteId }],
    queryFn: () => ApiClient.dueDiligence.getDocuments(siteId),
    enabled: enabled
  });

export const siteCrumbsQuery = (siteId: number, enabled = true) =>
  queryOptions({
    queryKey: ['site', 'crumbs', 'Diligence', { siteId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: siteId,
        entity_type: 'site',
        permission_module: 'Diligence'
      }),
    enabled: enabled
  });

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

export const createLoader =
  (queryClient: QueryClient) =>
  async ({ params }: LoaderFunctionArgs) => {
    const siteId = params.siteId;
    const companyId = params.companyId;
    const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
    if (!isValidId) throw new Error(`Provided site id "${siteId}" is invalid.`);
    const isValid = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
    if (!isValid) {
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    }
    const data = await queryClient.fetchQuery(companyCrumbsQuery(Number.parseInt(companyId)));
    const siteData = await queryClient.fetchQuery(siteCrumbsQuery(Number.parseInt(siteId)));

    return { siteData, data };
  };
