import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

export const createAddUserHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [
      { title: BREADCRUMB_LABELS.SETTINGS, link: CANONICAL_ROUTES.SETTINGS },
      { title: 'Add User' }
    ]
  });
};

export default createAddUserHandle;
