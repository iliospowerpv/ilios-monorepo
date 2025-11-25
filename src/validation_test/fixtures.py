# flake8: noqa
from typing import Any, Dict

import pytest

from src.pipelines.term_extraction.pipeline_config import (
    EPCPipelineConfig,
    InterconnectionAgreementPipelineConfig,
    LoanAgreementPipelineConfig,
    OMPipelineConfig,
    Phase1ESAConfig,
    PPAPipelineConfig,
    PVSystPipelineConfig,
    SiteLeasePipelineConfig,
    SubscriberMgmtPipelineConfig,
)


@pytest.fixture
def test_files_fixture() -> Dict[str, str]:
    return {
        InterconnectionAgreementPipelineConfig.pipeline_name: "Blue Sky.Interconnection Agreement.Felicita Town Centre.pdf",
        SiteLeasePipelineConfig.pipeline_name: "Site Lease - GLD - Canton (ES).pdf",
        PPAPipelineConfig.pipeline_name: "Sheridan PPA.pdf",
        OMPipelineConfig.pipeline_name: "O&M Agreement - Emerald Green - Cape Fear.pdf",
        EPCPipelineConfig.pipeline_name: "EPC Agreement - Novel - Bartel.pdf",
        LoanAgreementPipelineConfig.pipeline_name: "DuQuoin Solar Executed FMW Loan Docs.pdf",
        SubscriberMgmtPipelineConfig.pipeline_name: "Skyway Avenue Solar Farm_ LLC - Subscriber Management Agreement (NES 9.24.21).pdf",
        PVSystPipelineConfig.pipeline_name: "NC_Cape Fear_PVsyst_07192021.pdf",
        Phase1ESAConfig.pipeline_name: "Phase I ESA - Augusta Road Bowdoin Solar LLC.pdf",
    }


@pytest.fixture
def pipeline_configs() -> Dict[str | None, Any]:
    return {
        pipeline_config.pipeline_name: pipeline_config
        for pipeline_config in [
            InterconnectionAgreementPipelineConfig,
            SiteLeasePipelineConfig,
            PPAPipelineConfig,
            OMPipelineConfig,
            EPCPipelineConfig,
            LoanAgreementPipelineConfig,
            SubscriberMgmtPipelineConfig,
            PVSystPipelineConfig,
            Phase1ESAConfig,
        ]
    }
