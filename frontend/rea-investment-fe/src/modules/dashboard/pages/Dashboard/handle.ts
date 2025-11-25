import { RouteHandle } from '../../../../handles';

export const createDashboardHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'dashboard',
    crumbsBuilder: () => [{ title: 'Dashboard' }]
  });
};

export default createDashboardHandle;
