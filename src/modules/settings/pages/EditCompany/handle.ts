import { RouteHandle } from '../../../../handles';

export const createEditCompanyHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Settings', link: '/settings' }, { title: 'Edit Company' }]
  });
};

export default createEditCompanyHandle;
