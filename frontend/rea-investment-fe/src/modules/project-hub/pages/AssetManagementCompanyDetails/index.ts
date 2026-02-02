import AssetManagementCompanyDetails from './AssetManagementCompanyDetails';
import { createAssetManagementCompanyDetailsLoader } from './loader';
import { createAssetManagementCompanyDetailsHandle } from './handle';

export {
  AssetManagementCompanyDetails,
  createAssetManagementCompanyDetailsLoader,
  createAssetManagementCompanyDetailsHandle
};

export default {
  Component: AssetManagementCompanyDetails,
  createHandle: createAssetManagementCompanyDetailsHandle,
  createLoader: createAssetManagementCompanyDetailsLoader
};
