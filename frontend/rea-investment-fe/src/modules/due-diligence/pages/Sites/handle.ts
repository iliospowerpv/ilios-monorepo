import { RouteHandle } from '../../../../handles';
import { createDiligenceCompanyDetailsLoader } from './loader';
import { QueryClient } from '@tanstack/react-query';

export const createDueDiligenceHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.id !== 'number') {
      return [];
    }
    const companyDetails = queryClient.getQueryData<
      Awaited<ReturnType<ReturnType<typeof createDiligenceCompanyDetailsLoader>>>
    >(['company', 'crumbs', 'Diligence', { companyId: data.id }]);

    return companyDetails
      ? [{ title: 'Diligence', link: '/due-diligence' }, { title: companyDetails.name }]
      : [{ title: 'Diligence', link: '/due-diligence' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    moduleId: 'due-diligence',
    crumbsBuilder: crumbsBuilder
  });
};

export default createDueDiligenceHandle;
