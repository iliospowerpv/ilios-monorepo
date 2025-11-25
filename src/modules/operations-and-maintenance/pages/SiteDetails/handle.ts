import { RouteHandle } from '../../../../handles';

export const createSiteDetailsHandle = () => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.data?.id !== 'number') {
      return [];
    }

    return data?.data?.id && data?.siteData?.name
      ? [
          { title: 'O&M', link: '/operations-and-maintenance' },
          { title: data?.data?.name, link: `/operations-and-maintenance/companies/${data?.data?.id}` },
          { title: data?.siteData?.name }
        ]
      : [{ title: 'O&M', link: '/operations-and-maintenance' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'operations-and-maintenance'
  });
};
