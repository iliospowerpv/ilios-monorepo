import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createSettingsHandle = () => {
  return RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.SETTINGS }]
  });
};

export default createSettingsHandle;
