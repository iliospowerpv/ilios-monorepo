import DeviceDetails from './DeviceDetails';
import { createAssetManagementDeviceDetailsLoader } from './loader';
import { createAssetManagementDeviceDetailsHandle } from './handle';

export { DeviceDetails, createAssetManagementDeviceDetailsLoader, createAssetManagementDeviceDetailsHandle };

export default {
  Component: DeviceDetails,
  createHandle: createAssetManagementDeviceDetailsHandle,
  createLoader: createAssetManagementDeviceDetailsLoader
};
