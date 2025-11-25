import { RouteHandle } from '../../../../handles';

export const createAddCompanyHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Settings', link: '/settings' }, { title: 'Add Company' }]
  });
};

export default createAddCompanyHandle;
