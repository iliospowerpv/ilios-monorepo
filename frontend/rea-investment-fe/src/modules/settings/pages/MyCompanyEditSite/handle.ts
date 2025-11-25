import { RouteHandle } from '../../../../handles';

export const createMyCompanyEditSiteHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'My Company Settings', link: '/settings/my-company' }, { title: 'Edit Site' }]
  });
};

export default createMyCompanyEditSiteHandle;
