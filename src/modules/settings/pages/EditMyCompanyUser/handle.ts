import { RouteHandle } from '../../../../handles';

export const createEditMyCompanyUserHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'My Company Settings', link: '/settings/my-company' }, { title: 'Edit User' }]
  });
};

export default createEditMyCompanyUserHandle;
