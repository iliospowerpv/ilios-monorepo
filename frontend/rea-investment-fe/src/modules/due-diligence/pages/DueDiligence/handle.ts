import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createDueDiligenceHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'due-diligence',
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.DATA_ROOM }]
  });
};

export default createDueDiligenceHandle;
