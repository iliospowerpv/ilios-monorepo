"""
File from Back-End to store all possible site documents and sections.
"""

import enum


class DocumentSections(enum.Enum):
    """
    All possible site documents sections.
    By adding/removing sections also update sub section mapper in
    app/helpers/due_diligence/document_section_mapper.py
    """

    # Top level sections
    executive_summary = "Executive Summary"
    preview = "Preview"
    organization_overview = "Organizational Overview"
    stage1 = "Stage-1"
    stage2 = "Stage-2"
    stage3 = "Stage-3"
    # Stage-1
    site_stage1 = "Site Stage-1"
    offtaker_stage1 = "Offtaker Stage-1"
    projectco_lessor = "ProjectCo (Lessor)"
    projectco_lessor_owner = "ProjectCo (Lessor) Owner"
    projectco_lessor_owner_jv_member_1 = "ProjectCo (Lessor) Owner JV Member 1"
    projectco_lessor_owner_jv_member_2 = "ProjectCo (Lessor) Owner JV Member 2"
    projectco_lessor_owner_jv_member_3 = "ProjectCo (Lessor) Owner JV Member 3"
    projectco_lessor_parent = "ProjectCo (Lessor) Parent"
    managing_member_of_lessee_holdco_sponsor_parent = (
        "Managing Member of Lessee HoldCo (Sponsor) & Parent"
    )
    guarantor_managing_member_of_lessee_holdco_sponsor_parent = (
        "Guarantor (Managing Member of Lessee HoldCo (Sponsor & Parent))"
    )
    guarantor_2_managing_member_of_lessee_holdco_sponsor_parent = (
        "Guarantor 2  (Managing Member of Lessee HoldCo (Sponsor & Parent))"
    )
    guarantor_3_managing_member_of_lessee_holdco_sponsor_parent = (
        "Guarantor 3  (Managing Member of Lessee HoldCo (Sponsor & Parent))"
    )
    lessee_holdco = "Lessee HoldCo"
    tax_credit_fund = "Tax Credit Fund"
    incentives_stage1 = "Incentives Stage-1"
    construction_documents_stage1 = "Construction Documents Stage-1"
    utility_operational_documents_stage1 = "Utility/Operational Documents Stage-1"
    insurance_property_tax_stage1 = "Insurance & Property Tax Stage-1"
    project_financing_stage1 = "Project Financing Stage-1"
    grandfathering_stage1 = "Grandfathering Stage-1"
    closing_matters_stage1 = "Closing Matters Stage-1"
    tax_equity_funding_stage1 = "Tax Equity Funding Stage-1"
    # Stage-2
    site_stage2 = "Site Stage-2"
    mechanical_completion_stage2 = "Mechanical Completion Stage-2"
    utility_operational_documents_stage2 = "Utility/Operational Documents Stage-2"
    project_financing_stage2 = "Project Financing Stage-2"
    substantial_completion_stage2 = "Substantial Completion Stage-2"
    tax_equity_funding_stage2 = "Tax Equity Funding Stage-2"
    # Stage-3
    construction_documents_stage3 = "Construction Documents Stage-3"
    tax_equity_funding_stage3 = "Tax Equity Funding Stage-3"


class SiteDocumentsEnum(enum.Enum):
    """
    All possible site documents.
    By adding/removing documents also update document section mapper in
    app/helpers/due_diligence/document_section_mapper.py
    """

    # Executive summary
    executive_summary = "Executive Summary"
    # Preview
    financial_model = "Financial Model"
    preliminary_ie_review_for_model = "Preliminary IE Review for Model"
    preliminary_drawings_for_model_electronics = (
        "Preliminary Drawings for Model - Electrical"
    )
    preliminary_drawings_for_model_civil = "Preliminary Drawings for Model - Civil"
    seller_initial_pv_syst_full_data_package_for_model = (
        "PV Syst - Initial Package for Modeling - Seller"
    )
    cra_community_reinvestment_act = "CRA (Community Reinvestment Act)"
    nmtc_new_market_tax_credit = "NMTC (New Market Tax Credit)"
    fema_disaster_declaration_yn = "FEMA (Disaster Declaration Y/N)"
    esg_statement_enviromental_social_governance = (
        "ESG Statement (Environmental, Social & Governance)"
    )
    epa_greenhouse_gas_equivalencies_calculator = (
        "EPA Greenhouse Gas Equivalencies Calculator"
    )
    usda_reap = "USDA / REAP"
    ferc_556 = "FERC 556"
    project_preview = "Project Preview"
    # Organizational Overview
    org_chart_before_after_investment = "Org Chart (Before & After Investment)"
    # Site Stage-1
    site_lease = "Site Lease"
    formal_notice_of_commencement_of_lease = "Formal Notice of Commencement of Lease"
    title_report_title_commitment = "Title Report / Title Commitment"
    documents_evidencing_title_exceptions = "Documents Evidencing Title Exceptions"
    sndas_lien_releases_and_waivers = "SNDAs, Lien Releases, and Waivers"
    leasehold_area_metes_and_bounds_legal_description = (
        "Leasehold Area Metes and Bounds Legal Description"
    )
    purchase_option = "Purchase Option"
    evidence_of_application_for_municipal_permits = (
        "Evidence of Application for Municipal Permits"
    )
    zoning_approval_conditional_use_permit = "Zoning Approval / Conditional Use Permit"
    phase_1_esa = "Phase 1 ESA"
    phase_2_esa = "Phase 2 ESA"
    environmental_reports = "Environmental Reports"
    air = "Air"
    construction_stormwater = "Construction Stormwater"
    construction_demolition_debris = "Construction & Demolition Debris"
    endangered_species = "Endangered Species"
    wetlands = "Wetlands"
    usfws_concurrence_letter_re_protected_species = (
        "USFWS Concurrence Letter "
        "re. protected species, & any "
        "associated correspondence"
    )
    site_assessment = "Site Assessment"
    geotechnical_report = "GeoTechnical Report"
    alta_survey = "ALTA Survey"
    faa_obstruction_evaluation_airport_airspace_analysis = (
        "FAA Obstruction Evaluation / Airport Airspace Analysis"
    )
    assignment_of_site_lease_to_projectco_lessor = (
        "Assignment of Site Lease to ProjectCo (Lessor)"
    )
    recorded_memorandum_of_site_lease_assignments = (
        "Recorded Memorandum of Site Lease & Assignments"
    )
    site_lease_estoppel_for_benefit_of_investor = (
        "Site Lease Estoppel for Benefit of Investor"
    )
    phase_1_esa_reliance_letter_addressed_to_the_tax_credit_fund = (
        "Phase 1 ESA Reliance Letter addressed to the Tax Credit Fund"
    )
    pro_forma_title_policy = "Pro Forma Title Policy"
    ida_industrial_development_authority = "IDA (Industrial Development Authority)"
    # Offtaker Stage-1
    offtaker = "Offtaker"
    proof_of_legal_name = "Proof of Legal Name"
    _12_months_of_utility_bills = "12 months of Utility Bills"
    # common - financials_and_tax_returns_3_years
    bond_rating_or_other_third_party_financial_review = (
        "Bond Rating or other Third Party Financial Review"
    )
    ppa_and_amendments = "PPA - Power Purchase Agreement"
    # common - incumbency_certificate_resolutions_proof_of_authority
    assignment_of_ppa_to_projectco = "Assignment of PPA to ProjectCo"
    ppa_estoppel = "PPA Estoppel"
    # ProjectCo (Lessor)
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - operating_agreements_including_all_amendments_pre_tax_equity
    proof_of_projectco_ownership = "Proof of ProjectCo Ownership"
    financial_projections_project_life = "Financial Projections (Project Life)"
    # common - certificate_of_good_standing
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - amended_restated_operating_agreement_post_tax_equity
    # common - certificate_of_good_standing
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    ucc_terminations = "UCC Terminations"
    # ProjectCo (Lessor) Owner
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - financials_and_tax_returns_3_years
    # common - operating_agreement_including_all_amendments
    proof_of_projectco_ownership_amipa_acquisition_mipa = (
        "Proof of ProjectCo Ownership (AMIPA Acquisition MIPA)"
    )
    # common - certificate_of_good_standing
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # ProjectCo (Lessor) Owner JV Member 1
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - financials_and_tax_returns_3_years
    # common - operating_agreement_including_all_amendments
    # common - certificate_of_good_standing = "Certificate of Good Standing"
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # ProjectCo (Lessor) Owner JV Member 2
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - financials_and_tax_returns_3_years
    # common - operating_agreement_including_all_amendments
    # common - certificate_of_good_standing = "Certificate of Good Standing"
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # ProjectCo (Lessor) Owner JV Member 3
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - financials_and_tax_returns_3_years
    # common - operating_agreement_including_all_amendments
    # common - certificate_of_good_standing = "Certificate of Good Standing"
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # ProjectCo (Lessor) Parent
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - operating_agreements_including_all_amendments
    proof_of_projectco_ownership_pmipa_parent_mipa = (
        "Proof of ProjectCo Ownership (PMIPA Parent MIPA)"
    )
    # common - certificate_of_good_standing = "Certificate of Good Standing"
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    deliverables_at_closing = "Deliverables at Closing"
    assignment_of_membership_interests = "Assignment of Membership Interests"
    member_officer_resignations = "Member/Officer Resignations"
    seller_certificate_per_3bv = "Seller Certificate per 3(b)(v)"
    firpta = "FIRPTA"
    # Managing Member of Lessee HoldCo (Sponsor) & Parent
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - financials_and_tax_returns_3_years
    # common - operating_agreement_including_all_amendments
    # common - certificate_of_good_standing = "Certificate of Good Standing"
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # Guarantor (Managing Member of Lessee HoldCo (Sponsor & Parent))
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - financials_and_tax_returns_3_years
    # common - operating_agreement_including_all_amendments
    # common - certificate_of_good_standing = "Certificate of Good Standing"
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # Guarantor 2  (Managing Member of Lessee HoldCo (Sponsor & Parent))
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - financials_and_tax_returns_3_years
    # common - operating_agreement_including_all_amendments
    # common - certificate_of_good_standing = "Certificate of Good Standing"
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # Guarantor 3  (Managing Member of Lessee HoldCo (Sponsor & Parent))
    # common - statement_of_qualifications
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    # common - financials_and_tax_returns_3_years
    # common - operating_agreement_including_all_amendments
    # common - certificate_of_good_standing = "Certificate of Good Standing"
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # Lessee HoldCo
    # common - articles_of_organization
    # common - employer_identification_number_w9_or_irs_letter
    original_operating_agreement_including_all_amendments = (
        "Original Operating Agreement Including All Amendments"
    )
    mipa_to_lessee_holdco_mmipa_master_tenant_mipa = (
        "MIPA to Lessee HoldCo (MMIPA Master Tenant MIPA)"
    )
    mipa_assignment_agreement = "MIPA Assignment Agreement"
    date_of_investor_closing = "Date of Investor Closing"
    # common - ucc_tax_bankruptcy_judgment_and_pending_litigation_searches
    # common - incumbency_certificate_resolutions_proof_of_authority
    # common - certificate_of_good_standing
    # common - amended_restated_operating_agreement_post_tax_equity
    enforceability_opinion = "Enforce-ability Opinion"
    # Tax Credit Fund
    # common -articles_of_organization
    # common -employer_identification_number_w9_or_irs_letter
    # common - certificate_of_good_standing
    # Incentives Stage-1
    srec_approval = "SREC Approval"
    srec_contracts_or_proof_of_ability_to_merchandise = (
        "SREC Contracts or Proof of Ability to Merchandise"
    )
    production_based_incentive_pbi_approval = (
        "Production Based Incentive (PBI) Approval"
    )
    nyserda_grant = "NYSERDA Grant"
    nyserda_grant_status_portal_screen_shot_due_date = (
        "NYSERDA Grant Status (Portal Screen Shot & Due Date)"
    )
    nysdam_noi_final_determination = "NYSDAM NOI Final Determination"
    community_solar_program_participation = "Community Solar Program Participation"
    # Construction Documents Stage-1
    epc_agreement = "Engineering, Procurement, Construction (EPC) Agreement"
    full_notice_to_proceed = "Full Notice to Proceed"
    assignment_of_warranties = "Assignment of Warranties"
    epc_production_guaranty = "EPC Production Guaranty"
    ifc_issued_for_construction_pv_syst_first_buyer_pv_syst_report = (
        "PV Syst - Issued for Construction (IFC) - First Buyer Report"
    )
    ifc_issued_for_construction_stamped_project_drawings = (
        "IFC (Issued for Construction) Stamped Project Drawings"
    )
    project_schedule = "Project Schedule"
    current_progress_report_construction_complete = (
        "Current Progress Report / Construction % Complete"
    )
    epc_permit_studies_letter = "EPC Permit & Studies Letter"
    local_building_permits_electrical_construction_etc = (
        "Local Building Permits (electrical, construction, etc.)"
    )
    electrical_permit = "Electrical Permit"
    application_for_electrical_permit = "Application for Electrical Permit"
    building_permit = "Building Permit"
    application_for_building_permit = "Application for Building Permit"
    encroachment_driveway_access_permit = "Encroachment / Driveway Access Permit"
    application_for_encroachment_driveway_access_permit = (
        "Application for Encroachment / Driveway Access Permit"
    )
    project_budget_and_draws_requests = "Project Budget and Draws Requests"
    projectco_invoices = "ProjectCo Invoices"
    draw_1 = "Draw #1"
    draw_2 = "Draw #2"
    draw_3 = "Draw #3"
    draw_4 = "Draw #4"
    draw_5 = "Draw #5"
    draw_6 = "Draw #6"
    draw_7 = "Draw #7"
    draw_8 = "Draw #8"
    draw_9 = "Draw #9"
    draw_10 = "Draw #10"
    draw_11 = "Draw #11"
    draw_12 = "Draw #12"
    draw_13 = "Draw #13"
    draw_14 = "Draw #14"
    draw_15 = "Draw #15"
    draw_16 = "Draw #16"
    draw_17 = "Draw #17"
    draw_18 = "Draw #18"
    draw_19 = "Draw #19"
    draw_20 = "Draw #20"
    construction_lien_releases = "Construction Lien Releases"
    change_order_requests = "Change Order Requests"
    monitoring_system_and_das = "Monitoring System and DAS"
    ofe_owner_furnished_equipment_proof_of_procurement = (
        "OFE (Owner Furnished Equipment) Proof of Procurement"
    )
    module_specs = "Module Specs"
    module_warranty = "Module Warranty"
    module_warranty_backup_documents = "Module Warranty Backup Documents"
    racking_specs = "Racking Specs"
    racking_warranty = "Racking Warranty"
    fully_executed_racking_warranty = "Fully Executed Racking Warranty"
    racking_warranty_backup_documents = "Racking Warranty Backup Documents"
    inverter_specs = "Inverter Specs"
    inverter_warranty = "Inverter Warranty"
    inverter_warranty_backup_documents = "Inverter Warranty Backup Documents"
    transformer_specs = "Transformer Specs"
    transformer_warranty = "Transformer Warranty"
    transformer_warranty_backup_documents = "Transformer Warranty Backup Documents"
    storage_specs = "Storage Specs"
    battery_specs = "Battery Specs"
    storage_warranty = "Storage Warranty"
    storage_warranty_backup_documents = "Storage Warranty Backup Documents"
    battery_warranty = "Battery Warranty"
    battery_warranty_backup_documents = "Battery Warranty Backup Documents"
    # Utility/Operational Documents Stage-1
    net_metering_interconnection_application = (
        "Net Metering / Interconnection Application"
    )
    om_agreement = "Operations and Maintenance (O&M) & Production Guarantee Agreement"
    subscriber_management_agreement = "Subscriber Management Agreement"
    interconnection_agreement_and_amendments = (
        "Interconnection Agreement and Amendments"
    )
    interconnection_25 = "Interconnection 25%"
    interconnection_75 = "Interconnection 75%"
    assignment_of_interconnection_agreement_and_amendments = (
        "Assignment of Interconnection Agreement and Amendments"
    )
    utility_approval_interconnection_agreement_and_amendments = (
        "Utility Approval of Assignment of Interconnection Agreement and Amendments"
    )
    i39_approval = "i39 Approval"
    cesir = "CESIR"
    evidence_of_initial_payment = "Evidence of Initial Payment"
    nyseg_25_payment = "NYSEG 25% Payment"
    nyseg_75_payment = "NYSEG 75% Payment"
    nyseg_100_payment = "NYSEG 100% Payment"
    servicing_agreement = "Servicing Agreement"
    servicers_statement_of_qualifications_etc = (
        "Servicer's Statement of Qualifications etc."
    )
    # Insurance & Property Tax Stage-1
    property_tax_agreements = "Property Tax Agreements"
    epcs_insurance_liability_builders_risk = (
        "EPC’s Insurance (Liability & Builders Risk)"
    )
    real_estate_ownerslandlords_insurance_liability = (
        "Real Estate Owner's/Landlord's Insurance (Liability)"
    )
    projectcos_liability_insurance = "Projectco’s Liability Insurance"
    projectcos_property_insurance = "Projectco’s Property Insurance"
    projectcos_business_interruption_insurance = (
        "Projectco's Business Interruption Insurance"
    )
    insurance_companies_are_a_rated_or_better = (
        "Insurance Companies are A rated or better"
    )
    om_insurance = "O&M Insurance"
    decommissioning_bonds = "Decommissioning Bonds"
    # Project Financing Stage-1
    construction_loan_security_agreement = "Construction Loan Security Agreement"
    # common - loan_maturity_date
    construction_prom_note = "Construction Prom Note"
    construction_loan_guaranty = "Construction Loan Guaranty"
    pledge_agreement = "Pledge Agreement"
    consent_to_assignment_of_offtaker = "Consent to Assignment of Offtaker"
    consent_to_assignment_of_epc = "Consent to Assignment of EPC"
    ucc_financing_statements_for_construction_loan = (
        "UCC Financing Statements for Construction Loan"
    )
    usda_pre_cert_checklist = "USDA Pre-Cert Checklist"
    preappraisal_data_check = "Pre-Appraisal Data Check"
    project_appraisal = "Project Appraisal"
    # Grandfathering Stage-1
    proof_of_start_of_construction = "Proof of Start of Construction"
    # Closing Matters Stage-1
    flow_of_funds = "Flow of Funds"
    sources_and_uses = "Sources and Uses"
    payoff_letters = "Payoff Letters"
    third_party_invoices_acct_legal_etc = "Third Party Invoices (Acct, Legal, etc.)"
    wire_instructions = "Wire Instructions"
    opinions = "Opinions"
    # Tax Equity Funding Stage-1
    _20_funding = "20% Funding"
    # Site Stage-2
    asbuilt_alta_survey = "As-Built ALTA Survey"
    final_title_policy = "Final Title Policy"
    # Mechanical Completion Stage-2
    epc_mechanical_completion_reportcertificate = (
        "EPC Mechanical Completion Report/Certificate"
    )
    # common - independent_engineer_report
    utilitycity_mechanical_completion_tests = "Utility/City Mechanical Completion Tests"
    # Utility/Operational Documents Stage-2
    permission_to_operate_pto = "Permission to Operate (PTO)"
    commercial_operation_date_cod = "Commercial Operation Date (COD)"
    # Project Financing Stage-2
    ucc3_release_or_termination = "UCC3 Release or Termination"
    term_sheet_for_permanent_financing = "Term Sheet for Permanent Financing"
    permanent_loan_security_agreement = "Permanent Loan Security Agreement"
    # common - loan_maturity_date
    permanent_promissory_note = "Permanent Promissory Note"
    permanent_loan_guaranty = "Permanent Loan Guaranty"
    consent_to_assignment_of_om = "Consent to Assignment of O&M"
    ucc_financing_statements_for_permanent_loan = (
        "UCC Financing Statements for Permanent Loan"
    )
    forbearance_agreement = "Forbearance Agreement"
    # Substantial Completion Stage-2
    as_built_pv_syst_with_full_data_package = "PV Syst - As Built - Second Buyer Report"
    seller_acceptance_of_second_buyer_pv_syst_report = (
        "Seller Acceptance of Second Buyer PV Syst Report"
    )
    seller_independent_pv_syst_report = "PV Syst - Independent Report - Seller"
    final_pv_syst_reports_average = "Final PV Syst Reports Average"
    as_built_project_drawings = "As Built Project Drawings"
    epc_substantial_completion_report_certificate = (
        "EPC Substantial Completion Report/Certificate"
    )
    # common - independent_engineer_report
    placed_in_service_pis_letter = "Placed in Service (PIS) Letter"
    final_construction_lien_releases = "Final Construction Lien Releases"
    # Tax Equity Funding Stage-2
    _70_funding = "70% Funding"
    # Construction Documents Stage-3
    epc_final_completion_acceptance_report_certificate = (
        "EPC Final Completion/Acceptance Report/Certificate"
    )
    epc_closeout_documents = "EPC Closeout Documents"
    third_party_review_final_acceptance = "3rd Party Review - Final Acceptance"
    final_completion_acceptance = "Final Completion/Acceptance"
    photos_of_completed_project = "Photos of Completed Project"
    # Tax Equity Funding Stage-3
    _10_k1 = "10% K1"
    # Common documents for multiple sections
    financials_and_tax_returns_3_years = "Financials and Tax Returns (3 years)"
    incumbency_certificate_resolutions_proof_of_authority = (
        "Incumbency Certificate & Resolutions (Proof of Authority)"
    )
    articles_of_organization = "Articles of Organization"
    employer_identification_number_w9_or_irs_letter = (
        "Employer Identification Number (W-9 or IRS Letter)"
    )
    certificate_of_good_standing = "Certificate of Good Standing"
    ucc_tax_bankruptcy_judgment_and_pending_litigation_searches = (
        "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"
    )
    statement_of_qualifications = "Statement of Qualifications"
    operating_agreement_including_all_amendments = (
        "Operating Agreement Including All Amendments"
    )
    amended_restated_operating_agreement_post_tax_equity = (
        "Operating Agreement, Amended & Restated (Post Tax Equity)"
    )
    guaranty_agreement = "Guaranty Agreement"
    loan_maturity_date = "Loan Maturity Date"
    independent_engineer_report = "Independent Engineer Report"
    operating_agreements_including_all_amendments_pre_tax_equity = (
        "Operating Agreement Including All Amendments (Pre-Tax Equity)"
    )
