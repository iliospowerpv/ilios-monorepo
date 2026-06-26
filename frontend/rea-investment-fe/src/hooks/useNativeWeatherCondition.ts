import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';

import { ApiClient } from '../api';
import type { ObservedCondition, PerformanceContextQuery, PerformanceContextResponse } from '../types/telemetryV2';

export const nativeWeatherConditionKeys = {
  all: ['nativeWeatherCondition'] as const,
  site: (siteId: number, query: PerformanceContextQuery) => [...nativeWeatherConditionKeys.all, siteId, query] as const
};

// The cosmetic indicator only needs the most-recent reading; a rolling 24h
// window always captures it (a 'today' window would be empty just after local
// midnight). Bucketed hourly to keep the envelope small.
const DEFAULT_QUERY: PerformanceContextQuery = { window: '24h', bucket: '1h' };
const STALE = 15 * 60 * 1000;

/**
 * Read a single site's native observed-weather condition from the read-only V2
 * performance-context envelope. Dual-run with the (untouched) Weatherstack
 * pipeline: this surfaces ONLY the native `observed_condition` for the cosmetic
 * indicator and never triggers a provider/credential call or any write. Returns
 * `null` when unavailable — never a fabricated or zero condition.
 */
export const useNativeWeatherCondition = (
  siteId: number,
  query: PerformanceContextQuery = DEFAULT_QUERY,
  options?: Omit<
    UseQueryOptions<PerformanceContextResponse, Error, ObservedCondition | null>,
    'queryKey' | 'queryFn' | 'select'
  >
) =>
  useQuery({
    queryKey: nativeWeatherConditionKeys.site(siteId, query),
    queryFn: () => ApiClient.telemetryV2.getSitePerformanceContext(siteId, query),
    select: (data: PerformanceContextResponse) => data.observed_condition ?? null,
    enabled: Number.isFinite(siteId) && siteId > 0,
    staleTime: STALE,
    ...options
  });
