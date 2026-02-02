import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';

export const createSalesHomeHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.companyId !== 'number' && typeof data?.companyId !== 'string') {
      return [{ title: 'Sales Pipeline', link: '/sales' }];
    }

    const companyId = typeof data.companyId === 'string' ? parseInt(data.companyId, 10) : data.companyId;
    const companyDetails = queryClient.getQueryData<{ name: string }>(['company', 'details', { companyId }]);

    return companyDetails
      ? [{ title: 'Sales Pipeline', link: '/sales' }, { title: companyDetails.name }]
      : [{ title: 'Sales Pipeline', link: '/sales' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder,
    moduleId: 'sales'
  });
};

export default createSalesHomeHandle;
