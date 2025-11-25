import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createCompanyDetailsLoader } from './loader';

export const createCompanyDetailsHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.id !== 'number') {
      return [];
    }
    const companyDetails = queryClient.getQueryData<Awaited<ReturnType<ReturnType<typeof createCompanyDetailsLoader>>>>(
      ['company', 'operations-and-maintenance-details', { companyId: data.id }]
    );

    return companyDetails
      ? [{ title: 'O&M', link: '/operations-and-maintenance' }, { title: companyDetails.name }]
      : [{ title: 'O&M', link: '/operations-and-maintenance' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'operations-and-maintenance'
  });
};
