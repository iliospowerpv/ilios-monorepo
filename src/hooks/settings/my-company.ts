import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api';
export const useMyCompanySettings = () => {
  return useQuery({
    queryKey: ['my-company'],
    queryFn: ApiClient.myCompany.getMyCompany
  });
};
