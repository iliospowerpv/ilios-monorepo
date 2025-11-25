import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api';

export const useCompanies = (params: any) => {
  return useQuery({
    queryKey: ['companies'],
    queryFn: () => ApiClient.assetManagement.companies(params)
  });
};

export const useSites = (params: any) => {
  return useQuery({
    queryKey: ['sites'],
    queryFn: () => ApiClient.assetManagement.sites(params)
  });
};
