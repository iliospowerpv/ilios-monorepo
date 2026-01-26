import { RouteHandle } from '../../../../handles';

export const createAddSiteHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Settings', link: '/settings' }, { title: 'Add Project' }]
  });
};

export default createAddSiteHandle;
