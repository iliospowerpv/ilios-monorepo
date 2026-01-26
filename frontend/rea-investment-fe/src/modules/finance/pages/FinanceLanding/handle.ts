import { RouteHandle } from '../../../../handles';

export const createFinanceLandingHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Finance' }],
    moduleId: 'finance'
  });
};

export default createFinanceLandingHandle;
