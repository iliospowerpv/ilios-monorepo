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
from src.pipelines.term_extraction.pipeline_runner import PipelineRunner  # noqa
from src.validation_test.fixtures import pipeline_configs, test_files_fixture  # noqa


TEST_THRESHOLD = 0.8
TOLERANCE = 0.05


@pytest.mark.parametrize(
    "agreement_name",
    [
        pipeline_config.pipeline_name
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
    ],
)
def test_model_prediction(
    agreement_name: str,
    test_files_fixture: Dict[str, str],
    pipeline_configs: Dict[str, Any],
) -> None:
    PipelineConfigClass = pipeline_configs[agreement_name]
    pipeline_config = PipelineConfigClass()
    pipeline_config.file_names = [test_files_fixture[agreement_name]]
    pipeline_runner = PipelineRunner(pipeline_config, experiment="validation_testing")
    pipeline_runner.run()
    assert pipeline_runner.result_metrics["llm_validation_binary"] >= (  # type: ignore
        TEST_THRESHOLD - TOLERANCE
    ), "The LLM validation binary metric is too low"
