"""Enums for the Entity Directory system."""

import enum


class EntityType(enum.Enum):
    epc_contractor = "epc_contractor"
    om_provider = "om_provider"
    utility = "utility"
    insurance = "insurance"
    engineering = "engineering"
    legal = "legal"
    accounting = "accounting"
    bank = "bank"
    investor = "investor"
    developer = "developer"
    offtaker = "offtaker"
    subscriber_manager = "subscriber_manager"
    vegetation = "vegetation"
    community_solar = "community_solar"
    tax_equity = "tax_equity"
    other = "other"


class EntityRelationshipRole(enum.Enum):
    epc_contractor = "epc_contractor"
    om_provider = "om_provider"
    interconnection_utility = "interconnection_utility"
    insurance_provider = "insurance_provider"
    community_solar_manager = "community_solar_manager"
    vegetation_vendor = "vegetation_vendor"
    offtaker = "offtaker"
    tax_equity_provider = "tax_equity_provider"
    developer = "developer"
    compliance_entity = "compliance_entity"
    compliance_bank = "compliance_bank"
    hold_co = "hold_co"
    project_co = "project_co"
    landlord = "landlord"
    tenant = "tenant"


class DealEntityRole(enum.Enum):
    developer = "developer"
    project_company = "project_company"
    offtaker = "offtaker"
    offtaker_legal = "offtaker_legal"
