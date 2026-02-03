import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

export const createEditCompanyHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [
      { title: BREADCRUMB_LABELS.SETTINGS, link: CANONICAL_ROUTES.SETTINGS },
      { title: 'Edit Company' }
    ]
  });
};

export default createEditCompanyHandle;
