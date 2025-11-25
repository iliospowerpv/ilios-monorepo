import { RouteHandle } from '../../../../handles';

export const createSettingsHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Settings' }]
  });
};

export default createSettingsHandle;
