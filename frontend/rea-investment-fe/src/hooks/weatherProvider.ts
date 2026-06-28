import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';

import { ApiClient } from '../api';
import type {
  ExternalWeatherContextResponse,
  ProviderImportPreviewResponse,
  ProviderImportRequest,
  ProviderImportResponse,
  WeatherProviderAccountCreate,
  WeatherProviderAccountList,
  WeatherProviderAccountResponse,
  WeatherProviderAccountUpdate,
  WeatherProviderList,
  WeatherProviderTestResponse
} from '../types/weather';

/**
 * React Query bindings for the third-party weather provider framework
 * (Phases A–D). Everything here is CONTEXT-ONLY: the catalog/context reads are
 * descriptive, and the import mutations trigger explicitly-bounded, idempotent
 * pulls that never feed expected math. Account mutations invalidate the account
 * list; a successful import invalidates the per-site external-weather context so
 * the read-only provenance panel reflects newly-stored observations.
 */
export const weatherProviderKeys = {
  all: ['weatherProvider'] as const,
  providers: (includeDisabled: boolean) => [...weatherProviderKeys.all, 'providers', { includeDisabled }] as const,
  accounts: (companyId: number, includeArchived: boolean) =>
    [...weatherProviderKeys.all, 'accounts', companyId, { includeArchived }] as const,
  context: (siteId: number) => [...weatherProviderKeys.all, 'context', siteId] as const
};

const STALE_CATALOG = 60 * 1000;
const STALE_LIST = 30 * 1000;

export const useWeatherProviders = (
  options: { includeDisabled?: boolean } = {},
  queryOptions?: Omit<UseQueryOptions<WeatherProviderList>, 'queryKey' | 'queryFn'>
) => {
  const includeDisabled = options.includeDisabled ?? false;
  return useQuery({
    queryKey: weatherProviderKeys.providers(includeDisabled),
    queryFn: () => ApiClient.weather.listProviders(includeDisabled),
    staleTime: STALE_CATALOG,
    ...queryOptions
  });
};

export const useWeatherProviderAccounts = (
  companyId: number,
  options: { includeArchived?: boolean } = {},
  queryOptions?: Omit<UseQueryOptions<WeatherProviderAccountList>, 'queryKey' | 'queryFn'>
) => {
  const includeArchived = options.includeArchived ?? false;
  return useQuery({
    queryKey: weatherProviderKeys.accounts(companyId, includeArchived),
    queryFn: () => ApiClient.weather.listProviderAccounts(companyId, includeArchived),
    enabled: Number.isFinite(companyId) && companyId > 0,
    staleTime: STALE_LIST,
    ...queryOptions
  });
};

/**
 * Read-only external-weather context for a site. Safe for any site: a site with
 * no external sources returns an empty (zero-count) payload, so the panel can
 * render an honest "no external weather imported" state without a separate
 * probe. Never triggers a provider call.
 */
export const useExternalWeatherContext = (
  siteId: number,
  options?: Omit<UseQueryOptions<ExternalWeatherContextResponse>, 'queryKey' | 'queryFn'>
) =>
  useQuery({
    queryKey: weatherProviderKeys.context(siteId),
    queryFn: () => ApiClient.weather.getExternalWeatherContext(siteId),
    enabled: Number.isFinite(siteId) && siteId > 0,
    staleTime: STALE_LIST,
    ...options
  });

/**
 * Centralized account mutations for a company. Credential payloads are forwarded
 * to the API and never cached; responses carry only metadata. Archive is an
 * update to `status: 'archived'` (no hard delete) per the framework contract.
 */
export const useWeatherProviderAccountMutations = (companyId: number) => {
  const queryClient = useQueryClient();

  const invalidateAccounts = () => {
    queryClient.invalidateQueries({ queryKey: [...weatherProviderKeys.all, 'accounts', companyId] });
  };

  const createAccount = useMutation<WeatherProviderAccountResponse, Error, WeatherProviderAccountCreate>({
    mutationFn: payload => ApiClient.weather.createProviderAccount(companyId, payload),
    onSuccess: invalidateAccounts
  });

  const updateAccount = useMutation<
    WeatherProviderAccountResponse,
    Error,
    { accountId: number; payload: WeatherProviderAccountUpdate }
  >({
    mutationFn: ({ accountId, payload }) => ApiClient.weather.updateProviderAccount(companyId, accountId, payload),
    onSuccess: invalidateAccounts
  });

  const testAccount = useMutation<WeatherProviderTestResponse, Error, number>({
    mutationFn: accountId => ApiClient.weather.testProviderAccount(companyId, accountId),
    onSuccess: invalidateAccounts
  });

  const archiveAccount = useMutation<WeatherProviderAccountResponse, Error, number>({
    mutationFn: accountId => ApiClient.weather.updateProviderAccount(companyId, accountId, { status: 'archived' }),
    onSuccess: invalidateAccounts
  });

  return { createAccount, updateAccount, testAccount, archiveAccount, invalidateAccounts };
};

export type UseWeatherProviderAccountMutationsReturn = ReturnType<typeof useWeatherProviderAccountMutations>;

/**
 * Preview is a dry-run (no writes); it never invalidates anything. The run
 * mutation, on success, invalidates the site's external-weather context so the
 * read-only provenance panel reflects the newly-stored observations.
 */
export const useProviderImport = (siteId: number) => {
  const queryClient = useQueryClient();

  const preview = useMutation<ProviderImportPreviewResponse, Error, ProviderImportRequest>({
    mutationFn: payload => ApiClient.weather.previewProviderImport(siteId, payload)
  });

  const run = useMutation<ProviderImportResponse, Error, ProviderImportRequest>({
    mutationFn: payload => ApiClient.weather.runProviderImport(siteId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: weatherProviderKeys.context(siteId) });
    }
  });

  return { preview, run };
};
