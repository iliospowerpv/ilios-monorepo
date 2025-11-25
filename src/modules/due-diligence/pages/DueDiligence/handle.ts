import { RouteHandle } from '../../../../handles';

export const createDueDiligenceHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'due-diligence',
    crumbsBuilder: () => [{ title: 'Diligence' }]
  });
};

export default createDueDiligenceHandle;
