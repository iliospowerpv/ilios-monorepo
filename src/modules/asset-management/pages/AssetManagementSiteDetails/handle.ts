import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createAssetManagementSiteDetailsLoader } from './loader';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createAssetManagementSiteDetailsLoader>>>;

export const createAssetManagementSiteDetailsHandle = (queryClient: QueryClient) => {
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
          { title: siteDetails.name }
        ]
      : [{ title: 'Asset Management', link: '/asset-management' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
