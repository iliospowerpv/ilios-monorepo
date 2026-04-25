"""Pydantic schemas for the v2 telemetry API.

Credential fields are write-only — they are accepted on create/update payloads
but never appear on response schemas. The three-state account model
(``status``, ``credential_status``, ``last_sync_status``) is exposed on
account responses without ever leaking credential values.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.telemetry import (
    CompanyProviderStatus,
    CredentialStatus,
    ExternalSiteSyncStatus,
    LastSyncStatus,
    ProviderAccountStatus,
)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class ProviderCatalogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_key: str = Field(examples=["also_energy"])
    display_name: str = Field(examples=["Also Energy"])
    config_schema: dict[str, Any] = Field(default_factory=dict)
    docs_url: Optional[str] = None
    is_enabled: bool = True


class ProviderCatalogList(BaseModel):
    items: list[ProviderCatalogEntry]


# ---------------------------------------------------------------------------
# Company licenses
# ---------------------------------------------------------------------------


class LicensedProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    provider_key: str = Field(description="Catalog key (e.g. 'also_energy')")
    display_name: str = Field(description="Human-friendly provider name")
    status: CompanyProviderStatus = CompanyProviderStatus.active
    notes: Optional[str] = None
    account_count: int = Field(default=0, description="Number of provider accounts using this license")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LicensedProviderList(BaseModel):
    items: list[LicensedProviderResponse]


class LicenseCreateRequest(BaseModel):
    provider_key: str = Field(description="Provider catalog key", examples=["also_energy"])
    notes: Optional[str] = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Provider accounts (formerly DAS connections)
# ---------------------------------------------------------------------------


class ProviderAccountCredentials(BaseModel):
    """Write-only credential payload validated against the catalog config schema."""

    fields: dict[str, str] = Field(
        default_factory=dict,
        description="Provider-specific credential fields (e.g. token, username/password).",
    )

    @field_validator("fields")
    @classmethod
    def _strip_blank(cls, v: dict[str, str]) -> dict[str, str]:
        return {k: val for k, val in v.items() if val is not None and val != ""}


class ProviderAccountCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    provider_key: str = Field(description="Provider catalog key", examples=["also_energy"])
    external_account_label: Optional[str] = Field(default=None, max_length=255)
    credentials: ProviderAccountCredentials = Field(
        description="Write-only credential payload"
    )

    @model_validator(mode="after")
    def _require_credentials(self):
        if not self.credentials.fields:
            raise ValueError("credentials.fields is required and cannot be empty")
        return self


class ProviderAccountUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    external_account_label: Optional[str] = Field(default=None, max_length=255)
    status: Optional[ProviderAccountStatus] = None
    credentials: Optional[ProviderAccountCredentials] = Field(
        default=None,
        description="Optional rotation; omit to leave credentials unchanged",
    )


class ProviderAccountResponse(BaseModel):
    """Response — never includes credentials in any form."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    provider_key: str
    display_name: str
    external_account_label: Optional[str] = None
    status: ProviderAccountStatus
    credential_status: CredentialStatus
    last_sync_status: LastSyncStatus
    last_success_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    credentials_fingerprint: Optional[str] = Field(
        default=None,
        description="Short non-reversible fingerprint of stored credentials, "
        "for operator correlation only.",
    )


class ProviderAccountList(BaseModel):
    items: list[ProviderAccountResponse]


class TestAccountResponse(BaseModel):
    success: bool
    message: str
    credential_status: CredentialStatus
    available_sites_count: Optional[int] = None


# ---------------------------------------------------------------------------
# External sites (sync provenance)
# ---------------------------------------------------------------------------


class ExternalSiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_account_id: int
    external_site_id: str
    external_site_name: Optional[str] = None
    sync_status: ExternalSiteSyncStatus
    first_seen_at: datetime
    last_seen_at: datetime
    last_synced_at: datetime
    last_sync_run_id: Optional[str] = None
    last_sync_error: Optional[str] = None


class ExternalSiteList(BaseModel):
    items: list[ExternalSiteResponse]
    last_sync_run_id: Optional[str] = None
    last_sync_status: LastSyncStatus
    last_success_at: Optional[datetime] = None


class SyncSitesResponse(BaseModel):
    sync_run_id: str
    last_sync_status: LastSyncStatus
    seen_count: int
    new_count: int
    missing_count: int
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Site mappings (richer m:n)
# ---------------------------------------------------------------------------


class SiteMappingCreateRequest(BaseModel):
    site_id: int
    external_site_id: str = Field(min_length=1, max_length=255)
    external_site_name: str = Field(min_length=1, max_length=512)
    mapping_role: str = Field(default="primary", max_length=32)


class SiteMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: Optional[int]
    provider_account_id: Optional[int]
    telemetry_site_id: str
    telemetry_site_name: str
    mapping_role: str = "primary"
    is_active: bool = True


class SiteMappingList(BaseModel):
    items: list[SiteMappingResponse]
