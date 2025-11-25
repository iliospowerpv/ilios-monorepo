import { RouteHandle } from '../../../../handles';

export const createAllCompaniesHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'operations-and-maintenance',
    crumbsBuilder: () => [{ title: 'O&M' }]
  });
};

export default createAllCompaniesHandle;
