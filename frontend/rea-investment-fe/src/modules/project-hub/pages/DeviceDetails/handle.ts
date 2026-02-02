import { RouteHandle } from '../../../../handles';
import { createAssetManagementDeviceDetailsLoader } from './loader';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createAssetManagementDeviceDetailsLoader>>>;

export const createAssetManagementDeviceDetailsHandle = () => {
  const crumbsBuilder = (data: any) => {
    const resolvedData: LoaderOutput | undefined = data;

    if (!resolvedData || !resolvedData.deviceDetails || !resolvedData.siteDetails) {
      return [];
    }

    const { deviceDetails, siteDetails, companyDetails } = resolvedData;

    return [
      { title: 'Asset Management', link: '/asset-management' },
      { title: companyDetails.name, link: `/asset-management/companies/${companyDetails.id}` },
      { title: siteDetails.name, link: `/asset-management/companies/${companyDetails.id}/sites/${siteDetails.id}` },
      { title: deviceDetails.general_info.name }
    ];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
