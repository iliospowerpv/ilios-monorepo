import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createAssetManagementCompanyDetailsLoader } from './loader';

export const createAssetManagementCompanyDetailsHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.id !== 'number') {
      return [];
    }
    const companyDetails = queryClient.getQueryData<
      Awaited<ReturnType<ReturnType<typeof createAssetManagementCompanyDetailsLoader>>>
    >(['company', 'details', { companyId: data.id }]);

    return companyDetails
      ? [{ title: 'Asset Management', link: '/asset-management' }, { title: companyDetails.name }]
      : [{ title: 'Asset Management', link: '/asset-management' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
