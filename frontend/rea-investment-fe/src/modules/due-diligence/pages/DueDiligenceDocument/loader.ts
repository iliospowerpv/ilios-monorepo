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

export const documentInfoQuery = (siteId: number, documentId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryKey: ['documents', 'info', { siteId, documentId }],
    queryFn: () => ApiClient.dueDiligence.docInfo(siteId, documentId),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
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
    const documentId = params.documentId;

    const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
    if (!isValidId) throw new Error(`Provided site id "${siteId}" is invalid.`);
    const isValid = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
    if (!isValid) {
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    }

    const isValidDocumentId = !!documentId && Number.isSafeInteger(Number.parseInt(documentId));
    if (!isValidDocumentId) throw new Error(`Provided document id "${documentId}" is invalid.`);

    const [siteData, documentInfo, companyData] = await Promise.all([
      queryClient.fetchQuery(siteCrumbsQuery(Number.parseInt(siteId))),
      queryClient.fetchQuery(documentInfoQuery(Number.parseInt(siteId), Number.parseInt(documentId))),
      queryClient.fetchQuery(companyCrumbsQuery(Number.parseInt(companyId)))
    ]);

    return { siteData, documentInfo, companyData };
  };
