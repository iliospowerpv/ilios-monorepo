import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

export const createAddSiteHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [
      { title: BREADCRUMB_LABELS.SETTINGS, link: CANONICAL_ROUTES.SETTINGS },
      { title: 'Add Project' }
    ]
  });
};

export default createAddSiteHandle;
