import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

export const createAddCompanyHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [
      { title: BREADCRUMB_LABELS.SETTINGS, link: CANONICAL_ROUTES.SETTINGS },
      { title: 'Add Company' }
    ]
  });
};

export default createAddCompanyHandle;
