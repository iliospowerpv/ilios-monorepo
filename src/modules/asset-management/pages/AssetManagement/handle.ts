import { RouteHandle } from '../../../../handles';

export const createAssetManagementHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Asset Management' }],
    moduleId: 'asset-management'
  });
};

export default createAssetManagementHandle;
