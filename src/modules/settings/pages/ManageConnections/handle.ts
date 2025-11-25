import { RouteHandle } from '../../../../handles';

export const createManageConnectionsHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Settings', link: '/settings' }, { title: 'Manage Connections' }]
  });
};

export default createManageConnectionsHandle;
