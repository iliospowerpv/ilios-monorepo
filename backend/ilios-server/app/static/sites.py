from enum import Enum

from app.schema.site_details import (
    AssetOverviewUpdateSchema,
    CommunitySolarManagerSchema,
    ComplianceSchema,
    EPCContractorUpdateSchema,
    InsuranceProviderSchema,
    InterconnectionUtilityProviderUpdateSchema,
    KeyDatesUpdateSchema,
    OfftakerSchema,
    OnMUpdateSchema,
    OwnershipUpdateSchema,
    SiteLeaseUpdateSchema,
    SiteLevelDetailsUpdateSchema,
    TaxEquitySchema,
    VegetationVendorSchema,
)


class SiteDetailsSections(str, Enum):
    """Names of the asset management site sections/cards"""

    site_level_details = "site_level_details"
    asset_overview = "asset_overview"
    ownership = "ownership"
    tax_equity = "tax_equity"
    key_dates = "key_dates"
    o_and_m = "o_and_m"
    interconnection = "interconnection"
    epc_contractor = "epc_contractor"
    community_solar_manager = "community_solar_manager"
    insurance_provider = "insurance_provider"
    site_lease = "site_lease"
    vegetation_vendor = "vegetation_vendor"
    offtaker = "offtaker"
    compliance = "compliance"


# Map section values to corresponding update schemas
SITE_AM_SECTIONS_MAPPING = {
    SiteDetailsSections.site_level_details.value: SiteLevelDetailsUpdateSchema,
    SiteDetailsSections.asset_overview.value: AssetOverviewUpdateSchema,
    SiteDetailsSections.ownership.value: OwnershipUpdateSchema,
    SiteDetailsSections.tax_equity.value: TaxEquitySchema,
    SiteDetailsSections.key_dates.value: KeyDatesUpdateSchema,
    SiteDetailsSections.o_and_m.value: OnMUpdateSchema,
    SiteDetailsSections.interconnection.value: InterconnectionUtilityProviderUpdateSchema,
    SiteDetailsSections.epc_contractor.value: EPCContractorUpdateSchema,
    SiteDetailsSections.community_solar_manager.value: CommunitySolarManagerSchema,
    SiteDetailsSections.insurance_provider.value: InsuranceProviderSchema,
    SiteDetailsSections.site_lease.value: SiteLeaseUpdateSchema,
    SiteDetailsSections.vegetation_vendor.value: VegetationVendorSchema,
    SiteDetailsSections.offtaker.value: OfftakerSchema,
    SiteDetailsSections.compliance.value: ComplianceSchema,
}

SITE_AM_SECTIONS_SCHEMAS = SITE_AM_SECTIONS_MAPPING.values()

# Baseline-driving fields that must never be written through the site-details edit form.
# These values are owned by the Data Room / promoted project-facts provenance chain and are
# rendered read-only in the Project Hub Overview (Phase 1+2). The update_site_details endpoint
# strips them from the update payload before persistence (preserving existing values, never
# blanking them) and, because the site-characteristics BigQuery handler maps only these fields,
# stripping them makes that sync a guaranteed no-op for these sections.
PROTECTED_BASELINE_DRIVING_FIELDS = {
    SiteDetailsSections.asset_overview: {
        "dc_wiring_loss",
        "ac_wiring_loss",
        "medium_voltage_loss",
        "mv_line_loss",
    },
    SiteDetailsSections.key_dates: {
        "permission_to_operate",
    },
}

site_am_sections_doc = "\n\n".join(
    [
        f"{index}. {section_name}: {section_schema.__name__}"
        for index, (section_name, section_schema) in enumerate(SITE_AM_SECTIONS_MAPPING.items(), start=1)
    ]
)
