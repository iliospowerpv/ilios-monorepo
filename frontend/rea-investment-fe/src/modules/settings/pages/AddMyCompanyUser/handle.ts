import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createAddMyCompanyUserHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [
      { title: BREADCRUMB_LABELS.MY_COMPANY_SETTINGS, link: '/settings/my-company' },
      { title: 'Add User' }
    ]
  });
};

export default createAddMyCompanyUserHandle;
