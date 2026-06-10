import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseMutationOptions, UseQueryOptions } from '@tanstack/react-query';

import { ApiClient } from '../api';
import type {
  BackfillReadingsPayload,
  BackfillReadingsResponse,
  DeviceMappingBulkPayload,
  DeviceMappingBulkResponse,
  ExternalDeviceListResponse,
  ExternalSiteListResponse,
  LicenseCreatePayload,
  LicensedProvider,
  LicensedProviderList,
  ProviderAccount,
  ProviderAccountCreatePayload,
  ProviderAccountList,
  ProviderAccountUpdatePayload,
  ProviderCatalogList,
  RefreshReadingsPayload,
  RefreshReadingsResponse,
  SchedulerState,
  SchedulerUpdatePayload,
  SyncDevicesResponse,
  SyncSitesResponse,
  TelemetryLatestResponse,
  TestAccountResponse
} from '../types/telemetryV2';

export const telemetryV2Keys = {
  all: ['telemetryV2'] as const,
  catalog: () => [...telemetryV2Keys.all, 'catalog'] as const,
  licensedProviders: (companyId: number) => [...telemetryV2Keys.all, 'licensedProviders', companyId] as const,
  providerAccounts: (companyId: number, includeArchived: boolean) =>
    [...telemetryV2Keys.all, 'providerAccounts', companyId, { includeArchived }] as const,
  providerAccount: (companyId: number, accountId: number) =>
    [...telemetryV2Keys.all, 'providerAccount', companyId, accountId] as const,
  externalSites: (accountId: number) => [...telemetryV2Keys.all, 'externalSites', accountId] as const,
  externalDevices: (accountId: number, externalSiteId: string) =>
    [...telemetryV2Keys.all, 'externalDevices', accountId, externalSiteId] as const,
  siteLatest: (siteId: number) => [...telemetryV2Keys.all, 'siteLatest', siteId] as const,
  siteScheduler: (siteId: number) => [...telemetryV2Keys.all, 'siteScheduler', siteId] as const
};

const STALE_LIST = 30 * 1000;
const STALE_CATALOG = 60 * 1000;

export const useProviderCatalog = (options?: Omit<UseQueryOptions<ProviderCatalogList>, 'queryKey' | 'queryFn'>) =>
  useQuery({
    queryKey: telemetryV2Keys.catalog(),
    queryFn: () => ApiClient.telemetryV2.getCatalog(),
    staleTime: STALE_CATALOG,
    ...options
  });

export const useLicensedProviders = (
  companyId: number,
  options?: Omit<UseQueryOptions<LicensedProviderList>, 'queryKey' | 'queryFn'>
) =>
  useQuery({
    queryKey: telemetryV2Keys.licensedProviders(companyId),
    queryFn: () => ApiClient.telemetryV2.listLicensedProviders(companyId),
    enabled: Number.isFinite(companyId) && companyId > 0,
    staleTime: STALE_LIST,
    ...options
  });

export const useProviderAccounts = (
  companyId: number,
  options: { includeArchived?: boolean } = {},
  queryOptions?: Omit<UseQueryOptions<ProviderAccountList>, 'queryKey' | 'queryFn'>
) => {
  const includeArchived = options.includeArchived ?? false;
  return useQuery({
    queryKey: telemetryV2Keys.providerAccounts(companyId, includeArchived),
    queryFn: () => ApiClient.telemetryV2.listProviderAccounts(companyId, { includeArchived }),
    enabled: Number.isFinite(companyId) && companyId > 0,
    staleTime: STALE_LIST,
    ...queryOptions
  });
};

export const useProviderAccountDetail = (
  companyId: number,
  accountId: number | null,
  options?: Omit<UseQueryOptions<ProviderAccount>, 'queryKey' | 'queryFn'>
) =>
  useQuery({
    queryKey: telemetryV2Keys.providerAccount(companyId, accountId ?? -1),
    queryFn: () => ApiClient.telemetryV2.getProviderAccount(companyId, accountId as number),
    enabled: Number.isFinite(companyId) && companyId > 0 && !!accountId && accountId > 0,
    staleTime: STALE_LIST,
    ...options
  });

export const useExternalSites = (
  accountId: number | null,
  options?: Omit<UseQueryOptions<ExternalSiteListResponse>, 'queryKey' | 'queryFn'>
) =>
  useQuery({
    queryKey: telemetryV2Keys.externalSites(accountId ?? -1),
    queryFn: () => ApiClient.telemetryV2.listExternalSites(accountId as number),
    enabled: !!accountId && accountId > 0,
    staleTime: STALE_LIST,
    ...options
  });

/**
 * Cache-only read of the synced device list for one external site. Opening the
 * Device Mapping step calls this; it never triggers a live provider call, so it
 * succeeds even when the provider is unreachable as long as a sync ran before.
 */
export const useExternalDevices = (
  accountId: number | null,
  externalSiteId: string | null,
  options?: Omit<UseQueryOptions<ExternalDeviceListResponse>, 'queryKey' | 'queryFn'>
) =>
  useQuery({
    queryKey: telemetryV2Keys.externalDevices(accountId ?? -1, externalSiteId ?? ''),
    queryFn: () => ApiClient.telemetryV2.listExternalDevices(accountId as number, externalSiteId as string),
    enabled: !!accountId && accountId > 0 && !!externalSiteId,
    staleTime: STALE_LIST,
    ...options
  });

/**
 * Read the V2 freshness snapshot for a site (newest reading/rollup time + latest
 * value per metric). Read-only and safe for any site: non-V2 sites return an
 * all-null payload, so the caller can simply hide the "data as of" caption. Used
 * by the O&M Overview charts to show when the rendered telemetry was last
 * ingested.
 */
export const useSiteLatestTelemetry = (
  siteId: number,
  options?: Omit<UseQueryOptions<TelemetryLatestResponse>, 'queryKey' | 'queryFn'>
) =>
  useQuery({
    queryKey: telemetryV2Keys.siteLatest(siteId),
    queryFn: () => ApiClient.telemetryV2.getSiteLatestTelemetry(siteId),
    enabled: Number.isFinite(siteId) && siteId > 0,
    staleTime: STALE_LIST,
    ...options
  });

/**
 * Centralized mutation hooks. All cache invalidations are wired here so the
 * UI never has to remember which keys to refresh after a write.
 *
 * Credential payloads passed to create/update mutations are forwarded to the
 * API and never stored in any React Query cache; the response objects from
 * those mutations contain only metadata (status, fingerprint, timestamps).
 */
export const useTelemetryAdminMutations = (companyId: number) => {
  const queryClient = useQueryClient();

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: telemetryV2Keys.all });
  };

  const invalidateAccounts = () => {
    queryClient.invalidateQueries({
      queryKey: [...telemetryV2Keys.all, 'providerAccounts', companyId]
    });
  };

  const invalidateAccount = (accountId: number) => {
    queryClient.invalidateQueries({
      queryKey: telemetryV2Keys.providerAccount(companyId, accountId)
    });
  };

  const invalidateLicenses = () => {
    queryClient.invalidateQueries({
      queryKey: telemetryV2Keys.licensedProviders(companyId)
    });
  };

  const grantLicense = useMutation<LicensedProvider, Error, LicenseCreatePayload>({
    mutationFn: payload => ApiClient.telemetryV2.grantLicense(companyId, payload),
    onSuccess: () => {
      invalidateLicenses();
    }
  });

  const revokeLicense = useMutation<void, Error, number>({
    mutationFn: licenseId => ApiClient.telemetryV2.revokeLicense(companyId, licenseId),
    onSuccess: () => {
      invalidateLicenses();
      invalidateAccounts();
    }
  });

  const createAccount = useMutation<ProviderAccount, Error, ProviderAccountCreatePayload>({
    mutationFn: payload => ApiClient.telemetryV2.createProviderAccount(companyId, payload),
    onSuccess: () => {
      invalidateAccounts();
      invalidateLicenses();
    }
  });

  const updateAccount = useMutation<
    ProviderAccount,
    Error,
    { accountId: number; payload: ProviderAccountUpdatePayload }
  >({
    mutationFn: ({ accountId, payload }) => ApiClient.telemetryV2.updateProviderAccount(companyId, accountId, payload),
    onSuccess: (_data, { accountId }) => {
      invalidateAccounts();
      invalidateAccount(accountId);
    }
  });

  const archiveAccount = useMutation<void, Error, number>({
    mutationFn: accountId => ApiClient.telemetryV2.archiveProviderAccount(companyId, accountId),
    onSuccess: (_data, accountId) => {
      invalidateAccounts();
      invalidateAccount(accountId);
    }
  });

  const testAccount = useMutation<TestAccountResponse, Error, number>({
    mutationFn: accountId => ApiClient.telemetryV2.testProviderAccount(accountId),
    onSuccess: (_data, accountId) => {
      invalidateAccount(accountId);
      invalidateAccounts();
    }
  });

  const syncSites = useMutation<SyncSitesResponse, Error, number>({
    mutationFn: accountId => ApiClient.telemetryV2.syncProviderAccountSites(accountId),
    onSuccess: (_data, accountId) => {
      queryClient.invalidateQueries({ queryKey: telemetryV2Keys.externalSites(accountId) });
      invalidateAccount(accountId);
      invalidateAccounts();
    }
  });

  const syncDevices = useMutation<SyncDevicesResponse, Error, { accountId: number; externalSiteId: string }>({
    mutationFn: ({ accountId, externalSiteId }) =>
      ApiClient.telemetryV2.syncProviderAccountDevices(accountId, externalSiteId),
    onSuccess: (_data, { accountId, externalSiteId }) => {
      queryClient.invalidateQueries({
        queryKey: telemetryV2Keys.externalDevices(accountId, externalSiteId)
      });
    }
  });

  const saveDeviceMappings = useMutation<
    DeviceMappingBulkResponse,
    Error,
    { siteId: number; payload: DeviceMappingBulkPayload }
  >({
    mutationFn: ({ siteId, payload }) => ApiClient.telemetryV2.saveDeviceMappings(siteId, payload)
  });

  return {
    grantLicense,
    revokeLicense,
    createAccount,
    updateAccount,
    archiveAccount,
    testAccount,
    syncSites,
    syncDevices,
    saveDeviceMappings,
    invalidateAll
  };
};

export type UseTelemetryAdminMutationsReturn = ReturnType<typeof useTelemetryAdminMutations>;

/**
 * Trigger a manual native telemetry refresh for one project/site. On success it
 * invalidates the site's readiness + health panels (legacy `telemetry-readiness`
 * / `telemetry-health` query keys) so the UI reflects newly ingested data right
 * away. A caller-supplied `onSuccess`/`onError` still runs after the built-in
 * invalidation.
 */
export const useRefreshSiteReadings = (
  siteId: number,
  options?: Omit<UseMutationOptions<RefreshReadingsResponse, Error, RefreshReadingsPayload | void>, 'mutationFn'>
) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...rest } = options ?? {};

  return useMutation<RefreshReadingsResponse, Error, RefreshReadingsPayload | void>({
    mutationFn: payload => ApiClient.telemetryV2.refreshSiteReadings(siteId, payload || {}),
    ...rest,
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({ queryKey: ['telemetry-readiness', siteId] });
      queryClient.invalidateQueries({ queryKey: ['telemetry-health', siteId] });
      onSuccess?.(data, variables, context);
    }
  });
};

/**
 * Read one mapped site's native telemetry scheduler state. The underlying
 * endpoint is admin-gated, so callers MUST pass `enabled: isAdmin` for
 * non-admin users to avoid generating 403 noise. Pass a `refetchInterval` while
 * a run is active to observe the per-site lock clearing.
 */
export const useSiteScheduler = (
  siteId: number,
  options?: Omit<UseQueryOptions<SchedulerState>, 'queryKey' | 'queryFn'>
) =>
  useQuery({
    queryKey: telemetryV2Keys.siteScheduler(siteId),
    queryFn: () => ApiClient.telemetryV2.getSiteScheduler(siteId),
    enabled: Number.isFinite(siteId) && siteId > 0,
    staleTime: STALE_LIST,
    ...options
  });

/**
 * Enable/disable or change cadence for a site's scheduler. Writes config only —
 * it never claims the per-site lease lock, so it is safe even while a run is in
 * progress. On success the freshly returned state is written straight into the
 * scheduler cache so the control reflects the change immediately.
 */
export const useUpdateSiteScheduler = (
  siteId: number,
  options?: Omit<UseMutationOptions<SchedulerState, Error, SchedulerUpdatePayload>, 'mutationFn'>
) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...rest } = options ?? {};

  return useMutation<SchedulerState, Error, SchedulerUpdatePayload>({
    mutationFn: payload => ApiClient.telemetryV2.updateSiteScheduler(siteId, payload),
    ...rest,
    onSuccess: (data, variables, context) => {
      queryClient.setQueryData(telemetryV2Keys.siteScheduler(siteId), data);
      onSuccess?.(data, variables, context);
    }
  });
};

/**
 * Run a bounded historical backfill for one mapped site. Regardless of outcome
 * (success / partial / failure / 409 lock-held) it refreshes the scheduler row
 * (lock + last-run), the O&M readiness/health panels, and the latest-telemetry
 * snapshot so the UI reflects newly written data and the released lock. The
 * endpoint never wipes existing data and never advances the scheduled cursor.
 */
export const useBackfillSiteReadings = (
  siteId: number,
  options?: Omit<UseMutationOptions<BackfillReadingsResponse, Error, BackfillReadingsPayload>, 'mutationFn'>
) => {
  const queryClient = useQueryClient();
  const { onSettled, ...rest } = options ?? {};

  return useMutation<BackfillReadingsResponse, Error, BackfillReadingsPayload>({
    mutationFn: payload => ApiClient.telemetryV2.backfillSiteReadings(siteId, payload),
    ...rest,
    onSettled: (data, error, variables, context) => {
      queryClient.invalidateQueries({ queryKey: telemetryV2Keys.siteScheduler(siteId) });
      queryClient.invalidateQueries({ queryKey: ['telemetry-readiness', siteId] });
      queryClient.invalidateQueries({ queryKey: ['telemetry-health', siteId] });
      queryClient.invalidateQueries({ queryKey: telemetryV2Keys.siteLatest(siteId) });
      onSettled?.(data, error, variables, context);
    }
  });
};

export type { UseMutationOptions };
