import { RouteHandle } from '../../../../handles';

export const createEditUserHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Settings', link: '/settings' }, { title: 'Edit User' }]
  });
};

export default createEditUserHandle;
