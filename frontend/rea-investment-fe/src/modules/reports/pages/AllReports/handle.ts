import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createAllReportsHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'reports',
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.REPORTS }]
  });
};

export default createAllReportsHandle;
