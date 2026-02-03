import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createFinanceLandingHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.FINANCE }],
    moduleId: 'finance'
  });
};

export default createFinanceLandingHandle;
