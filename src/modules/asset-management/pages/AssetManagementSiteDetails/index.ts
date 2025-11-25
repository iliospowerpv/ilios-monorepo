import AssetManagementSiteDetails from './AssetManagementSiteDetails';
import { createAssetManagementSiteDetailsLoader } from './loader';
import { createAssetManagementSiteDetailsHandle } from './handle';

export { AssetManagementSiteDetails, createAssetManagementSiteDetailsLoader, createAssetManagementSiteDetailsHandle };

export default {
  Component: AssetManagementSiteDetails,
  createHandle: createAssetManagementSiteDetailsHandle,
  createLoader: createAssetManagementSiteDetailsLoader
};
