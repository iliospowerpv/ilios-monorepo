import enum


# Keys Extraction
NOT_PROVIDED_STR = "Not provided."
NO_POISON_PILLS_STR = "Text does not contain any poison pills."
ERROR_DURING_RETRIEVING = "Error during retrieving of the answer: "
NOT_SUPPORTED_KEY_ITEM = "Key item is not supported."

# Chatbot
HARMFUL_PLEASE_REPHRASE = (
    "Seems that your question was potentially harmful, please rephrase."
)


class AgreementType(enum.Enum):
    SITE_LEASE = "Site Lease"
    INTERCONNECTION_AGREEMENT = "Interconnection Agreement"
    OM_AGREEMENT = "O&M Agreement"
    EPC = "EPC Agreement"
    PPA = "Power Purchase Agreement"
    OM_PRODUCTION_GUARANTEE = "O&M Production Guarantee"
    PV_SYST = "PV Syst"
    SUBSCRIBER_MANAGEMENT_AGREEMENT = "Subscriber Management Agreement"
    LOAN_AGREEMENT = "Loan Agreement"
    PHASE_1_ESA = "Phase 1 ESA"
    OPERATING_AGREEMENT = "Operating Agreement"
    OTHER = "Other"

    @staticmethod
    def from_str(label: str) -> "AgreementType":
        if label in ("Site Lease", "siteLease", "site_lease"):
            return AgreementType.SITE_LEASE
        elif label in (
            "Interconnection Agreement",
            "interconnectionAgreement",
            "interconnection_agreement",
        ):
            return AgreementType.INTERCONNECTION_AGREEMENT
        elif label in ("O&M Agreement", "OMAgreement", "om_agreement"):
            return AgreementType.OM_AGREEMENT
        elif label in ("EPC Agreement", "EPCAgreement", "epc_agreement"):
            return AgreementType.EPC
        elif label in (
            "Power Purchase Agreement",
            "PowerPurchaseAgreement",
            "power_purchase_agreement",
        ):
            return AgreementType.PPA
        elif label in (
            "O&M Production Guarantee",
            "OMProductionGuarantee",
            "om_production_guarantee",
        ):
            return AgreementType.OM_PRODUCTION_GUARANTEE
        elif label in ("PV Syst", "PVSyst", "pv_syst"):
            return AgreementType.PV_SYST
        elif label in (
            "Subscriber Management Agreement",
            "SubscriberManagementAgreement",
            "subscriber_management_agreement",
        ):
            return AgreementType.SUBSCRIBER_MANAGEMENT_AGREEMENT
        elif label in ("Loan Agreement", "LoanAgreement", "loan_agreement"):
            return AgreementType.LOAN_AGREEMENT
        elif label in ("Phase 1 ESA", "Phase1ESA", "phase_1_esa"):
            return AgreementType.PHASE_1_ESA
        elif label in (
            "Operating Agreement",
            "OperatingAgreement",
            "operating_agreement",
        ):
            return AgreementType.OPERATING_AGREEMENT
        else:
            return AgreementType.OTHER
