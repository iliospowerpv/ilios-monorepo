from app.static.messages import BaseMessageEnum


class CompanyTypes(BaseMessageEnum):
    operation_maintenance_contractor = "O&M Contractor"
    project_site_owner = "Project/Site Owner"
    epc_contractor = "EPC Contractor"
    bank = "Bank"
    appraiser = "Appraiser"
    engineering_firm = "Engineering Firm"
    law_firm = "Law Firm"
    investor = "Investor"
    subscriber_manager = "Subscriber Manager"
    insurance_company = "Insurance Company"
