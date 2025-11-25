"""make document key name field string

Revision ID: 1fcea2f7f527
Revises: a5adab2cb707
Create Date: 2024-08-06 13:48:39.644267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from enum import Enum

# revision identifiers, used by Alembic.
from app.crud.document_key import DocumentKeyCRUD

revision: str = '1fcea2f7f527'
down_revision: Union[str, None] = 'a5adab2cb707'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

class DocumentKeys(Enum):
    # site lease documents
    landlord_name = "Lessor (Landlord) Entity Name"
    tenant_name = "Lessee (Tenant) Entity Name"
    effective_date = "Effective Date"
    property_size = "Property Size"
    initial_term = "Initial Term"
    rent_commencement = "Rent Commencement"
    renewal_terms = "Renewal Terms"
    rent_calculation = "Rent Calculation"
    rent_amount = "Rent Amount"
    payment_terms = "Payment Terms"
    first_payment_due = "First Payment Due"
    expiration_date = "Expiration Date"
    renewal_notice_term = "Renewal Notice Term"
    lease_prepayment_applicable = "Site Lease Prepayment (Y/N)"
    lease_prepayment_amount = "Site Lease Prepayment (Amount)"
    removal_timeline_and_expectations = "Removal Timeline & Expectations"
    fee_simple_owner_applicable = "Fee Simple Owner (Y/N)"
    rent_escalator_applicable = "Rent Escalator (Y/N)"
    rent_escalator_amount = "Rent Escalator (Amount)"
    rent_escalator_effective_date = "Rent Escalator Effective Date"
    coterminus_ppa_applicable = "Co-terminus with PPA (Y/N)"
    lessee_termination = "Termination & Removal - Lessee"
    lessor_termination = "Termination & Removal - Lessor"
    termination_notice_requirements = "Termination - Notice Requirements"
    default = "Default"
    lessee_assignment = "Assignment by Lessee"
    lessor_assignment = "Assignment by Lessor"
    removal_requirements = "Removal Requirements"
    access_rights = "Site Access Rights"
    quiet_enjoyment = "Quiet Enjoyment"
    non_disturbance_requirements = "Non-Disturbance Requirements"
    snda = "SNDA"
    eminent_domain = "Eminent Domain"
    force_majeure = "Force Majeure"
    property_tax = "Property Tax ($)"
    purchase_options_available = "Purchase Options (Y/N)"
    liens = "Liens"
    amendments_assignments_estoppels = "Amendments, Assignments, and/or Estoppels"
    prevailing_party_provision_applicable = "Prevailing Party Provision (Y/N)"
    governing_law = "Governing Law"
    # interconnection
    interconnection_utility_company = "Interconnection Utility Company"
    interconnection_customer = "Interconnection Customer"
    term = "Term"
    nameplate_capacity_limits = "Nameplate Capacity Limits"
    mechanical_completion_date = "Mechanical Completion Date"
    commercial_operation_date = "Commercial Operation Date"
    interconnect_date_deadline = "Deadline to Interconnect Date"
    amendments_assignments = "Amendments and/or Assignments"
    provider_default = "Default by Provider"
    customer_default = "Default by Customer"
    disconnection_terms = "Terms for Disconnection"
    nameplate_capacity_size = "Nameplate Capacity (System Size)"
    customer_assignment = "Assignment by Customer"
    provider_assignment = "Assignment by Provider"
    customer_termination = "Termination by Customer"
    provider_termination = "Termination by Provider"
    insurance_requirements = "Insurance Requirements"
    taxes = "Taxes"
    economic_terms_summary = "Summary of Economic Terms"
    interconnection_cost_responsibility = "Cost Responsibility for Interconnection"
    system_upgrades_cost_responsibility = "Cost Responsibility for System Upgrades"
    prevailing_party_provision = "Prevailing Party Provision"
    responsible_party_metering = "Responsible Party for Metering"
    recurring_monthly_costs = "Recurring Monthly Costs"
    warranty = "Warranty"
    other_dates_referenced = "Other Dates/Deadlines Referenced"
    # PPA
    offtaker = "Offtaker"
    provider = "Provider"
    ppa_rate = "Power Purchase Agreement Rate"
    ppa_end_date = "Power Purchase Agreement End Date"
    commercial_operation_date_definition = "Commercial Operation Date Definition"
    buyout_option = "Buyout Option"
    buyout_amount = "Buyout Amount"
    nameplate_capacity = "Nameplate Capacity"
    projected_production = "Projected Production"
    degradation_amount = "Degradation Amount"
    production_guarantee = "Production Guarantee"
    metering_adjustment = "Metering Adjustment"
    ppa_rate_table = "Summary of Economic Terms (PPA Rate Table)"
    offtaker_default = "Default - Offtaker"
    ppa_provider_default = "Default - Provider"
    offtaker_termination = "Termination - Offtaker"
    ppa_provider_termination = "Termination - Provider"
    offtaker_assignment = "Assignment - Offtaker"
    ppa_provider_assignment = "Assignment - Provider"
    amendments_estoppels = "Amendments and/or Estoppels"
    tax_responsibilities = "Tax Responsibilities"
    workflow_questions = "Workflow Questions"
    lease_coterminus = "Coterminus with the Lease?"
    # O&M
    customer = "Customer"
    commencement_date = "Commencement Date"
    utility_company = "Utility Company"
    renewal = "Renewal"
    maintenance_service_fee = "Maintenance Service Fee"
    escalator = "Escalator"
    services_warranty_terms = "Services Warranty Terms"
    year_one_production = "Year 1 Production"
    production_guarantee_term = "Production Guarantee Term"
    production_estimate_definition = "Production Estimate - Definition"
    degradation = "Degradation"
    production_factor = "Production Factor"
    adjustments_production_loss = "Adjustments - Production Loss"
    guarantee_statement = "Statement of Guarantee"
    production_shortfall_rate = "Production Shortfall Rate"
    guarantee_limitations = "Guarantee Limitations"
    proactive_reactive_reporting = "Reporting (Proactive and Reactive)"
    om_customer_termination = "Termination - Customer"
    termination_maximum_liability = "Termination - Maximum Liability"
    om_customer_default = "Default - Customer"
    om_customer_assignment = "Assignment - Customer"
    prevailing_party = "Prevailing Party"
    ppa_net_energy_rate = "PPA Net Energy Rate"
    scope_and_services = "Scope & Services"
    noncovered_service_rate_schedule = "Noncovered Service - Rate Schedule"
    # EPC
    owner = "Owner"
    epc_contractor_name = "EPC Contractor Name"
    system_size = "System Size"
    address = "Address"
    construction_status = "Construction Status"
    mechanical_completion_definition = "Mechanical Completion - Definition"
    substantial_completion_definition = "Substantial Completion - Definition"
    final_completion_definition = "Final Completion - Definition"
    substantial_completion_within_mechanical_completion = (
        "Is Substantial Completion Date within 3 months of Mechanical Completion Date?"
    )
    substantial_completion_date = "Substantial Completion Date"
    liquidated_damages_depends_on_substantial_completion = (
        "Are Liquidated Damages Associated with Substantial Completion Date?"
    )
    final_completion_date = "Final Completion Date"
    owner_default = "Default - Owner"
    contractor_default = "Default - Contractor"
    owner_termination = "Termination - Owner"
    contractor_termination = "Termination - Contractor"
    warranties = "Warranties"
    guaranties = "Guaranties"
    owner_assignment = "Assignment - Owner"
    contractor_assignment = "Assignment - Contractor"
    mechanical_completion_rea_notification = "Mechanical Completion - Notification to REA by Developer"
    mechanical_completion_review_period = "Mechanical Completion - Review Period"
    mechanical_completion_acceptance = "Mechanical Completion - Acceptance"
    mechanical_completion_rejection = "Mechanical Completion - Rejection"
    substantial_completion_rea_notification = "Substantial Completion - Notification to REA by Developer"
    substantial_completion_review_period = "Substantial Completion - Review Period"
    substantial_completion_acceptance = "Substantial Completion - Acceptance"
    substantial_completion_rejection = "Substantial Completion - Rejection"
    final_completion_rea_notification = "Final Completion - Notification to REA by Developer"
    final_completion_review_period = "Final Completion - Review Period"
    final_completion_acceptance = "Final Completion - Acceptance"
    final_completion_rejection = "Final Completion - Rejection"
    pre_contract_payment = "Pre Contract Module Procurement Payment"
    lntp = "EPC Agreement Execution / LNTP"
    lntp2 = "LNTP #2"
    notice_to_proceed = "Notice to Proceed"
    site_preparation_completion = "Site Preparation Completion"
    racking_delivery = "Delivery of Racking to Site"
    modules_delivery = "Delivery of Modules to Site"
    inverters_delivery = "Delivery of Inverters & Energy Storage Unit to Site"
    racking_installation = "Racking Installation"
    modules_installation = "Module Installation"
    inverters_installation = "Inverters & Energy Storage Unit Installation"
    mechanical_completion = "Mechanical Completion"
    witness_test = "Witness Test"
    pto = "PTO"
    pv_substantial_completion = "PV Substantial Completion"
    ess_substantial_completion = "ESS Substantial Completion"
    final_completion = "Final Completion"


def get_value_by_key(key_name):
    for val in DocumentKeys:
        if val.name == key_name:
            return val.value


def get_key_by_value(key_value):
    for val in DocumentKeys:
        if val.value == key_value:
            return val.name

def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('document_keys', 'name',
               existing_type=postgresql.ENUM('landlord_name', 'tenant_name', 'effective_date', 'property_size', 'initial_term', 'rent_commencement', 'renewal_terms', 'rent_calculation', 'rent_amount', 'payment_terms', 'first_payment_due', 'expiration_date', 'renewal_notice_term', 'lease_prepayment_applicable', 'lease_prepayment_amount', 'removal_timeline_and_expectations', 'fee_simple_owner_applicable', 'rent_escalator_applicable', 'rent_escalator_amount', 'rent_escalator_effective_date', 'coterminus_ppa_applicable', 'lessee_termination', 'lessor_termination', 'termination_notice_requirements', 'default', 'lessee_assignment', 'lessor_assignment', 'removal_requirements', 'access_rights', 'quiet_enjoyment', 'non_disturbance_requirements', 'snda', 'eminent_domain', 'force_majeure', 'property_tax', 'purchase_options_available', 'liens', 'amendments_assignments_estoppels', 'prevailing_party_provision_applicable', 'governing_law', 'interconnection_utility_company', 'interconnection_customer', 'term', 'nameplate_capacity_limits', 'mechanical_completion_date', 'commercial_operation_date', 'interconnect_date_deadline', 'amendments_assignments', 'provider_default', 'customer_default', 'disconnection_terms', 'nameplate_capacity_size', 'customer_assignment', 'provider_assignment', 'customer_termination', 'provider_termination', 'insurance_requirements', 'taxes', 'economic_terms_summary', 'interconnection_cost_responsibility', 'system_upgrades_cost_responsibility', 'prevailing_party_provision', 'responsible_party_metering', 'recurring_monthly_costs', 'warranty', 'other_dates_referenced', 'offtaker', 'provider', 'ppa_rate', 'ppa_end_date', 'commercial_operation_date_definition', 'buyout_option', 'buyout_amount', 'nameplate_capacity', 'projected_production', 'degradation_amount', 'production_guarantee', 'metering_adjustment', 'ppa_rate_table', 'offtaker_default', 'ppa_provider_default', 'offtaker_termination', 'ppa_provider_termination', 'offtaker_assignment', 'ppa_provider_assignment', 'amendments_estoppels', 'tax_responsibilities', 'workflow_questions', 'lease_coterminus', 'customer', 'commencement_date', 'utility_company', 'renewal', 'maintenance_service_fee', 'escalator', 'services_warranty_terms', 'year_one_production', 'production_guarantee_term', 'production_estimate_definition', 'degradation', 'production_factor', 'adjustments_production_loss', 'guarantee_statement', 'production_shortfall_rate', 'guarantee_limitations', 'proactive_reactive_reporting', 'om_customer_termination', 'termination_maximum_liability', 'om_customer_default', 'om_customer_assignment', 'prevailing_party', 'ppa_net_energy_rate', 'scope_and_services', 'noncovered_service_rate_schedule', 'owner', 'epc_contractor_name', 'system_size', 'address', 'construction_status', 'mechanical_completion_definition', 'substantial_completion_definition', 'final_completion_definition', 'substantial_completion_within_mechanical_completion', 'substantial_completion_date', 'liquidated_damages_depends_on_substantial_completion', 'final_completion_date', 'owner_default', 'contractor_default', 'owner_termination', 'contractor_termination', 'warranties', 'guaranties', 'owner_assignment', 'contractor_assignment', 'mechanical_completion_rea_notification', 'mechanical_completion_review_period', 'mechanical_completion_acceptance', 'mechanical_completion_rejection', 'substantial_completion_rea_notification', 'substantial_completion_review_period', 'substantial_completion_acceptance', 'substantial_completion_rejection', 'final_completion_rea_notification', 'final_completion_review_period', 'final_completion_acceptance', 'final_completion_rejection', 'pre_contract_payment', 'lntp', 'lntp2', 'notice_to_proceed', 'site_preparation_completion', 'racking_delivery', 'modules_delivery', 'inverters_delivery', 'racking_installation', 'modules_installation', 'inverters_installation', 'mechanical_completion', 'witness_test', 'pto', 'pv_substantial_completion', 'ess_substantial_completion', 'final_completion', name='documentkeys'),
               type_=sa.String(),
               nullable=False)
    # transform enum values to the string key representation
    document_key_crud = DocumentKeyCRUD(db_session=sa.orm.Session(bind=op.get_bind()))
    for document_key in document_key_crud.get(skip_pagination=True):
        document_key_crud.update_by_id(document_key.id, {"name": get_value_by_key(document_key.name)})
    sa.Enum('landlord_name', 'tenant_name', 'effective_date', 'property_size', 'initial_term', 'rent_commencement', 'renewal_terms', 'rent_calculation', 'rent_amount', 'payment_terms', 'first_payment_due', 'expiration_date', 'renewal_notice_term', 'lease_prepayment_applicable', 'lease_prepayment_amount', 'removal_timeline_and_expectations', 'fee_simple_owner_applicable', 'rent_escalator_applicable', 'rent_escalator_amount', 'rent_escalator_effective_date', 'coterminus_ppa_applicable', 'lessee_termination', 'lessor_termination', 'termination_notice_requirements', 'default', 'lessee_assignment', 'lessor_assignment', 'removal_requirements', 'access_rights', 'quiet_enjoyment', 'non_disturbance_requirements', 'snda', 'eminent_domain', 'force_majeure', 'property_tax', 'purchase_options_available', 'liens', 'amendments_assignments_estoppels', 'prevailing_party_provision_applicable', 'governing_law', 'interconnection_utility_company', 'interconnection_customer', 'term', 'nameplate_capacity_limits', 'mechanical_completion_date', 'commercial_operation_date', 'interconnect_date_deadline', 'amendments_assignments', 'provider_default', 'customer_default', 'disconnection_terms', 'nameplate_capacity_size', 'customer_assignment', 'provider_assignment', 'customer_termination', 'provider_termination', 'insurance_requirements', 'taxes', 'economic_terms_summary', 'interconnection_cost_responsibility', 'system_upgrades_cost_responsibility', 'prevailing_party_provision', 'responsible_party_metering', 'recurring_monthly_costs', 'warranty', 'other_dates_referenced', 'offtaker', 'provider', 'ppa_rate', 'ppa_end_date', 'commercial_operation_date_definition', 'buyout_option', 'buyout_amount', 'nameplate_capacity', 'projected_production', 'degradation_amount', 'production_guarantee', 'metering_adjustment', 'ppa_rate_table', 'offtaker_default', 'ppa_provider_default', 'offtaker_termination', 'ppa_provider_termination', 'offtaker_assignment', 'ppa_provider_assignment', 'amendments_estoppels', 'tax_responsibilities', 'workflow_questions', 'lease_coterminus', 'customer', 'commencement_date', 'utility_company', 'renewal', 'maintenance_service_fee', 'escalator', 'services_warranty_terms', 'year_one_production', 'production_guarantee_term', 'production_estimate_definition', 'degradation', 'production_factor', 'adjustments_production_loss', 'guarantee_statement', 'production_shortfall_rate', 'guarantee_limitations', 'proactive_reactive_reporting', 'om_customer_termination', 'termination_maximum_liability', 'om_customer_default', 'om_customer_assignment', 'prevailing_party', 'ppa_net_energy_rate', 'scope_and_services', 'noncovered_service_rate_schedule', 'owner', 'epc_contractor_name', 'system_size', 'address', 'construction_status', 'mechanical_completion_definition', 'substantial_completion_definition', 'final_completion_definition', 'substantial_completion_within_mechanical_completion', 'substantial_completion_date', 'liquidated_damages_depends_on_substantial_completion', 'final_completion_date', 'owner_default', 'contractor_default', 'owner_termination', 'contractor_termination', 'warranties', 'guaranties', 'owner_assignment', 'contractor_assignment', 'mechanical_completion_rea_notification', 'mechanical_completion_review_period', 'mechanical_completion_acceptance', 'mechanical_completion_rejection', 'substantial_completion_rea_notification', 'substantial_completion_review_period', 'substantial_completion_acceptance', 'substantial_completion_rejection', 'final_completion_rea_notification', 'final_completion_review_period', 'final_completion_acceptance', 'final_completion_rejection', 'pre_contract_payment', 'lntp', 'lntp2', 'notice_to_proceed', 'site_preparation_completion', 'racking_delivery', 'modules_delivery', 'inverters_delivery', 'racking_installation', 'modules_installation', 'inverters_installation', 'mechanical_completion', 'witness_test', 'pto', 'pv_substantial_completion', 'ess_substantial_completion', 'final_completion', name='documentkeys').drop(op.get_bind())
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    sa.Enum('landlord_name', 'tenant_name', 'effective_date', 'property_size', 'initial_term', 'rent_commencement', 'renewal_terms', 'rent_calculation', 'rent_amount', 'payment_terms', 'first_payment_due', 'expiration_date', 'renewal_notice_term', 'lease_prepayment_applicable', 'lease_prepayment_amount', 'removal_timeline_and_expectations', 'fee_simple_owner_applicable', 'rent_escalator_applicable', 'rent_escalator_amount', 'rent_escalator_effective_date', 'coterminus_ppa_applicable', 'lessee_termination', 'lessor_termination', 'termination_notice_requirements', 'default', 'lessee_assignment', 'lessor_assignment', 'removal_requirements', 'access_rights', 'quiet_enjoyment', 'non_disturbance_requirements', 'snda', 'eminent_domain', 'force_majeure', 'property_tax', 'purchase_options_available', 'liens', 'amendments_assignments_estoppels', 'prevailing_party_provision_applicable', 'governing_law', 'interconnection_utility_company', 'interconnection_customer', 'term', 'nameplate_capacity_limits', 'mechanical_completion_date', 'commercial_operation_date', 'interconnect_date_deadline', 'amendments_assignments', 'provider_default', 'customer_default', 'disconnection_terms', 'nameplate_capacity_size', 'customer_assignment', 'provider_assignment', 'customer_termination', 'provider_termination', 'insurance_requirements', 'taxes', 'economic_terms_summary', 'interconnection_cost_responsibility', 'system_upgrades_cost_responsibility', 'prevailing_party_provision', 'responsible_party_metering', 'recurring_monthly_costs', 'warranty', 'other_dates_referenced', 'offtaker', 'provider', 'ppa_rate', 'ppa_end_date', 'commercial_operation_date_definition', 'buyout_option', 'buyout_amount', 'nameplate_capacity', 'projected_production', 'degradation_amount', 'production_guarantee', 'metering_adjustment', 'ppa_rate_table', 'offtaker_default', 'ppa_provider_default', 'offtaker_termination', 'ppa_provider_termination', 'offtaker_assignment', 'ppa_provider_assignment', 'amendments_estoppels', 'tax_responsibilities', 'workflow_questions', 'lease_coterminus', 'customer', 'commencement_date', 'utility_company', 'renewal', 'maintenance_service_fee', 'escalator', 'services_warranty_terms', 'year_one_production', 'production_guarantee_term', 'production_estimate_definition', 'degradation', 'production_factor', 'adjustments_production_loss', 'guarantee_statement', 'production_shortfall_rate', 'guarantee_limitations', 'proactive_reactive_reporting', 'om_customer_termination', 'termination_maximum_liability', 'om_customer_default', 'om_customer_assignment', 'prevailing_party', 'ppa_net_energy_rate', 'scope_and_services', 'noncovered_service_rate_schedule', 'owner', 'epc_contractor_name', 'system_size', 'address', 'construction_status', 'mechanical_completion_definition', 'substantial_completion_definition', 'final_completion_definition', 'substantial_completion_within_mechanical_completion', 'substantial_completion_date', 'liquidated_damages_depends_on_substantial_completion', 'final_completion_date', 'owner_default', 'contractor_default', 'owner_termination', 'contractor_termination', 'warranties', 'guaranties', 'owner_assignment', 'contractor_assignment', 'mechanical_completion_rea_notification', 'mechanical_completion_review_period', 'mechanical_completion_acceptance', 'mechanical_completion_rejection', 'substantial_completion_rea_notification', 'substantial_completion_review_period', 'substantial_completion_acceptance', 'substantial_completion_rejection', 'final_completion_rea_notification', 'final_completion_review_period', 'final_completion_acceptance', 'final_completion_rejection', 'pre_contract_payment', 'lntp', 'lntp2', 'notice_to_proceed', 'site_preparation_completion', 'racking_delivery', 'modules_delivery', 'inverters_delivery', 'racking_installation', 'modules_installation', 'inverters_installation', 'mechanical_completion', 'witness_test', 'pto', 'pv_substantial_completion', 'ess_substantial_completion', 'final_completion', name='documentkeys').create(op.get_bind())
    # transform string values to the enum key representation
    document_key_crud = DocumentKeyCRUD(db_session=sa.orm.Session(bind=op.get_bind()))
    for document_key in document_key_crud.get(skip_pagination=True):
        document_key_crud.update_by_id(document_key.id, {"name": get_key_by_value(document_key.name)})
    op.alter_column('document_keys', 'name',
               existing_type=sa.String(),
               type_=postgresql.ENUM('landlord_name', 'tenant_name', 'effective_date', 'property_size', 'initial_term', 'rent_commencement', 'renewal_terms', 'rent_calculation', 'rent_amount', 'payment_terms', 'first_payment_due', 'expiration_date', 'renewal_notice_term', 'lease_prepayment_applicable', 'lease_prepayment_amount', 'removal_timeline_and_expectations', 'fee_simple_owner_applicable', 'rent_escalator_applicable', 'rent_escalator_amount', 'rent_escalator_effective_date', 'coterminus_ppa_applicable', 'lessee_termination', 'lessor_termination', 'termination_notice_requirements', 'default', 'lessee_assignment', 'lessor_assignment', 'removal_requirements', 'access_rights', 'quiet_enjoyment', 'non_disturbance_requirements', 'snda', 'eminent_domain', 'force_majeure', 'property_tax', 'purchase_options_available', 'liens', 'amendments_assignments_estoppels', 'prevailing_party_provision_applicable', 'governing_law', 'interconnection_utility_company', 'interconnection_customer', 'term', 'nameplate_capacity_limits', 'mechanical_completion_date', 'commercial_operation_date', 'interconnect_date_deadline', 'amendments_assignments', 'provider_default', 'customer_default', 'disconnection_terms', 'nameplate_capacity_size', 'customer_assignment', 'provider_assignment', 'customer_termination', 'provider_termination', 'insurance_requirements', 'taxes', 'economic_terms_summary', 'interconnection_cost_responsibility', 'system_upgrades_cost_responsibility', 'prevailing_party_provision', 'responsible_party_metering', 'recurring_monthly_costs', 'warranty', 'other_dates_referenced', 'offtaker', 'provider', 'ppa_rate', 'ppa_end_date', 'commercial_operation_date_definition', 'buyout_option', 'buyout_amount', 'nameplate_capacity', 'projected_production', 'degradation_amount', 'production_guarantee', 'metering_adjustment', 'ppa_rate_table', 'offtaker_default', 'ppa_provider_default', 'offtaker_termination', 'ppa_provider_termination', 'offtaker_assignment', 'ppa_provider_assignment', 'amendments_estoppels', 'tax_responsibilities', 'workflow_questions', 'lease_coterminus', 'customer', 'commencement_date', 'utility_company', 'renewal', 'maintenance_service_fee', 'escalator', 'services_warranty_terms', 'year_one_production', 'production_guarantee_term', 'production_estimate_definition', 'degradation', 'production_factor', 'adjustments_production_loss', 'guarantee_statement', 'production_shortfall_rate', 'guarantee_limitations', 'proactive_reactive_reporting', 'om_customer_termination', 'termination_maximum_liability', 'om_customer_default', 'om_customer_assignment', 'prevailing_party', 'ppa_net_energy_rate', 'scope_and_services', 'noncovered_service_rate_schedule', 'owner', 'epc_contractor_name', 'system_size', 'address', 'construction_status', 'mechanical_completion_definition', 'substantial_completion_definition', 'final_completion_definition', 'substantial_completion_within_mechanical_completion', 'substantial_completion_date', 'liquidated_damages_depends_on_substantial_completion', 'final_completion_date', 'owner_default', 'contractor_default', 'owner_termination', 'contractor_termination', 'warranties', 'guaranties', 'owner_assignment', 'contractor_assignment', 'mechanical_completion_rea_notification', 'mechanical_completion_review_period', 'mechanical_completion_acceptance', 'mechanical_completion_rejection', 'substantial_completion_rea_notification', 'substantial_completion_review_period', 'substantial_completion_acceptance', 'substantial_completion_rejection', 'final_completion_rea_notification', 'final_completion_review_period', 'final_completion_acceptance', 'final_completion_rejection', 'pre_contract_payment', 'lntp', 'lntp2', 'notice_to_proceed', 'site_preparation_completion', 'racking_delivery', 'modules_delivery', 'inverters_delivery', 'racking_installation', 'modules_installation', 'inverters_installation', 'mechanical_completion', 'witness_test', 'pto', 'pv_substantial_completion', 'ess_substantial_completion', 'final_completion', name='documentkeys'),
               nullable=True,
               postgresql_using='name::documentkeys')
    # ### end Alembic commands ###
