import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

export const createSiteDetailsHandle = () => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.data?.id !== 'number') {
      return [];
    }

    return data?.data?.id && data?.siteData?.name
      ? [
          { title: BREADCRUMB_LABELS.OM, link: '/operations-and-maintenance' },
          { title: data?.data?.name, link: `/operations-and-maintenance/companies/${data?.data?.id}` },
          { title: data?.siteData?.name, link: CANONICAL_ROUTES.PROJECT_HUB_PROJECT_TAB(data?.siteData?.id, 'om') }
        ]
      : [{ title: BREADCRUMB_LABELS.OM, link: '/operations-and-maintenance' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'operations-and-maintenance'
  });
};
