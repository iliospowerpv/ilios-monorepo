import { RouteHandle } from '../../../../handles';

export const createEditSiteHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Settings', link: '/settings' }, { title: 'Edit Project' }]
  });
};

export default createEditSiteHandle;
