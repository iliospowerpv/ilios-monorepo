import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createMyCompanySettingsHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.MY_COMPANY_SETTINGS }]
  });
};

export default createMyCompanySettingsHandle;
