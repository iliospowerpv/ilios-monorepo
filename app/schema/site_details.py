"""API Schema for site-related Endpoints"""

import logging
from datetime import date, datetime, timezone
from typing import ClassVar, Optional

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator

from app.models.site import LeasePaymentFrequencies, LeasePaymentMethods, MountTypes, OfftakerTypes, SiteStatuses
from app.schema.common import date_field_validator
from app.schema.site import BaseSiteSchema

"""
Unfortunately, Pydantic URL field is always await to be prefixed with scheme (e.g. http).
We need to allow all sites be valid (such as www.site.org, site.org, http(s)://site.org)
"""
URL_PATTERN = (
    r"(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})"
    r"?\/[a-zA-Z0-9]{2,}|((https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})"
    r"(\.[a-zA-Z]{2,})?)|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}"
    r"\.[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})?"
)
BLANK_VALUE = ""


def phone_field_validator(phone: str):
    """Validate phone is a number-only string 10 characters long, or None"""
    if not phone:
        return phone
    if not phone.isnumeric():
        raise ValueError("Expected numbers-only")
    if not len(phone) == 10:
        raise ValueError("Must be 10 digits")
    return phone


class SiteLevelDetailsUpdateSchema(BaseModel):
    status: Optional[SiteStatuses] = Field(None, examples=["Placed In Service"])
    project_id: Optional[str] = Field(None, examples=[BLANK_VALUE], max_length=100)
    pvsyst: Optional[str] = Field(None, examples=["link"], min_length=2, pattern=URL_PATTERN)
    greenhouse_gas_offset: Optional[str] = Field(None, examples=[BLANK_VALUE], max_length=100)
    incentive_program: Optional[str] = Field(None, examples=[BLANK_VALUE], max_length=100)
    das_provider: Optional[str] = Field(None, examples=["DAS provider"], max_length=100)
    das_account: Optional[str] = Field(None, examples=["DAS account"], max_length=100)
    das_username: Optional[str] = Field(None, examples=["DAS username"], max_length=100)
    das_password: Optional[str] = Field(None, examples=["12345678"], max_length=100)


class SiteLevelDetailsViewSchema(SiteLevelDetailsUpdateSchema, BaseSiteSchema):
    cameras_uuids: ClassVar
    year_one_expected_production: str | None = Field(examples=[1200])
    degradation_amount: str | None = Field(examples=[0.5])
    capacity_as_percent_of_total_portfolio: float | None = Field(default=None, examples=[10.5])


class AssetOverviewUpdateSchema(BaseModel):
    battery_storage: Optional[str] = Field(None, examples=["Yes"])
    mount_type: Optional[MountTypes] = Field(None, examples=["Fixed Tilt Ground Mount"])
    dc_wiring_loss: float = Field(examples=[0.58])
    ac_wiring_loss: float = Field(examples=[-0.71])
    medium_voltage_loss: float = Field(examples=[-1.35])
    mv_line_loss: float = Field(examples=[-0.01])

    @field_validator("battery_storage")
    @classmethod
    def verify_battery_storage(cls, battery_storage: str):
        """Verify battery storage is a 'Yes' or 'No' string"""
        if battery_storage and battery_storage not in ["Yes", "No"]:
            raise ValueError("Expected 'Yes' or 'No'")
        return battery_storage


class AssetOverviewViewSchema(AssetOverviewUpdateSchema):
    module_quantity: Optional[str] = Field(examples=["4"])
    inverter_quantity: Optional[str] = Field(examples=["4"])
    project_type: Optional[str] = Field(examples=["Ground"])
    # over-write fields, which are required in the edit form, but can be null if section wasn't edited
    dc_wiring_loss: Optional[float] = None
    ac_wiring_loss: Optional[float] = None
    medium_voltage_loss: Optional[float] = None
    mv_line_loss: Optional[float] = None


class OwnershipUpdateSchema(BaseModel):
    ownership_structure: Optional[str] = Field(None, examples=["Tax Equity Only"], max_length=100)
    hold_co: Optional[str] = Field(None, examples=["Shawmut Solar Holdings, LLC"], max_length=100)
    project_co: Optional[str] = Field(None, examples=[BLANK_VALUE], max_length=100)
    tax_credit_fund: Optional[str] = Field(None, examples=["credit fund"], max_length=100)


class OwnershipViewSchema(OwnershipUpdateSchema):
    project_co: Optional[str] = Field(None, examples=[BLANK_VALUE])
    guarantor: Optional[str] = Field(examples=[BLANK_VALUE])


class TaxEquitySchema(BaseModel):
    tax_equity_fund: Optional[str] = Field(None, examples=["AZ-REA TCF2, LLC"], max_length=100)
    tax_equity_provider: Optional[str] = Field(None, examples=[BLANK_VALUE], max_length=100)
    tax_equity_buyout_amount: Optional[float] = Field(None, examples=[460874])
    tax_equity_buyout_date: Optional[date] = Field(None, examples=["2026-12-21"])
    tax_equity_pref_rate: Optional[float] = Field(None, examples=[2.73])
    smartsheet_data_tape: Optional[str] = Field(None, examples=["($XX.XX)"], max_length=100)

    _validate_date = field_validator("tax_equity_buyout_date", mode="before")(date_field_validator)


class KeyDatesUpdateSchema(BaseModel):
    permission_to_operate: Optional[date] = Field(None, examples=["2020-01-04"])
    placed_in_service_date: Optional[date] = Field(None, examples=["2020-01-04"])
    financial_close_date: Optional[date] = Field(None, examples=["2025-01-07"])

    _validate_date = field_validator(
        "permission_to_operate", "placed_in_service_date", "financial_close_date", mode="before"
    )(date_field_validator)


class KeyDatesViewSchema(KeyDatesUpdateSchema):
    permission_to_operate: Optional[date] = Field(None, examples=["2025-01-07"])
    mechanical_completion_date: Optional[str] = Field(examples=["2018-12-27"])
    substantial_completion_date: Optional[str] = Field(examples=["2019-02-14"])
    final_completion_date: Optional[str] = Field(examples=["2019-03-25"])


class OnMUpdateSchema(BaseModel):
    om_address: Optional[str] = Field(None, examples=["1500 19th Ave. SW Byron, MN 55920"], max_length=100)
    om_contact_name: Optional[str] = Field(None, examples=["John Starks"], max_length=100)
    om_contact_email: Optional[EmailStr] = Field(None, examples=["johnstarks@gmail.com"], max_length=100)
    om_contact_phone: Optional[str] = Field(None, examples=["5733455671"])
    o_and_m_rate: Optional[float] = Field(None, examples=[1])

    _validate_phone_field = field_validator("om_contact_phone")(phone_field_validator)


class OnMViewSchema(OnMUpdateSchema):
    provider: Optional[str] = Field(examples=["Novel Energy Solutions L.L.C"])
    agreement_effective_date: Optional[str] = Field(examples=["01/07/22"])
    o_and_m_escalator: Optional[str] = Field(examples=["2"])
    production_guarantee: Optional[str] = Field(examples=[BLANK_VALUE])


class InterconnectionUtilityProviderUpdateSchema(BaseModel):
    iut_address: Optional[str] = Field(None, examples=["60 Campanelli Drive, Braintree, MA"], max_length=100)
    iut_contact_name: Optional[str] = Field(None, examples=["Stan Mcbride"], max_length=100)
    iut_contact_email: Optional[EmailStr] = Field(None, examples=["stanmcbride@gmail.com"], max_length=100)
    iut_contact_phone: Optional[str] = Field(None, examples=["6043455671"])
    utility_rate: Optional[str] = Field(None, examples=[BLANK_VALUE], max_length=100)

    _validate_phone_field = field_validator("iut_contact_phone")(phone_field_validator)


class InterconnectionUtilityProviderViewSchema(InterconnectionUtilityProviderUpdateSchema):
    provider: Optional[str] = Field(examples=[BLANK_VALUE])
    ppa_term: Optional[str] = Field(examples=["20"])  # years
    ppa_effective_date: Optional[str] = Field(examples=["12/14/2022"])
    production_guarantee: Optional[str] = Field(examples=["NA"])
    interconnection_agreement_effective_date: Optional[str] = Field(examples=["01/07/22"])

    @computed_field
    @property
    def remaining_ppa_term(self) -> str | None:
        """Calculate how many years and months are remaining since ppa_effective_date according to the date today"""
        if self.ppa_effective_date and self.ppa_term:
            try:
                ppa_effective_date = datetime.strptime(self.ppa_effective_date, "%m/%d/%Y")
                ppa_term_end_date = datetime(
                    year=ppa_effective_date.year + int(self.ppa_term),
                    month=ppa_effective_date.month,
                    day=ppa_effective_date.day,
                    tzinfo=timezone.utc,
                )

                now = datetime.now(timezone.utc)
                delta = relativedelta(ppa_term_end_date, now)
                remaining_years, remaining_months = delta.years, delta.months

                if remaining_years > int(self.ppa_term):  # ppa term not started yet
                    return f"{self.ppa_term} years, 0 months"
                if remaining_months < 0:  # ppa term already expired
                    return "0 years, 0 months"

                return (
                    f"{remaining_years} {'year' if remaining_years == 1 else 'years'}, "
                    f"{delta.months} {'month' if remaining_months == 1 else 'months'}"
                )
            except Exception as error_msg:
                # TODO: temporary solution for ppa_effective_date calculation,
                #  should be removed after calculation process and field values are agreed
                logging.exception(f"It is not possible to calculate remaining ppa_effective_date due to {error_msg}")
                return None
        else:
            return None


class EPCContractorUpdateSchema(BaseModel):
    epc_address: Optional[str] = Field(None, examples=["1503 Country Club Rd SE, Byron, MN 55920"], max_length=100)
    epc_contact_name: Optional[str] = Field(None, examples=["Collin Drake"], max_length=100)
    epc_contact_email: Optional[EmailStr] = Field(None, examples=["collindr@gmail.com"], max_length=100)
    epc_contact_phone: Optional[str] = Field(None, examples=["6043455671"])

    _validate_phone_field = field_validator("epc_contact_phone")(phone_field_validator)


class EPCContractorViewSchema(EPCContractorUpdateSchema):
    provider: str | None = Field(examples=["SunRaise Development, LLC"])
    agreement_effective_date: str | None = Field(examples=["01/07/22"])


class CommunitySolarManagerSchema(BaseModel):
    csm_provider: Optional[str] = Field(None, examples=["PowerMarket"], max_length=100)
    csm_address: Optional[str] = Field(None, examples=["21 Alpha Road, Chelmsford, MA 01824"], max_length=100)
    csm_contact_name: Optional[str] = Field(None, examples=["Collin Snow"], max_length=100)
    csm_contact_email: Optional[EmailStr] = Field(None, examples=["collinsnow@gmail.com"], max_length=100)
    csm_contact_phone: Optional[str] = Field(None, examples=["6043455671"])
    csm_fee: Optional[float] = Field(None, examples=[24.45])
    escalator: Optional[float] = Field(None, examples=[35.45])
    escalator_effective: Optional[date] = Field(None, examples=["2024-05-12"])

    _validate_phone_field = field_validator("csm_contact_phone")(phone_field_validator)
    _validate_date = field_validator("escalator_effective", mode="before")(date_field_validator)


class InsuranceProviderSchema(BaseModel):
    insurance_provider: Optional[str] = Field(None, examples=["Chubb Insurance"], max_length=100)
    insurance_address: Optional[str] = Field(None, examples=["100 Enterprise Ave, Gardiner, ME 04345"], max_length=100)


class SiteLeaseUpdateSchema(BaseModel):
    payment_due_date: Optional[date] = Field(None, examples=["25 years from COD"])
    lease_payment_method: Optional[LeasePaymentMethods] = Field(None, examples=["Check"])
    lease_payment_frequency: Optional[LeasePaymentFrequencies] = Field(None, examples=["Monthly"])
    landlord_contact_phone: Optional[str] = Field(None, examples=["6045685678"])

    _validate_phone_field = field_validator("landlord_contact_phone")(phone_field_validator)


class SiteLeaseViewSchema(SiteLeaseUpdateSchema):
    landlord: Optional[str] = Field(examples=["Brixmor Holdings 1 SPE, LLC"])
    tenant: Optional[str] = Field(examples=["GreenLife Solar, LLC d/b/a Shine Development Partners"])
    property_size: Optional[str] = Field(examples=["24.6257"])
    effective_date: Optional[str] = Field(examples=["01/07/25"])
    rent_escalator: Optional[str] = Field(examples=["2"])
    rent_commencement: Optional[str] = Field(examples=["01/07/24"])
    rent_amount: Optional[str] = Field(examples=["24625.70"])
    rent_escalator_effective_date: Optional[str] = Field(examples=["01/07/26"])
    initial_term: Optional[str] = Field(examples=["20 years beginning on the date the Permission to Operate was issued"])
    renewal_terms: Optional[str] = Field(
        examples=[
            "Three (3) additional five (5) year periods with written notice ninety (90) days prior to the expiration"
        ]
    )


class VegetationVendorSchema(BaseModel):
    vv_provider: Optional[str] = Field(None, examples=["Acme Corporation"], max_length=100)
    vv_address: Optional[str] = Field(None, examples=["5445 N 27th St, Milwaukee, WI"], max_length=100)
    vv_contact_name: Optional[str] = Field(None, examples=["John Doe"], max_length=100)
    vv_contact_phone: Optional[str] = Field(None, examples=["5551234567"])
    vv_contact_email: Optional[EmailStr] = Field(None, examples=["john.doe@acmecorp.com"], max_length=100)

    _validate_phone_field = field_validator("vv_contact_phone")(phone_field_validator)


class OfftakerSchema(BaseModel):
    offtaker_name: Optional[str] = Field(None, examples=["Sunshine Energy"], max_length=100)
    offtaker_type: Optional[OfftakerTypes] = Field(None, examples=["Community Solar"])
    credit_rating: Optional[str] = Field(None, examples=["BB+"], max_length=100)
    rating_agency: Optional[str] = Field(None, examples=["Standard & Poor’s"], max_length=100)
    date_of_rating: Optional[date] = Field(None, examples=["2024-01-07"])

    _validate_date = field_validator("date_of_rating", mode="before")(date_field_validator)


class ComplianceSchema(BaseModel):
    entity: Optional[str] = Field(None, examples=["Global Compliance Services"], max_length=100)
    bank: Optional[str] = Field(None, examples=["Regulatory Bank Corp."], max_length=100)
    report_due_date: Optional[date] = Field(None, examples=["2024-08-15"])
    fiscal_year_end: Optional[date] = Field(None, examples=["2024-12-31"])
    tax_return_deadline: Optional[date] = Field(None, examples=["2025-04-30"])

    _validate_date = field_validator("report_due_date", "fiscal_year_end", "tax_return_deadline", mode="before")(
        date_field_validator
    )


class SiteFullDetailsSchema(BaseModel):
    site_level_details: SiteLevelDetailsViewSchema
    asset_overview: AssetOverviewViewSchema
    ownership: OwnershipViewSchema
    tax_equity: TaxEquitySchema
    key_dates: KeyDatesViewSchema
    o_and_m: OnMViewSchema
    interconnection: InterconnectionUtilityProviderViewSchema
    epc_contractor: EPCContractorViewSchema
    community_solar_manager: CommunitySolarManagerSchema
    insurance_provider: InsuranceProviderSchema
    site_lease: SiteLeaseViewSchema
    vegetation_vendor: VegetationVendorSchema
    offtaker: OfftakerSchema
    compliance: ComplianceSchema
