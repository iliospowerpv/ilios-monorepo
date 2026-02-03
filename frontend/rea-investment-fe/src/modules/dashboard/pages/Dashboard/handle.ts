import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createDashboardHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'dashboard',
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.DASHBOARD }]
  });
};

export default createDashboardHandle;
