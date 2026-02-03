import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createFinanceHomeHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.companyId !== 'number' && typeof data?.companyId !== 'string') {
      return [{ title: BREADCRUMB_LABELS.FINANCE, link: '/finance' }];
    }

    const companyId = typeof data.companyId === 'string' ? parseInt(data.companyId, 10) : data.companyId;
    const companyDetails = queryClient.getQueryData<{ name: string }>(['company', 'details', { companyId }]);

    return companyDetails
      ? [{ title: BREADCRUMB_LABELS.FINANCE, link: '/finance' }, { title: companyDetails.name }]
      : [{ title: BREADCRUMB_LABELS.FINANCE, link: '/finance' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder,
    moduleId: 'finance'
  });
};

export default createFinanceHomeHandle;
