from src.pipelines.constants import AgreementType
from src.pipelines.term_extraction.pipeline_config import (
    EPCPipelineConfig,
    InterconnectionAgreementPipelineConfig,
    LoanAgreementPipelineConfig,
    OMPipelineConfig,
    OMProductionGuarantee,
    OperatingAgreementPipelineConfig,
    Phase1ESAConfig,
    PPAPipelineConfig,
    PVSystPipelineConfig,
    SiteLeasePipelineConfig,
    SubscriberMgmtPipelineConfig,
)


agreement_type_to_config = {
    AgreementType.SITE_LEASE: SiteLeasePipelineConfig,
    AgreementType.INTERCONNECTION_AGREEMENT: InterconnectionAgreementPipelineConfig,
    AgreementType.PPA: PPAPipelineConfig,
    AgreementType.OM_AGREEMENT: OMPipelineConfig,
    AgreementType.EPC: EPCPipelineConfig,
    AgreementType.OM_PRODUCTION_GUARANTEE: OMProductionGuarantee,
    AgreementType.PV_SYST: PVSystPipelineConfig,
    AgreementType.SUBSCRIBER_MANAGEMENT_AGREEMENT: SubscriberMgmtPipelineConfig,
    AgreementType.LOAN_AGREEMENT: LoanAgreementPipelineConfig,
    AgreementType.PHASE_1_ESA: Phase1ESAConfig,
    AgreementType.OPERATING_AGREEMENT: OperatingAgreementPipelineConfig,
}

agreement_types = {
    pipeline_config.pipeline_name: pipeline_config  # type: ignore
    for pipeline_config in agreement_type_to_config.values()
}

agreements_types_in_db_mapping = {
    AgreementType.SITE_LEASE: "site_lease",
    AgreementType.INTERCONNECTION_AGREEMENT: "interconnection_agreement_and_amendments",
    AgreementType.PPA: "ppa_and_amendments",
    AgreementType.OM_AGREEMENT: "om_agreement",
    AgreementType.EPC: "epc_agreement",
    AgreementType.PV_SYST: [
        "seller_initial_pv_syst_full_data_package_for_model",
        "ifc_issued_for_construction_pv_syst_first_buyer_pv_syst_report",
        "as_built_pv_syst_with_full_data_package",
        "seller_independent_pv_syst_report",
    ],
    AgreementType.SUBSCRIBER_MANAGEMENT_AGREEMENT: "subscriber_management_agreement",
    AgreementType.LOAN_AGREEMENT: [
        "construction_loan_security_agreement",
        "permanent_loan_security_agreement",
    ],
    AgreementType.PHASE_1_ESA: "phase_1_esa",
    AgreementType.OPERATING_AGREEMENT: "operating_agreement_including_all_amendments",
}
