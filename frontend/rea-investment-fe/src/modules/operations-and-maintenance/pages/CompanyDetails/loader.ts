import { QueryClient, queryOptions } from '@tanstack/react-query';
import { LoaderFunctionArgs } from 'react-router-dom';
import { ApiClient } from '../../../../api';

export const companyDetailsQuery = (companyId: number, enabled = true) =>
  queryOptions({
    queryKey: ['company', 'operations-and-maintenance-details', { companyId }],
    queryFn: () => ApiClient.operationsAndMaintenance.getCompanyById(companyId),
    enabled: enabled,
    staleTime: 60 * 1000
  });

export const createCompanyDetailsLoader =
  (queryClient: QueryClient) =>
  async ({ params }: LoaderFunctionArgs) => {
    const companyId = params.companyId;
    const isValidId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
    if (!isValidId) {
      throw new Error(`Provided company id "${companyId}" is invalid.`);
    }
    const data = await queryClient.fetchQuery(companyDetailsQuery(Number.parseInt(companyId)));
    return data;
  };
