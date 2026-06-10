export type ProviderAccountStatus = 'active' | 'paused' | 'archived';

export type CredentialStatus = 'unverified' | 'verified' | 'invalid' | 'expired';

export type LastSyncStatus = 'never' | 'success' | 'partial' | 'failed';

export type CompanyProviderStatus = 'active' | 'suspended';

export type ExternalSiteSyncStatus = 'seen' | 'missing' | 'stale';

export interface ProviderCatalogEntry {
  id: number;
  provider_key: string;
  display_name: string;
  config_schema: Record<string, unknown>;
  docs_url: string | null;
  is_enabled: boolean;
}

export interface ProviderCatalogList {
  items: ProviderCatalogEntry[];
}

export interface LicensedProvider {
  id: number;
  company_id: number;
  provider_key: string;
  display_name: string;
  status: CompanyProviderStatus;
  notes: string | null;
  account_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface LicensedProviderList {
  items: LicensedProvider[];
}

export interface LicenseCreatePayload {
  provider_key: string;
  notes?: string | null;
}

/**
 * Write-only credential payload. The backend never echoes these fields back
 * in any response. The frontend must not store them in any persistent state,
 * pass them to siblings/components, or include them in props beyond the
 * single dialog that submits them.
 */
export interface ProviderAccountCredentialsPayload {
  fields: Record<string, string>;
}

export interface ProviderAccountCreatePayload {
  name: string;
  provider_key: string;
  external_account_label?: string | null;
  credentials: ProviderAccountCredentialsPayload;
}

export interface ProviderAccountUpdatePayload {
  name?: string;
  external_account_label?: string | null;
  status?: ProviderAccountStatus;
  credentials?: ProviderAccountCredentialsPayload;
}

export interface ProviderAccount {
  id: number;
  company_id: number;
  name: string;
  provider_key: string;
  display_name: string;
  external_account_label: string | null;
  status: ProviderAccountStatus;
  credential_status: CredentialStatus;
  last_sync_status: LastSyncStatus;
  last_success_at: string | null;
  last_error_at: string | null;
  last_error_message: string | null;
  is_archived: boolean;
  archived_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  credentials_fingerprint: string | null;
  external_site_count: number;
  active_mapping_count: number;
}

export interface ProviderAccountList {
  items: ProviderAccount[];
}

export interface TestAccountResponse {
  success: boolean;
  message: string;
  credential_status: CredentialStatus;
  available_sites_count: number | null;
}

export interface ExternalSite {
  id: number;
  provider_account_id: number;
  external_site_id: string;
  external_site_name: string | null;
  sync_status: ExternalSiteSyncStatus;
  first_seen_at: string;
  last_seen_at: string;
  last_synced_at: string;
  last_sync_run_id: string | null;
  last_sync_error: string | null;
}

export interface ExternalSiteListResponse {
  items: ExternalSite[];
  last_sync_run_id: string | null;
  last_sync_status: LastSyncStatus;
  last_success_at: string | null;
}

export interface SyncSitesResponse {
  sync_run_id: string;
  last_sync_status: LastSyncStatus;
  seen_count: number;
  new_count: number;
  missing_count: number;
  error: string | null;
}

/**
 * Payload for the V2 (DB-only) project/site mapping save. The mapping is keyed
 * on `{provider_account_id, external_site_id}`; the display name is resolved
 * server-side from the iliOS external-site cache, so no live provider call is
 * required when the site has already been synced.
 */
export interface SiteMappingSavePayload {
  provider_account_id: number;
  external_site_id: string;
  mapping_role?: string;
}

export interface SiteMappingResponse {
  id: number;
  site_id: number | null;
  company_id: number | null;
  connection_id: number | null;
  provider_account_id: number | null;
  telemetry_site_id: string;
  telemetry_site_name: string;
  mapping_role: string;
  is_active: boolean;
  created_by_user_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * A single external (provider-side) device cached in the iliOS DB. Populated by
 * the V2 `sync-devices` call and read cache-only when opening Device Mapping.
 */
export interface ExternalDevice {
  id: number;
  provider_account_id: number;
  external_site_id: string;
  external_device_id: string;
  external_device_name: string | null;
  sync_status: ExternalSiteSyncStatus;
  first_seen_at: string;
  last_seen_at: string;
  last_synced_at: string;
  last_sync_run_id: string | null;
  last_sync_error: string | null;
}

export interface ExternalDeviceListResponse {
  items: ExternalDevice[];
  last_sync_run_id: string | null;
  last_sync_status: LastSyncStatus;
  last_success_at: string | null;
}

export interface SyncDevicesResponse {
  sync_run_id: string;
  last_sync_status: LastSyncStatus;
  seen_count: number;
  new_count: number;
  missing_count: number;
  error: string | null;
}

/**
 * A single iliOS device -> external device pairing. The display name is resolved
 * server-side from the synced device cache, so it is not sent here.
 */
export interface DeviceMappingItem {
  device_id: number;
  external_device_id: string;
  device_role?: string;
}

/**
 * Payload for the V2 (DB-only) bulk device mapping save. Mappings are keyed on
 * `{provider_account_id, external_site_id}`; each external device must already
 * exist in the synced device cache so no live provider call is required.
 */
export interface DeviceMappingBulkPayload {
  provider_account_id: number;
  external_site_id: string;
  mappings: DeviceMappingItem[];
}

export interface DeviceMappingBulkResponse {
  successful_count: number;
  failed_count: number;
  errors: string[] | null;
}
