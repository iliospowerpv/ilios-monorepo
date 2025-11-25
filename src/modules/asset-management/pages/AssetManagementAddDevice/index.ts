import AssetManagementAddDevice from './AssetManagementAddDevice';
import { createAssetManagementAddDeviceHandle } from './handle';
import { createAssetManagementAddDeviceLoader } from './loader';

export { AssetManagementAddDevice, createAssetManagementAddDeviceHandle };

export default {
  Component: AssetManagementAddDevice,
  createHandle: createAssetManagementAddDeviceHandle,
  createLoader: createAssetManagementAddDeviceLoader
};
