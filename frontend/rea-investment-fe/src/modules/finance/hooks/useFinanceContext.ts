import { useQuery } from '@tanstack/react-query';
import { httpClient } from '../../../api/http-client';

interface SiteDetails {
  id: number;
  company_id: number;
  name?: string;
}

interface FinanceContext {
  companyId: number | null;
  siteId: number;
  isLoading: boolean;
  error: Error | null;
}

export const useFinanceContext = (siteId: number | string | undefined): FinanceContext => {
  const numericSiteId = typeof siteId === 'string' ? parseInt(siteId, 10) : siteId;

  const { data, isLoading, error } = useQuery({
    queryKey: ['site-details', numericSiteId],
    queryFn: async () => {
      const response = await httpClient.get<SiteDetails>(`/api/sites/${numericSiteId}`);
      return response.data;
    },
    enabled: !!numericSiteId && !isNaN(numericSiteId),
    staleTime: 5 * 60 * 1000
  });

  return {
    companyId: data?.company_id ?? null,
    siteId: numericSiteId || 0,
    isLoading,
    error: error as Error | null
  };
};

export default useFinanceContext;
