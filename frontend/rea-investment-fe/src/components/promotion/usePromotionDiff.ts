import { useQuery } from '@tanstack/react-query';

import { ApiClient } from '../../api';

/**
 * Read-only live diff for a file version's pending promotion. Never cached
 * (staleTime/gcTime 0) so the dialog always reflects the current blast radius —
 * this is the authoritative payload and must be re-fetched at confirm time.
 */
export const usePromotionDiff = (siteId: number, fileId: number, enabled: boolean) =>
  useQuery({
    queryKey: ['site', 'assumptions', 'promotion-diff', { siteId, fileId }],
    queryFn: () => ApiClient.assumptions.getPromotionDiff(siteId, fileId),
    enabled: enabled && Number.isInteger(fileId),
    staleTime: 0,
    gcTime: 0,
    retry: false as const,
    refetchOnWindowFocus: false
  });
