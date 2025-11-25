import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';

export const siteDetailsQuery = (siteId: number, enabled = true) =>
  queryOptions({
    queryKey: ['site', 'details', { siteId }],
    queryFn: () => ApiClient.operationsAndMaintenance.getSiteById(siteId),
    refetchInterval: 15 * 60 * 1000,
    enabled: enabled
  });

export const companyDetailsQuery = (companyId: number, enabled = true) =>
  queryOptions({
    queryKey: ['company', 'crumbs', 'O&M (Production Monitoring)', { companyId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: companyId,
        entity_type: 'company',
        permission_module: 'O&M (Production Monitoring)'
      }),
    enabled: enabled
  });

export const siteCrumbsQuery = (siteId: number, enabled = true) =>
  queryOptions({
    queryKey: ['site', 'crumbs', 'O&M (Production Monitoring)', { siteId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: siteId,
        entity_type: 'site',
        permission_module: 'O&M (Production Monitoring)'
      }),
    enabled: enabled
  });

export const createSiteDetailsLoader =
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
    const data = await queryClient.fetchQuery(companyDetailsQuery(Number.parseInt(companyId)));
    const siteData = await queryClient.fetchQuery(siteDetailsQuery(Number.parseInt(siteId)));

    return { siteData, data };
  };

export const createSiteCrumbsLoader =
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
    const data = await queryClient.fetchQuery(companyDetailsQuery(Number.parseInt(companyId)));
    const siteData = await queryClient.fetchQuery(siteCrumbsQuery(Number.parseInt(siteId)));

    return { siteData, data };
  };
