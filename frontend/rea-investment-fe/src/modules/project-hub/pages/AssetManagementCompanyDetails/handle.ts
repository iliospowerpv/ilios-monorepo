import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createAssetManagementCompanyDetailsLoader } from './loader';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

export const createAssetManagementCompanyDetailsHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.id !== 'number') {
      return [];
    }
    const companyDetails = queryClient.getQueryData<
      Awaited<ReturnType<ReturnType<typeof createAssetManagementCompanyDetailsLoader>>>
    >(['company', 'details', { companyId: data.id }]);

    return companyDetails
      ? [{ title: BREADCRUMB_LABELS.PROJECT_HUB, link: CANONICAL_ROUTES.PROJECT_HUB }, { title: companyDetails.name }]
      : [{ title: BREADCRUMB_LABELS.PROJECT_HUB, link: CANONICAL_ROUTES.PROJECT_HUB }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
