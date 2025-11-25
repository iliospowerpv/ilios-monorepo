import { RouteHandle } from '../../../../handles';

export const createEditMyCompanyHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'My Company Settings', link: '/settings/my-company' }, { title: 'Edit Company' }]
  });
};

export default createEditMyCompanyHandle;
