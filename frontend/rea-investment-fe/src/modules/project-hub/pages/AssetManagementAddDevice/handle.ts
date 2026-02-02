import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createAssetManagementSiteDetailsLoader } from '../AssetManagementSiteDetails';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createAssetManagementSiteDetailsLoader>>>;

export const createAssetManagementAddDeviceHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.id !== 'number') {
      return [];
    }

    const siteDetails = queryClient.getQueryData<LoaderOutput>(['site', 'details', { siteId: data.id }]);
    const companyInfo = siteDetails?.company;

    return siteDetails && companyInfo
      ? [
          { title: 'Asset Management', link: '/asset-management' },
          { title: companyInfo.name, link: `/asset-management/companies/${companyInfo.id}` },
          { title: siteDetails.name, link: `/asset-management/companies/${companyInfo.id}/sites/${siteDetails.id}` },
          { title: 'Add Device' }
        ]
      : [{ title: 'Asset Management', link: '/asset-management' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
