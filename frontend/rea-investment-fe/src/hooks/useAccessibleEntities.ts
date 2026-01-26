import { useQuery } from '@tanstack/react-query';
import { useMemo, useCallback } from 'react';
import { ApiClient, AccessibleCompany, AccessibleProject, AccessibleEntitiesResponse } from '../api';

const ACCESSIBLE_ENTITIES_QUERY_KEY = ['accessible-entities'];

export const useAccessibleEntities = () => {
  const query = useQuery<AccessibleEntitiesResponse>({
    queryKey: ACCESSIBLE_ENTITIES_QUERY_KEY,
    queryFn: () => ApiClient.accessibleEntities.getAccessibleEntities(),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false
  });

  const getProjectsByCompanyId = useCallback(
    (companyId: number | null): AccessibleProject[] => {
      if (!query.data?.projects) return [];
      if (companyId === null) return query.data.projects;
      return query.data.projects.filter(p => p.company_id === companyId);
    },
    [query.data?.projects]
  );

  const getCompanyById = useCallback(
    (companyId: number): AccessibleCompany | undefined => {
      return query.data?.companies.find(c => c.id === companyId);
    },
    [query.data?.companies]
  );

  const getProjectById = useCallback(
    (projectId: number): AccessibleProject | undefined => {
      return query.data?.projects.find(p => p.id === projectId);
    },
    [query.data?.projects]
  );

  return useMemo(
    () => ({
      companies: query.data?.companies ?? [],
      projects: query.data?.projects ?? [],
      isLoading: query.isLoading,
      isError: query.isError,
      error: query.error,
      refetch: query.refetch,
      getProjectsByCompanyId,
      getCompanyById,
      getProjectById
    }),
    [query, getProjectsByCompanyId, getCompanyById, getProjectById]
  );
};

export type { AccessibleCompany, AccessibleProject, AccessibleEntitiesResponse };
