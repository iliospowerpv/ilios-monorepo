import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

export const createAssetManagementHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.PROJECT_HUB, link: CANONICAL_ROUTES.PROJECT_HUB }],
    moduleId: 'asset-management'
  });
};

export default createAssetManagementHandle;
