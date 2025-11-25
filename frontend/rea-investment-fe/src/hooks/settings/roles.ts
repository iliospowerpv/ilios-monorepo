import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api';
export const useRolesSettings = () => {
  return useQuery({
    queryKey: ['roles'],
    queryFn: ApiClient.user.roles
  });
};
