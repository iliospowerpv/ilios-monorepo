import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createEditMyCompanyUserHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [
      { title: BREADCRUMB_LABELS.MY_COMPANY_SETTINGS, link: '/settings/my-company' },
      { title: 'Edit User' }
    ]
  });
};

export default createEditMyCompanyUserHandle;
