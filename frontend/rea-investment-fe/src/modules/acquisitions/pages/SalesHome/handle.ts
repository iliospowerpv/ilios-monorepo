import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createSalesHomeHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.companyId !== 'number' && typeof data?.companyId !== 'string') {
      return [{ title: BREADCRUMB_LABELS.ACQUISITIONS, link: '/acquisitions' }];
    }

    const companyId = typeof data.companyId === 'string' ? parseInt(data.companyId, 10) : data.companyId;
    const companyDetails = queryClient.getQueryData<{ name: string }>(['company', 'details', { companyId }]);

    return companyDetails
      ? [{ title: BREADCRUMB_LABELS.ACQUISITIONS, link: '/acquisitions' }, { title: companyDetails.name }]
      : [{ title: BREADCRUMB_LABELS.ACQUISITIONS, link: '/acquisitions' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder,
    moduleId: 'sales'
  });
};

export default createSalesHomeHandle;
