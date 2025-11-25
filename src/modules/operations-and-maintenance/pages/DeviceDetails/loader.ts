import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';

export const siteDetailsQuery = (siteId: number, enabled = true) =>
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

export const deviceCrumbsQuery = (deviceId: number, enabled = true) =>
  queryOptions({
    queryKey: ['device', 'crumbs', 'O&M (Production Monitoring)', { deviceId }],
    queryFn: () =>
      ApiClient.breadcrumbs.breadcrumbs({
        entity_id: deviceId,
        entity_type: 'device',
        permission_module: 'O&M (Production Monitoring)'
      }),
    enabled: enabled
  });

export const deviceDetailsQuery = (deviceId: number, enabled = true) =>
  queryOptions({
    queryKey: ['device', 'details', { deviceId }],
    queryFn: () => ApiClient.operationsAndMaintenance.getDeviceById(deviceId),
    enabled: enabled
  });

export const createDeviceDetailsLoader =
  (queryClient: QueryClient) =>
  async ({ params }: LoaderFunctionArgs) => {
    const siteId = params.siteId;
    const companyId = params.companyId;
    const deviceId = params.deviceId;
    const isValiddeviceId = !!deviceId && Number.isSafeInteger(Number.parseInt(deviceId));
    if (!isValiddeviceId) throw new Error(`Provided device id "${deviceId}" is invalid.`);
    const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
    if (!isValidId) throw new Error(`Provided site id "${siteId}" is invalid.`);
    const isValid = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
    if (!isValid) {
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    }

    const device = await queryClient.fetchQuery(deviceCrumbsQuery(Number.parseInt(deviceId)));
    if (device.parent_id !== Number.parseInt(siteId)) throw new Error(`Provided site id "${siteId}" is invalid.`);
    const siteData = await queryClient.fetchQuery(siteDetailsQuery(Number.parseInt(siteId)));
    if (siteData.parent_id !== Number.parseInt(companyId))
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    const data = await queryClient.fetchQuery(companyDetailsQuery(Number.parseInt(companyId)));
    const deviceData = await queryClient.fetchQuery(deviceDetailsQuery(Number.parseInt(deviceId)));

    return { siteData, data, deviceData };
  };
