import { RouteHandle } from '../../../../handles';

export const createAddMyCompanySiteHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'My Company Settings', link: '/settings/my-company' }, { title: 'Add Site' }]
  });
};

export default createAddMyCompanySiteHandle;
