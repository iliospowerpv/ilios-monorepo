import { RouteHandle } from '../../../../handles';

export const createAddMyCompanyUserHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'My Company Settings', link: '/settings/my-company' }, { title: 'Add User' }]
  });
};

export default createAddMyCompanyUserHandle;
