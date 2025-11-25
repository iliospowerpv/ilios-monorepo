from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

EXECUTIVE_SUMMARY_SECTION_NAME = "Executive Summary"
EXPECTED_DOCUMENTS_RESPONSE = [
    {
        "name": EXECUTIVE_SUMMARY_SECTION_NAME,
        "documents_count": 1,
        "completed_tasks_percentage": 0,
        "documents": [
            {
                "name": "Executive Summary",
                "files_count": 0,
                "status": "To Upload",
                "assignee": None,
                "ai_supported": False,
            }
        ],
        "related_sections": [],
    },
    {
        "name": "Preview",
        "documents_count": 5,
        "completed_tasks_percentage": 0,
        "documents": [
            {"name": "Site Lease", "files_count": 0, "status": "To Upload", "assignee": None, "ai_supported": True},
            {
                "name": "Interconnection Agreement and Amendments",
                "files_count": 0,
                "status": "To Upload",
                "assignee": None,
                "ai_supported": True,
            },
            {
                "name": "Operations and Maintenance (O&M) & Production Guarantee Agreement",
                "files_count": 0,
                "status": "To Upload",
                "assignee": None,
                "ai_supported": True,
            },
            {
                "name": "Engineering, Procurement, Construction (EPC) Agreement",
                "files_count": 0,
                "status": "To Upload",
                "assignee": None,
                "ai_supported": True,
            },
            {
                "name": "PPA - Power Purchase Agreement",
                "files_count": 0,
                "status": "To Upload",
                "assignee": None,
                "ai_supported": True,
            },
        ],
        "related_sections": [],
    },
]

CREATE_DOCUMENT_PAYLOAD = {
    "description": "",
    "name": SiteDocumentsEnum.executive_summary.value,
}

INVALID_SECTION_NAME_ERROR_MSG = "Validation error: body.section_name - Input should be 'Executive Summary' or 'Preview'"

INVALID_SECTION_DOCUMENT_NAME_ERROR_MSG = (
    "There is no 'Flow of Funds' documents in 'Executive Summary' document section. Input should be one of: "
    "'Executive Summary'"
)

INVALID_DOCUMENT_NAME_ERROR_MSG = (
    "Validation error: body.name - Input should be 'Executive Summary', 'Financial Model', "
    "'Preliminary IE Review for Model', 'Preliminary Drawings for Model - Electrical', "
    "'Preliminary Drawings for Model - Civil', 'PV Syst - Initial Package for Modeling - Seller', "
    "'CRA (Community Reinvestment Act)', 'NMTC (New Market Tax Credit)', 'FEMA (Disaster Declaration Y/N)', "
    "'ESG Statement (Environmental, Social & Governance)', 'EPA Greenhouse Gas Equivalencies Calculator', "
    "'USDA / REAP', 'FERC 556', 'Project Preview', 'Org Chart (Before & After Investment)', 'Site Lease', "
    "'Formal Notice of Commencement of Lease', 'Title Report / Title Commitment', "
    "'Documents Evidencing Title Exceptions', 'SNDAs, Lien Releases, and Waivers', "
    "'Leasehold Area Metes and Bounds Legal Description', 'Purchase Option', "
    "'Evidence of Application for Municipal Permits', 'Zoning Approval / Conditional Use Permit', 'Phase 1 ESA', "
    "'Phase 2 ESA', 'Environmental Reports', 'Air', 'Construction Stormwater', 'Construction & Demolition Debris', "
    "'Endangered Species', 'Wetlands', 'USFWS Concurrence Letter re. protected species, & any associated correspondence'"
    ", 'Site Assessment', 'GeoTechnical Report', 'ALTA Survey', 'FAA Obstruction Evaluation / Airport Airspace Analysis'"
    ", 'Assignment of Site Lease to ProjectCo (Lessor)', 'Recorded Memorandum of Site Lease & Assignments', "
    "'Site Lease Estoppel for Benefit of Investor', 'Phase 1 ESA Reliance Letter addressed to the Tax Credit Fund', "
    "'Pro Forma Title Policy', 'IDA (Industrial Development Authority)', 'Offtaker', 'Proof of Legal Name', "
    "'12 months of Utility Bills', 'Bond Rating or other Third Party Financial Review', 'PPA - Power Purchase Agreement', "
    "'Assignment of PPA to ProjectCo', 'PPA Estoppel', 'Proof of ProjectCo Ownership', "
    "'Financial Projections (Project Life)', 'UCC Terminations', 'Proof of ProjectCo Ownership (AMIPA Acquisition MIPA)'"
    ", 'Proof of ProjectCo Ownership (PMIPA Parent MIPA)', 'Deliverables at Closing', "
    "'Assignment of Membership Interests', 'Member/Officer Resignations', 'Seller Certificate per 3(b)(v)', 'FIRPTA', "
    "'Original Operating Agreement Including All Amendments', 'MIPA to Lessee HoldCo (MMIPA Master Tenant MIPA)', "
    "'MIPA Assignment Agreement', 'Date of Investor Closing', 'Enforce-ability Opinion', 'SREC Approval', "
    "'SREC Contracts or Proof of Ability to Merchandise', 'Production Based Incentive (PBI) Approval', 'NYSERDA Grant', "
    "'NYSERDA Grant Status (Portal Screen Shot & Due Date)', 'NYSDAM NOI Final Determination', "
    "'Community Solar Program Participation', 'Engineering, Procurement, Construction (EPC) Agreement', 'Full Notice to Proceed', 'Assignment of Warranties', "
    "'EPC Production Guaranty', 'PV Syst - Issued for Construction (IFC) - First Buyer Report', "
    "'IFC (Issued for Construction) Stamped Project Drawings', 'Project Schedule', "
    "'Current Progress Report / Construction % Complete', 'EPC Permit & Studies Letter', "
    "'Local Building Permits (electrical, construction, etc.)', 'Electrical Permit', 'Application for Electrical Permit'"
    ", 'Building Permit', 'Application for Building Permit', 'Encroachment / Driveway Access Permit', "
    "'Application for Encroachment / Driveway Access Permit', 'Project Budget and Draws Requests', 'ProjectCo Invoices'"
    ", 'Draw #1', 'Draw #2', 'Draw #3', 'Draw #4', 'Draw #5', 'Draw #6', 'Draw #7', 'Draw #8', 'Draw #9', 'Draw #10', "
    "'Draw #11', 'Draw #12', 'Draw #13', 'Draw #14', 'Draw #15', 'Draw #16', 'Draw #17', 'Draw #18', 'Draw #19', "
    "'Draw #20', 'Construction Lien Releases', 'Change Order Requests', 'Monitoring System and DAS', "
    "'OFE (Owner Furnished Equipment) Proof of Procurement', 'Module Specs', 'Module Warranty', "
    "'Module Warranty Backup Documents', 'Racking Specs', 'Racking Warranty', 'Fully Executed Racking Warranty', "
    "'Racking Warranty Backup Documents', 'Inverter Specs', 'Inverter Warranty', 'Inverter Warranty Backup Documents', "
    "'Transformer Specs', 'Transformer Warranty', 'Transformer Warranty Backup Documents', 'Storage Specs', "
    "'Battery Specs', 'Storage Warranty', 'Storage Warranty Backup Documents', 'Battery Warranty', "
    "'Battery Warranty Backup Documents', 'Net Metering / Interconnection Application', 'Operations and Maintenance (O&M) & Production Guarantee Agreement', "
    "'Subscriber Management Agreement', 'Interconnection Agreement and Amendments', 'Interconnection 25%', "
    "'Interconnection 75%', 'Assignment of Interconnection Agreement and Amendments', "
    "'Utility Approval of Assignment of Interconnection Agreement and Amendments', 'i39 Approval', 'CESIR', "
    "'Evidence of Initial Payment', 'NYSEG 25% Payment', 'NYSEG 75% Payment', 'NYSEG 100% Payment', "
    "'Servicing Agreement', \"Servicer's Statement of Qualifications etc.\", 'Property Tax Agreements', "
    "'EPC’s Insurance (Liability & Builders Risk)', \"Real Estate Owner's/Landlord's Insurance (Liability)\", "
    "'Projectco’s Liability Insurance', 'Projectco’s Property Insurance', "
    "\"Projectco's Business Interruption Insurance\", 'Insurance Companies are A rated or better', 'O&M Insurance', "
    "'Decommissioning Bonds', 'Construction Loan Security Agreement', 'Construction Prom Note', "
    "'Construction Loan Guaranty', 'Pledge Agreement', 'Consent to Assignment of Offtaker', "
    "'Consent to Assignment of EPC', 'UCC Financing Statements for Construction Loan', 'USDA Pre-Cert Checklist', "
    "'Pre-Appraisal Data Check', 'Project Appraisal', 'Proof of Start of Construction', 'Flow of Funds', "
    "'Sources and Uses', 'Payoff Letters', 'Third Party Invoices (Acct, Legal, etc.)', 'Wire Instructions', "
    "'Opinions', '20% Funding', 'As-Built ALTA Survey', 'Final Title Policy', "
    "'EPC Mechanical Completion Report/Certificate', 'Utility/City Mechanical Completion Tests', "
    "'Permission to Operate (PTO)', 'Commercial Operation Date (COD)', 'UCC3 Release or Termination', "
    "'Term Sheet for Permanent Financing', 'Permanent Loan Security Agreement', 'Permanent Promissory Note', "
    "'Permanent Loan Guaranty', 'Consent to Assignment of O&M', 'UCC Financing Statements for Permanent Loan', "
    "'Forbearance Agreement', 'PV Syst - As Built - Second Buyer Report', "
    "'Seller Acceptance of Second Buyer PV Syst Report', 'PV Syst - Independent Report - Seller', "
    "'Final PV Syst Reports Average', 'As Built Project Drawings', 'EPC Substantial Completion Report/Certificate', "
    "'Placed in Service (PIS) Letter', 'Final Construction Lien Releases', '70% Funding', "
    "'EPC Final Completion/Acceptance Report/Certificate', 'EPC Closeout Documents', "
    "'3rd Party Review - Final Acceptance', 'Final Completion/Acceptance', 'Photos of Completed Project', '10% K1', "
    "'Financials and Tax Returns (3 years)', 'Incumbency Certificate & Resolutions (Proof of Authority)', "
    "'Articles of Organization', 'Employer Identification Number (W-9 or IRS Letter)', 'Certificate of Good Standing', "
    "'UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches', 'Statement of Qualifications', "
    "'Operating Agreement Including All Amendments', 'Operating Agreement, Amended & Restated (Post Tax Equity)', "
    "'Guaranty Agreement', 'Loan Maturity Date', 'Independent Engineer Report' or "
    "'Operating Agreement Including All Amendments (Pre-Tax Equity)'"
)

EMPTY_KEY_PAYLOAD_ERR = "Validation error: body.name - Field required; body.value - Field required"
KEY_VALUE_TOO_SHORT_ERR = "Validation error: body.value - String should have at least 1 character"
KEY_VALUE_TOO_LONG_ERR = "Validation error: body.value - String should have at most 2000 characters"
KEY_NOT_ALLOWED_FOR_DOCUMENT_KIND_ERR = "Key 'Owner' is not allowed for the 'Executive Summary' document"

# Define test sections mapper to not create whole list of sections
test_document_sub_sections_mapper = {
    DocumentSections.executive_summary: [],
    DocumentSections.preview: [],
}

# Define test document sections mapper to not create whole list of site documents
test_document_name_section_mapper = {
    DocumentSections.executive_summary: [
        SiteDocumentsEnum.executive_summary,
    ],
    DocumentSections.preview: [
        SiteDocumentsEnum.site_lease,
        SiteDocumentsEnum.interconnection_agreement_and_amendments,
        SiteDocumentsEnum.om_agreement,
        SiteDocumentsEnum.epc_agreement,
        SiteDocumentsEnum.ppa_and_amendments,
    ],
}


EXPECTED_DOCUMENTS_RESPONSE_ALL_SITES_DOCUMENTS = [
    {
        "name": "Executive Summary",
        "documents_count": 1,
        "documents": [{"name": "Executive Summary"}],
        "related_sections": [],
    },
    {
        "name": "Preview",
        "documents_count": 13,
        "documents": [
            {"name": "Financial Model"},
            {"name": "Preliminary IE Review for Model"},
            {"name": "Preliminary Drawings for Model - Electrical"},
            {"name": "Preliminary Drawings for Model - Civil"},
            {"name": "PV Syst - Initial Package for Modeling - Seller"},
            {"name": "CRA (Community Reinvestment Act)"},
            {"name": "NMTC (New Market Tax Credit)"},
            {"name": "FEMA (Disaster Declaration Y/N)"},
            {"name": "ESG Statement (Environmental, Social & Governance)"},
            {"name": "EPA Greenhouse Gas Equivalencies Calculator"},
            {"name": "USDA / REAP"},
            {"name": "FERC 556"},
            {"name": "Project Preview"},
        ],
        "related_sections": [],
    },
    {
        "name": "Organizational Overview",
        "documents_count": 1,
        "documents": [{"name": "Org Chart (Before & After Investment)"}],
        "related_sections": [],
    },
    {
        "name": "Stage-1",
        "documents_count": 0,
        "documents": [],
        "related_sections": [
            {
                "name": "Site Stage-1",
                "documents_count": 28,
                "documents": [
                    {"name": "Site Lease"},
                    {"name": "Formal Notice of Commencement of Lease"},
                    {"name": "Title Report / Title Commitment"},
                    {"name": "Documents Evidencing Title Exceptions"},
                    {"name": "SNDAs, Lien Releases, and Waivers"},
                    {"name": "Leasehold Area Metes and Bounds Legal Description"},
                    {"name": "Purchase Option"},
                    {"name": "Evidence of Application for Municipal Permits"},
                    {"name": "Zoning Approval / Conditional Use Permit"},
                    {"name": "Phase 1 ESA"},
                    {"name": "Phase 2 ESA"},
                    {"name": "Environmental Reports"},
                    {"name": "Air"},
                    {"name": "Construction Stormwater"},
                    {"name": "Construction & Demolition Debris"},
                    {"name": "Endangered Species"},
                    {"name": "Wetlands"},
                    {"name": "USFWS Concurrence Letter re. protected species, & any associated correspondence"},
                    {"name": "Site Assessment"},
                    {"name": "GeoTechnical Report"},
                    {"name": "ALTA Survey"},
                    {"name": "FAA Obstruction Evaluation / Airport Airspace Analysis"},
                    {"name": "Assignment of Site Lease to ProjectCo (Lessor)"},
                    {"name": "Recorded Memorandum of Site Lease & Assignments"},
                    {"name": "Site Lease Estoppel for Benefit of Investor"},
                    {"name": "Phase 1 ESA Reliance Letter addressed to the Tax Credit Fund"},
                    {"name": "Pro Forma Title Policy"},
                    {"name": "IDA (Industrial Development Authority)"},
                ],
                "related_sections": [],
            },
            {
                "name": "Offtaker Stage-1",
                "documents_count": 9,
                "documents": [
                    {"name": "Offtaker"},
                    {"name": "Proof of Legal Name"},
                    {"name": "12 months of Utility Bills"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Bond Rating or other Third Party Financial Review"},
                    {"name": "PPA - Power Purchase Agreement"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "Assignment of PPA to ProjectCo"},
                    {"name": "PPA Estoppel"},
                ],
                "related_sections": [],
            },
            {
                "name": "ProjectCo (Lessor)",
                "documents_count": 10,
                "documents": [
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Operating Agreement Including All Amendments (Pre-Tax Equity)"},
                    {"name": "Proof of ProjectCo Ownership"},
                    {"name": "Financial Projections (Project Life)"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "Operating Agreement, Amended & Restated (Post Tax Equity)"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                    {"name": "UCC Terminations"},
                ],
                "related_sections": [],
            },
            {
                "name": "ProjectCo (Lessor) Owner",
                "documents_count": 9,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Proof of ProjectCo Ownership (AMIPA Acquisition MIPA)"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                ],
                "related_sections": [],
            },
            {
                "name": "ProjectCo (Lessor) Owner JV Member 1",
                "documents_count": 8,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                ],
                "related_sections": [],
            },
            {
                "name": "ProjectCo (Lessor) Owner JV Member 2",
                "documents_count": 8,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                ],
                "related_sections": [],
            },
            {
                "name": "ProjectCo (Lessor) Owner JV Member 3",
                "documents_count": 8,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                ],
                "related_sections": [],
            },
            {
                "name": "ProjectCo (Lessor) Parent",
                "documents_count": 13,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Proof of ProjectCo Ownership (PMIPA Parent MIPA)"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                    {"name": "Deliverables at Closing"},
                    {"name": "Assignment of Membership Interests"},
                    {"name": "Member/Officer Resignations"},
                    {"name": "Seller Certificate per 3(b)(v)"},
                    {"name": "FIRPTA"},
                ],
                "related_sections": [],
            },
            {
                "name": "Managing Member of Lessee HoldCo (Sponsor) & Parent",
                "documents_count": 8,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                ],
                "related_sections": [],
            },
            {
                "name": "Guarantor (Managing Member of Lessee HoldCo (Sponsor & Parent))",
                "documents_count": 9,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "Guaranty Agreement"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                ],
                "related_sections": [],
            },
            {
                "name": "Guarantor 2  (Managing Member of Lessee HoldCo (Sponsor & Parent))",
                "documents_count": 9,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "Guaranty Agreement"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                ],
                "related_sections": [],
            },
            {
                "name": "Guarantor 3  (Managing Member of Lessee HoldCo (Sponsor & Parent))",
                "documents_count": 9,
                "documents": [
                    {"name": "Statement of Qualifications"},
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Financials and Tax Returns (3 years)"},
                    {"name": "Operating Agreement Including All Amendments"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "Guaranty Agreement"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                ],
                "related_sections": [],
            },
            {
                "name": "Lessee HoldCo",
                "documents_count": 11,
                "documents": [
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Original Operating Agreement Including All Amendments"},
                    {"name": "MIPA to Lessee HoldCo (MMIPA Master Tenant MIPA)"},
                    {"name": "MIPA Assignment Agreement"},
                    {"name": "Date of Investor Closing"},
                    {"name": "UCC, Tax, Bankruptcy, Judgment and Pending Litigation Searches"},
                    {"name": "Incumbency Certificate & Resolutions (Proof of Authority)"},
                    {"name": "Certificate of Good Standing"},
                    {"name": "Operating Agreement, Amended & Restated (Post Tax Equity)"},
                    {"name": "Enforce-ability Opinion"},
                ],
                "related_sections": [],
            },
            {
                "name": "Tax Credit Fund",
                "documents_count": 3,
                "documents": [
                    {"name": "Articles of Organization"},
                    {"name": "Employer Identification Number (W-9 or IRS Letter)"},
                    {"name": "Certificate of Good Standing"},
                ],
                "related_sections": [],
            },
            {
                "name": "Incentives Stage-1",
                "documents_count": 7,
                "documents": [
                    {"name": "SREC Approval"},
                    {"name": "SREC Contracts or Proof of Ability to Merchandise"},
                    {"name": "Production Based Incentive (PBI) Approval"},
                    {"name": "NYSERDA Grant"},
                    {"name": "NYSERDA Grant Status (Portal Screen Shot & Due Date)"},
                    {"name": "NYSDAM NOI Final Determination"},
                    {"name": "Community Solar Program Participation"},
                ],
                "related_sections": [],
            },
            {
                "name": "Construction Documents Stage-1",
                "documents_count": 61,
                "documents": [
                    {"name": "Engineering, Procurement, Construction (EPC) Agreement"},
                    {"name": "Full Notice to Proceed"},
                    {"name": "Assignment of Warranties"},
                    {"name": "EPC Production Guaranty"},
                    {"name": "PV Syst - Issued for Construction (IFC) - First Buyer Report"},
                    {"name": "IFC (Issued for Construction) Stamped Project Drawings"},
                    {"name": "Project Schedule"},
                    {"name": "Current Progress Report / Construction % Complete"},
                    {"name": "EPC Permit & Studies Letter"},
                    {"name": "Local Building Permits (electrical, construction, etc.)"},
                    {"name": "Electrical Permit"},
                    {"name": "Application for Electrical Permit"},
                    {"name": "Building Permit"},
                    {"name": "Application for Building Permit"},
                    {"name": "Encroachment / Driveway Access Permit"},
                    {"name": "Application for Encroachment / Driveway Access Permit"},
                    {"name": "Project Budget and Draws Requests"},
                    {"name": "ProjectCo Invoices"},
                    {"name": "Draw #1"},
                    {"name": "Draw #2"},
                    {"name": "Draw #3"},
                    {"name": "Draw #4"},
                    {"name": "Draw #5"},
                    {"name": "Draw #6"},
                    {"name": "Draw #7"},
                    {"name": "Draw #8"},
                    {"name": "Draw #9"},
                    {"name": "Draw #10"},
                    {"name": "Draw #11"},
                    {"name": "Draw #12"},
                    {"name": "Draw #13"},
                    {"name": "Draw #14"},
                    {"name": "Draw #15"},
                    {"name": "Draw #16"},
                    {"name": "Draw #17"},
                    {"name": "Draw #18"},
                    {"name": "Draw #19"},
                    {"name": "Draw #20"},
                    {"name": "Construction Lien Releases"},
                    {"name": "Change Order Requests"},
                    {"name": "Monitoring System and DAS"},
                    {"name": "OFE (Owner Furnished Equipment) Proof of Procurement"},
                    {"name": "Module Specs"},
                    {"name": "Module Warranty"},
                    {"name": "Module Warranty Backup Documents"},
                    {"name": "Racking Specs"},
                    {"name": "Racking Warranty"},
                    {"name": "Fully Executed Racking Warranty"},
                    {"name": "Racking Warranty Backup Documents"},
                    {"name": "Inverter Specs"},
                    {"name": "Inverter Warranty"},
                    {"name": "Inverter Warranty Backup Documents"},
                    {"name": "Transformer Specs"},
                    {"name": "Transformer Warranty"},
                    {"name": "Transformer Warranty Backup Documents"},
                    {"name": "Storage Specs"},
                    {"name": "Battery Specs"},
                    {"name": "Storage Warranty"},
                    {"name": "Storage Warranty Backup Documents"},
                    {"name": "Battery Warranty"},
                    {"name": "Battery Warranty Backup Documents"},
                ],
                "related_sections": [],
            },
            {
                "name": "Utility/Operational Documents Stage-1",
                "documents_count": 16,
                "documents": [
                    {"name": "Net Metering / Interconnection Application"},
                    {"name": "Operations and Maintenance (O&M) & Production Guarantee Agreement"},
                    {"name": "Subscriber Management Agreement"},
                    {"name": "Interconnection Agreement and Amendments"},
                    {"name": "Interconnection 25%"},
                    {"name": "Interconnection 75%"},
                    {"name": "Assignment of Interconnection Agreement and Amendments"},
                    {"name": "Utility Approval of Assignment of Interconnection Agreement and Amendments"},
                    {"name": "i39 Approval"},
                    {"name": "CESIR"},
                    {"name": "Evidence of Initial Payment"},
                    {"name": "NYSEG 25% Payment"},
                    {"name": "NYSEG 75% Payment"},
                    {"name": "NYSEG 100% Payment"},
                    {"name": "Servicing Agreement"},
                    {"name": "Servicer's Statement of Qualifications etc."},
                ],
                "related_sections": [],
            },
            {
                "name": "Insurance & Property Tax Stage-1",
                "documents_count": 9,
                "documents": [
                    {"name": "Property Tax Agreements"},
                    {"name": "EPC’s Insurance (Liability & Builders Risk)"},
                    {"name": "Real Estate Owner's/Landlord's Insurance (Liability)"},
                    {"name": "Projectco’s Liability Insurance"},
                    {"name": "Projectco’s Property Insurance"},
                    {"name": "Projectco's Business Interruption Insurance"},
                    {"name": "Insurance Companies are A rated or better"},
                    {"name": "O&M Insurance"},
                    {"name": "Decommissioning Bonds"},
                ],
                "related_sections": [],
            },
            {
                "name": "Project Financing Stage-1",
                "documents_count": 11,
                "documents": [
                    {"name": "Construction Loan Security Agreement"},
                    {"name": "Loan Maturity Date"},
                    {"name": "Construction Prom Note"},
                    {"name": "Construction Loan Guaranty"},
                    {"name": "Pledge Agreement"},
                    {"name": "Consent to Assignment of Offtaker"},
                    {"name": "Consent to Assignment of EPC"},
                    {"name": "UCC Financing Statements for Construction Loan"},
                    {"name": "USDA Pre-Cert Checklist"},
                    {"name": "Pre-Appraisal Data Check"},
                    {"name": "Project Appraisal"},
                ],
                "related_sections": [],
            },
            {
                "name": "Grandfathering Stage-1",
                "documents_count": 1,
                "documents": [{"name": "Proof of Start of Construction"}],
                "related_sections": [],
            },
            {
                "name": "Closing Matters Stage-1",
                "documents_count": 6,
                "documents": [
                    {"name": "Flow of Funds"},
                    {"name": "Sources and Uses"},
                    {"name": "Payoff Letters"},
                    {"name": "Third Party Invoices (Acct, Legal, etc.)"},
                    {"name": "Wire Instructions"},
                    {"name": "Opinions"},
                ],
                "related_sections": [],
            },
            {
                "name": "Tax Equity Funding Stage-1",
                "documents_count": 1,
                "documents": [{"name": "20% Funding"}],
                "related_sections": [],
            },
        ],
    },
    {
        "name": "Stage-2",
        "documents_count": 0,
        "documents": [],
        "related_sections": [
            {
                "name": "Site Stage-2",
                "documents_count": 2,
                "documents": [{"name": "As-Built ALTA Survey"}, {"name": "Final Title Policy"}],
                "related_sections": [],
            },
            {
                "name": "Mechanical Completion Stage-2",
                "documents_count": 3,
                "documents": [
                    {"name": "EPC Mechanical Completion Report/Certificate"},
                    {"name": "Independent Engineer Report"},
                    {"name": "Utility/City Mechanical Completion Tests"},
                ],
                "related_sections": [],
            },
            {
                "name": "Utility/Operational Documents Stage-2",
                "documents_count": 2,
                "documents": [{"name": "Permission to Operate (PTO)"}, {"name": "Commercial Operation Date (COD)"}],
                "related_sections": [],
            },
            {
                "name": "Project Financing Stage-2",
                "documents_count": 9,
                "documents": [
                    {"name": "UCC3 Release or Termination"},
                    {"name": "Term Sheet for Permanent Financing"},
                    {"name": "Permanent Loan Security Agreement"},
                    {"name": "Loan Maturity Date"},
                    {"name": "Permanent Promissory Note"},
                    {"name": "Permanent Loan Guaranty"},
                    {"name": "Consent to Assignment of O&M"},
                    {"name": "UCC Financing Statements for Permanent Loan"},
                    {"name": "Forbearance Agreement"},
                ],
                "related_sections": [],
            },
            {
                "name": "Substantial Completion Stage-2",
                "documents_count": 9,
                "documents": [
                    {"name": "PV Syst - As Built - Second Buyer Report"},
                    {"name": "Seller Acceptance of Second Buyer PV Syst Report"},
                    {"name": "PV Syst - Independent Report - Seller"},
                    {"name": "Final PV Syst Reports Average"},
                    {"name": "As Built Project Drawings"},
                    {"name": "EPC Substantial Completion Report/Certificate"},
                    {"name": "Independent Engineer Report"},
                    {"name": "Placed in Service (PIS) Letter"},
                    {"name": "Final Construction Lien Releases"},
                ],
                "related_sections": [],
            },
            {
                "name": "Tax Equity Funding Stage-2",
                "documents_count": 1,
                "documents": [{"name": "70% Funding"}],
                "related_sections": [],
            },
        ],
    },
    {
        "name": "Stage-3",
        "documents_count": 0,
        "documents": [],
        "related_sections": [
            {
                "name": "Construction Documents Stage-3",
                "documents_count": 5,
                "documents": [
                    {"name": "EPC Final Completion/Acceptance Report/Certificate"},
                    {"name": "EPC Closeout Documents"},
                    {"name": "3rd Party Review - Final Acceptance"},
                    {"name": "Final Completion/Acceptance"},
                    {"name": "Photos of Completed Project"},
                ],
                "related_sections": [],
            },
            {
                "name": "Tax Equity Funding Stage-3",
                "documents_count": 1,
                "documents": [{"name": "10% K1"}],
                "related_sections": [],
            },
        ],
    },
]
EXPECTED_DOCUMENTS_RESPONSE_CONSTRUCTION_MANAGER = [
    {
        "name": "Executive Summary",
        "documents_count": 1,
        "documents": [{"name": "Executive Summary"}],
        "related_sections": [],
    },
    {
        "name": "Preview",
        "documents_count": 4,
        "documents": [
            {"name": "Preliminary IE Review for Model"},
            {"name": "Preliminary Drawings for Model - Electrical"},
            {"name": "Preliminary Drawings for Model - Civil"},
            {"name": "PV Syst - Initial Package for Modeling - Seller"},
        ],
        "related_sections": [],
    },
    {
        "name": "Stage-1",
        "documents_count": 0,
        "documents": [],
        "related_sections": [
            {
                "name": "Site Stage-1",
                "documents_count": 1,
                "documents": [{"name": "Site Lease"}],
                "related_sections": [],
            },
            {
                "name": "Construction Documents Stage-1",
                "documents_count": 37,
                "documents": [
                    {"name": "Engineering, Procurement, Construction (EPC) Agreement"},
                    {"name": "Full Notice to Proceed"},
                    {"name": "EPC Production Guaranty"},
                    {"name": "PV Syst - Issued for Construction (IFC) - First Buyer Report"},
                    {"name": "IFC (Issued for Construction) Stamped Project Drawings"},
                    {"name": "Project Schedule"},
                    {"name": "Current Progress Report / Construction % Complete"},
                    {"name": "EPC Permit & Studies Letter"},
                    {"name": "Local Building Permits (electrical, construction, etc.)"},
                    {"name": "Electrical Permit"},
                    {"name": "Application for Electrical Permit"},
                    {"name": "Building Permit"},
                    {"name": "Application for Building Permit"},
                    {"name": "Encroachment / Driveway Access Permit"},
                    {"name": "Application for Encroachment / Driveway Access Permit"},
                    {"name": "Change Order Requests"},
                    {"name": "Monitoring System and DAS"},
                    {"name": "OFE (Owner Furnished Equipment) Proof of Procurement"},
                    {"name": "Module Specs"},
                    {"name": "Module Warranty"},
                    {"name": "Module Warranty Backup Documents"},
                    {"name": "Racking Specs"},
                    {"name": "Racking Warranty"},
                    {"name": "Fully Executed Racking Warranty"},
                    {"name": "Racking Warranty Backup Documents"},
                    {"name": "Inverter Specs"},
                    {"name": "Inverter Warranty"},
                    {"name": "Inverter Warranty Backup Documents"},
                    {"name": "Transformer Specs"},
                    {"name": "Transformer Warranty"},
                    {"name": "Transformer Warranty Backup Documents"},
                    {"name": "Storage Specs"},
                    {"name": "Battery Specs"},
                    {"name": "Storage Warranty"},
                    {"name": "Storage Warranty Backup Documents"},
                    {"name": "Battery Warranty"},
                    {"name": "Battery Warranty Backup Documents"},
                ],
                "related_sections": [],
            },
            {
                "name": "Utility/Operational Documents Stage-1",
                "documents_count": 1,
                "documents": [{"name": "Interconnection Agreement and Amendments"}],
                "related_sections": [],
            },
        ],
    },
    {
        "name": "Stage-3",
        "documents_count": 0,
        "documents": [],
        "related_sections": [
            {
                "name": "Construction Documents Stage-3",
                "documents_count": 1,
                "documents": [{"name": "Photos of Completed Project"}],
                "related_sections": [],
            }
        ],
    },
]
