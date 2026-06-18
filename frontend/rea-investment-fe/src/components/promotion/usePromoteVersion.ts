import { useMutation, useQueryClient } from '@tanstack/react-query';

import { ApiClient } from '../../api';
import type { PromoteVersionPayload, PromoteVersionResponse } from '../../api';

interface UsePromoteVersionOptions {
  onSuccess?: (result: PromoteVersionResponse) => void;
  onError?: (error: unknown) => void;
}

/**
 * Promote mutation shared by the Reconciliation and Data Room launchers. On
 * success it invalidates the assumptions / reconciliation / promotion-history
 * caches common to both surfaces, then defers surface-specific follow-up
 * (notify, close, extra invalidations) to the caller's `onSuccess`.
 */
export const usePromoteVersion = (siteId: number, options?: UsePromoteVersionOptions) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromoteVersionPayload) => ApiClient.assumptions.promoteVersion(siteId, payload),
    onSuccess: result => {
      queryClient.invalidateQueries({ queryKey: ['site', 'reconciliation', { siteId }] });
      queryClient.invalidateQueries({ queryKey: ['site', 'assumptions', 'facts', { siteId }] });
      queryClient.invalidateQueries({ queryKey: ['site', 'assumptions', 'promotions', { siteId }] });
      options?.onSuccess?.(result);
    },
    onError: error => {
      options?.onError?.(error);
    }
  });
};
