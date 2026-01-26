import { RouteHandle } from '../../../../handles';

export const createMyCompanyEditSiteHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'My Company Settings', link: '/settings/my-company' }, { title: 'Edit Project' }]
  });
};

export default createMyCompanyEditSiteHandle;
