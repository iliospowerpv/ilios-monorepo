import { RouteHandle } from '../../../../handles/handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createHomeHandle = () =>
  RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.HOME }]
  });
