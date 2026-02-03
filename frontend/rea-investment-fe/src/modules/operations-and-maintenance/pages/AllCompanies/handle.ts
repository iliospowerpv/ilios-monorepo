import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createAllCompaniesHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'operations-and-maintenance',
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.OM }]
  });
};

export default createAllCompaniesHandle;
