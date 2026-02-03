import { RouteHandle } from '../../../../handles';
import { createAssetManagementDeviceDetailsLoader } from './loader';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createAssetManagementDeviceDetailsLoader>>>;

export const createAssetManagementDeviceDetailsHandle = () => {
  const crumbsBuilder = (data: any) => {
    const resolvedData: LoaderOutput | undefined = data;

    if (!resolvedData || !resolvedData.deviceDetails || !resolvedData.siteDetails) {
      return [];
    }

    const { deviceDetails, siteDetails } = resolvedData;

    return [
      { title: BREADCRUMB_LABELS.PROJECT_HUB, link: CANONICAL_ROUTES.PROJECT_HUB },
      { title: siteDetails.name, link: CANONICAL_ROUTES.PROJECT_HUB_PROJECT_TAB(siteDetails.id, 'om') },
      { title: deviceDetails.general_info.name }
    ];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
