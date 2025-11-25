import { RouteHandle } from '../../../../handles';

export const createAddUserHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Settings', link: '/settings' }, { title: 'Add User' }]
  });
};

export default createAddUserHandle;
