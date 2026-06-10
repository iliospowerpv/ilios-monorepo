import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseMutationOptions, UseQueryOptions } from '@tanstack/react-query';

import { ApiClient } from '../api';
import type {
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
  SyncDevicesResponse,
  SyncSitesResponse,
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
    [...telemetryV2Keys.all, 'externalDevices', accountId, externalSiteId] as const
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

export type { UseMutationOptions };
