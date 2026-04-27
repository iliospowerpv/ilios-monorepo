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
