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

site_am_sections_doc = "\n\n".join(
    [
        f"{index}. {section_name}: {section_schema.__name__}"
        for index, (section_name, section_schema) in enumerate(SITE_AM_SECTIONS_MAPPING.items(), start=1)
    ]
)
