import type { AxiosInstance } from 'axios';

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
  SiteMappingResponse,
  SiteMappingSavePayload,
  SyncDevicesResponse,
  SyncSitesResponse,
  TestAccountResponse
} from '../types/telemetryV2';

const V2 = '/api/telemetry/v2';

export const buildTelemetryV2Api = (httpClient: AxiosInstance) => {
  const getCatalog = async (): Promise<ProviderCatalogList> => {
    const { data } = await httpClient.get<ProviderCatalogList>(`${V2}/catalog`);
    return data;
  };

  const listLicensedProviders = async (companyId: number): Promise<LicensedProviderList> => {
    const { data } = await httpClient.get<LicensedProviderList>(`${V2}/companies/${companyId}/licensed-providers`);
    return data;
  };

  const grantLicense = async (companyId: number, payload: LicenseCreatePayload): Promise<LicensedProvider> => {
    const { data } = await httpClient.post<LicensedProvider>(
      `${V2}/companies/${companyId}/licensed-providers`,
      payload
    );
    return data;
  };

  const revokeLicense = async (companyId: number, licenseId: number): Promise<void> => {
    await httpClient.delete(`${V2}/companies/${companyId}/licensed-providers/${licenseId}`);
  };

  const listProviderAccounts = async (
    companyId: number,
    options: { includeArchived?: boolean } = {}
  ): Promise<ProviderAccountList> => {
    const params = options.includeArchived ? '?include_archived=true' : '';
    const { data } = await httpClient.get<ProviderAccountList>(
      `${V2}/companies/${companyId}/provider-accounts${params}`
    );
    return data;
  };

  const getProviderAccount = async (companyId: number, accountId: number): Promise<ProviderAccount> => {
    const { data } = await httpClient.get<ProviderAccount>(
      `${V2}/companies/${companyId}/provider-accounts/${accountId}`
    );
    return data;
  };

  /**
   * Creates a provider account and persists the credentials write-only.
   * The server intentionally does NOT call the external provider here;
   * the new account appears with credential_status=unverified and
   * last_sync_status=never. The UI must prompt the user to test next.
   */
  const createProviderAccount = async (
    companyId: number,
    payload: ProviderAccountCreatePayload
  ): Promise<ProviderAccount> => {
    const { data } = await httpClient.post<ProviderAccount>(`${V2}/companies/${companyId}/provider-accounts`, payload);
    return data;
  };

  /**
   * PATCH supports renaming, status changes, and credential rotation. When
   * `credentials` is provided the server adds a new secret version (or
   * mints a fresh secret in legacy fallback) and resets credential_status
   * to unverified. Credential values are never returned in the response.
   */
  const updateProviderAccount = async (
    companyId: number,
    accountId: number,
    payload: ProviderAccountUpdatePayload
  ): Promise<ProviderAccount> => {
    const { data } = await httpClient.patch<ProviderAccount>(
      `${V2}/companies/${companyId}/provider-accounts/${accountId}`,
      payload
    );
    return data;
  };

  const archiveProviderAccount = async (companyId: number, accountId: number): Promise<void> => {
    await httpClient.delete(`${V2}/companies/${companyId}/provider-accounts/${accountId}`);
  };

  const testProviderAccount = async (accountId: number): Promise<TestAccountResponse> => {
    const { data } = await httpClient.post<TestAccountResponse>(`${V2}/provider-accounts/${accountId}/test`);
    return data;
  };

  const syncProviderAccountSites = async (accountId: number): Promise<SyncSitesResponse> => {
    const { data } = await httpClient.post<SyncSitesResponse>(`${V2}/provider-accounts/${accountId}/sync-sites`);
    return data;
  };

  const listExternalSites = async (accountId: number): Promise<ExternalSiteListResponse> => {
    const { data } = await httpClient.get<ExternalSiteListResponse>(
      `${V2}/provider-accounts/${accountId}/external-sites`
    );
    return data;
  };

  /**
   * Create or update the project/site -> external-site mapping in the iliOS DB.
   * This is the V2 (DB-only) save path: it does not require a live provider call
   * or any GCP/Firestore sync. The selected external site must already exist in
   * the synced cache for the connection.
   */
  const saveSiteMapping = async (siteId: number, payload: SiteMappingSavePayload): Promise<SiteMappingResponse> => {
    const { data } = await httpClient.put<SiteMappingResponse>(`${V2}/sites/${siteId}/mapping`, payload);
    return data;
  };

  /**
   * Read the synced device cache for one external site. This is cache-only: it
   * never triggers a live provider call, so opening Device Mapping is safe even
   * when the provider is unreachable.
   */
  const listExternalDevices = async (
    accountId: number,
    externalSiteId: string
  ): Promise<ExternalDeviceListResponse> => {
    const { data } = await httpClient.get<ExternalDeviceListResponse>(
      `${V2}/provider-accounts/${accountId}/external-sites/${encodeURIComponent(externalSiteId)}/devices`
    );
    return data;
  };

  /**
   * Explicitly refresh the device cache for one external site by calling the
   * provider once. Never wipes existing cache/mappings on failure.
   */
  const syncProviderAccountDevices = async (
    accountId: number,
    externalSiteId: string
  ): Promise<SyncDevicesResponse> => {
    const { data } = await httpClient.post<SyncDevicesResponse>(
      `${V2}/provider-accounts/${accountId}/external-sites/${encodeURIComponent(externalSiteId)}/sync-devices`
    );
    return data;
  };

  /**
   * Persist iliOS device -> external device mappings in the iliOS DB. V2
   * (DB-only) path: no live provider call, no GCP/Firestore sync. Each external
   * device must already exist in the synced device cache.
   */
  const saveDeviceMappings = async (
    siteId: number,
    payload: DeviceMappingBulkPayload
  ): Promise<DeviceMappingBulkResponse> => {
    const { data } = await httpClient.post<DeviceMappingBulkResponse>(`${V2}/sites/${siteId}/device-mappings`, payload);
    return data;
  };

  return {
    getCatalog,
    listLicensedProviders,
    grantLicense,
    revokeLicense,
    listProviderAccounts,
    getProviderAccount,
    createProviderAccount,
    updateProviderAccount,
    archiveProviderAccount,
    testProviderAccount,
    syncProviderAccountSites,
    listExternalSites,
    saveSiteMapping,
    listExternalDevices,
    syncProviderAccountDevices,
    saveDeviceMappings
  };
};

export type TelemetryV2Api = ReturnType<typeof buildTelemetryV2Api>;
