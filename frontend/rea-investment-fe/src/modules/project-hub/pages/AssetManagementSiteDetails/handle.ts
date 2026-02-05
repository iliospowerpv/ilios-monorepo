import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createAssetManagementSiteDetailsLoader } from './loader';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createAssetManagementSiteDetailsLoader>>>;

export const createAssetManagementSiteDetailsHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.id !== 'number') {
      return [];
    }
    const siteDetails = queryClient.getQueryData<LoaderOutput>(['site', 'details', { siteId: data.id }]);

    return siteDetails
      ? [{ title: BREADCRUMB_LABELS.PROJECT_HUB, link: CANONICAL_ROUTES.PROJECT_HUB }, { title: siteDetails.name }]
      : [{ title: BREADCRUMB_LABELS.PROJECT_HUB, link: CANONICAL_ROUTES.PROJECT_HUB }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
