import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';

export const deviceDetailsQuery = (siteId: number, deviceId: number, enabled = true, throwOnError = false) =>
  queryOptions({
    queryKey: ['device', 'details', { siteId, deviceId }],
    queryFn: () => ApiClient.assetManagement.deviceById(siteId, deviceId),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const siteDetailsQuery = (siteId: number, enabled = true) =>
  queryOptions({
    queryKey: ['site', 'crumbs', 'Asset Management', { siteId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: siteId,
        entity_type: 'site',
        permission_module: 'Asset Management'
      }),
    enabled: enabled
  });

export const companyDetailsQuery = (companyId: number, enabled = true) =>
  queryOptions({
    queryKey: ['company', 'crumbs', 'Asset Management', { companyId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: companyId,
        entity_type: 'company',
        permission_module: 'Asset Management'
      }),
    enabled: enabled
  });

export const createAssetManagementDeviceDetailsLoader =
  (queryClient: QueryClient) =>
  async ({ params }: LoaderFunctionArgs) => {
    const siteId = params.siteId;
    const companyId = params.companyId;
    const deviceId = params.deviceId;

    if (!siteId || !Number.isSafeInteger(Number.parseInt(siteId))) {
      throw new Error(`Provided site id "${siteId}" is invalid.`);
    }

    if (!companyId || !Number.isSafeInteger(Number.parseInt(companyId))) {
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    }

    if (!deviceId || !Number.isSafeInteger(Number.parseInt(deviceId))) {
      throw new Error(`Provided device id "${deviceId}" is invalid.`);
    }

    const deviceDetailsPromise = queryClient.fetchQuery(
      deviceDetailsQuery(Number.parseInt(siteId), Number.parseInt(deviceId))
    );
    const siteDetailsPromise = queryClient.fetchQuery(siteDetailsQuery(Number.parseInt(siteId)));
    const companyDetailsPromise = queryClient.fetchQuery(companyDetailsQuery(Number.parseInt(companyId)));

    const [deviceDetails, siteDetails, companyDetails] = await Promise.all([
      deviceDetailsPromise,
      siteDetailsPromise,
      companyDetailsPromise
    ]);

    if (siteDetails.parent_id !== Number.parseInt(companyId))
      throw new Error(`Provided company id "${companyId}" is invalid.`);

    return { siteDetails, deviceDetails, deviceId: Number.parseInt(deviceId), companyDetails };
  };
