import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';

export const createSiteFinanceHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.companyId === 'undefined' || typeof data?.siteId === 'undefined') {
      return [{ title: 'Finance', link: '/finance' }];
    }

    const companyId = typeof data.companyId === 'string' ? parseInt(data.companyId, 10) : data.companyId;
    const siteId = typeof data.siteId === 'string' ? parseInt(data.siteId, 10) : data.siteId;

    const companyDetails = queryClient.getQueryData<{ name: string }>(['company', 'details', { companyId }]);
    const siteDetails = queryClient.getQueryData<{ name: string }>(['site', 'details', { siteId }]);

    if (companyDetails && siteDetails) {
      return [
        { title: 'Finance', link: '/finance' },
        { title: companyDetails.name, link: `/finance/companies/${companyId}` },
        { title: siteDetails.name }
      ];
    }

    if (companyDetails) {
      return [
        { title: 'Finance', link: '/finance' },
        { title: companyDetails.name, link: `/finance/companies/${companyId}` },
        { title: '...' }
      ];
    }

    return [{ title: 'Finance', link: '/finance' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder,
    moduleId: 'finance'
  });
};

export default createSiteFinanceHandle;
