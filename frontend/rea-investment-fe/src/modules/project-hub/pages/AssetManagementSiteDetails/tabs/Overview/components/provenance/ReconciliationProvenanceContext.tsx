import React from 'react';
import { useQuery } from '@tanstack/react-query';

import { ApiClient } from '../../../../../../../../api';
import type { ReconciliationRow } from '../../../../../../../../api';
import { useAuth } from '../../../../../../../../contexts/auth/auth';
import { buildReconciliationIndex, resolveReconciliationRow } from './reconciliationFieldMap';

/**
 * Phase 3 — LIVE reconciliation provenance for protected Overview fields.
 *
 * A single tab-level provider fetches the site reconciliation report ONCE and
 * exposes a per-field row lookup to the Overview cards through context. This:
 *   - dedupes against the Reconciliation tab's own query (same query key);
 *   - centralizes the Diligence permission gate so we never fire a 403 for
 *     asset-only users; and
 *   - keeps `useAuth()` out of the individual cards. Cards consume only this
 *     context, which has a SAFE DEFAULT, so they never throw when rendered
 *     without the provider (e.g. isolated card unit tests) and degrade to their
 *     existing static provenance labels.
 *
 * It is strictly READ-ONLY: it performs no writes and never mutates project
 * facts, baselines, SAFL, or any backend state.
 */

export interface ReconciliationProvenanceContextValue {
  /** True when the user may view reconciliation (system user OR Diligence:view). */
  canView: boolean;
  isLoading: boolean;
  isError: boolean;
  /** Owning site id when valid, else null (used for read-only deep links). */
  siteId: number | null;
  /** Resolves the reconciliation row backing an Overview field, or undefined. */
  getRow: (field: string) => ReconciliationRow | undefined;
}

const DEFAULT_VALUE: ReconciliationProvenanceContextValue = {
  canView: false,
  isLoading: false,
  isError: false,
  siteId: null,
  getRow: () => undefined
};

const ReconciliationProvenanceContext = React.createContext<ReconciliationProvenanceContextValue>(DEFAULT_VALUE);

/** Mirrors the page-level reconciliation gate used by BaselineNavLinks. */
export const canViewReconciliation = (user: { is_system_user?: boolean; role?: any } | null | undefined): boolean =>
  !!user?.is_system_user || !!user?.role?.permissions?.['Diligence']?.view;

interface OverviewProvenanceProviderProps {
  siteId: number;
  children: React.ReactNode;
}

export const OverviewProvenanceProvider: React.FC<OverviewProvenanceProviderProps> = ({ siteId, children }) => {
  const { user } = useAuth();
  const canView = canViewReconciliation(user);
  const isValidId = Number.isSafeInteger(siteId) && siteId > 0;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['site', 'reconciliation', { siteId }],
    queryFn: () => ApiClient.reconciliation.getSiteReconciliation(siteId),
    enabled: canView && isValidId,
    retry: false
  });

  const index = React.useMemo(() => buildReconciliationIndex(data?.rows), [data]);
  const getRow = React.useCallback((field: string) => resolveReconciliationRow(index, field), [index]);

  const value = React.useMemo<ReconciliationProvenanceContextValue>(
    () => ({
      canView,
      isLoading: canView && isValidId ? isLoading : false,
      isError: canView && isValidId ? isError : false,
      siteId: isValidId ? siteId : null,
      getRow
    }),
    [canView, isLoading, isError, isValidId, siteId, getRow]
  );

  return <ReconciliationProvenanceContext.Provider value={value}>{children}</ReconciliationProvenanceContext.Provider>;
};

/**
 * Reads the Overview reconciliation provenance context. Returns the SAFE DEFAULT
 * (canView=false, getRow→undefined) when no provider is present, so consuming
 * components never throw and gracefully fall back to static provenance labels.
 */
export const useReconciliationProvenance = (): ReconciliationProvenanceContextValue =>
  React.useContext(ReconciliationProvenanceContext);
