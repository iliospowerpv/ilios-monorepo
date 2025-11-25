import { RouteHandle } from '../../../../handles';

export const createMyCompanySettingsHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'My Company Settings' }]
  });
};

export default createMyCompanySettingsHandle;
