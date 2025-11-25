import { RouteHandle } from '../../../../handles';

export const createAllReportsHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'reports',
    crumbsBuilder: () => [{ title: 'Reports' }]
  });
};

export default createAllReportsHandle;
