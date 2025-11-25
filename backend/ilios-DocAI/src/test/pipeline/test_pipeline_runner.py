from unittest.mock import Mock, patch

import pandas as pd
import pytest
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from src.pipelines.term_extraction.pipeline_config import PipelineConfig
from src.pipelines.term_extraction.pipeline_runner import PipelineRunner


terms_and_definitions = pd.DataFrame(
    {"Key Items": ["term1", "term2"], "Definitions": ["def1", "def2"]}
)


@pytest.fixture
def pipeline_config() -> PipelineConfig:
    """Create a mock PipelineConfig object."""
    mock_config = Mock(spec=PipelineConfig)
    mock_config.get_file_names.return_value = ["file1", "file2"]
    mock_config.get_project_previews_path.return_value = "/path/to/project_previews/"
    mock_config.get_documents_path.return_value = "/path/to/documents/"
    mock_config.get_output_results_path.return_value = "/path/to/output_results/"
    mock_config.get_terms_and_definitions.return_value = terms_and_definitions
    mock_config.chunk_size = 600
    mock_config.model_type = "CLAUDE"
    mock_config.overlap_factor = 3
    mock_config.pipeline_name = "test_experiment"
    mock_config.metrics = ["metric1", "metric2"]
    return mock_config


@pytest.fixture
def pipeline_runner(pipeline_config: PipelineConfig) -> PipelineRunner:
    """Create a mock PipelineRunner object."""
    pipeline_runner = PipelineRunner(pipeline_config)
    return pipeline_runner


@patch("src.pipelines.term_extraction.pipeline.Pipeline.from_config")
def test_init(mock_from_config: Mock, pipeline_config: PipelineConfig) -> None:
    """Test that the PipelineRunner is initialized correctly."""
    pipeline_runner = PipelineRunner(pipeline_config)
    mock_from_config.assert_called_once_with(pipeline_config)
    assert pipeline_runner.config == pipeline_config


def set_valid_test_pipeline_name(
    experiment_name: str, pipeline_runner: PipelineRunner
) -> None:
    """
    If we set the pipeline name to the one that
    is already deleted, we need to restore it.
    Other way, we will get an error when trying to
    create a new experiment with the same name.
    This function checks if the experiment exists
    and restores it if it is deleted.
    So we can run the test without any errors.
    :param experiment_name:
    :param pipeline_runner:
    :return:
    """
    client = MlflowClient()
    try:
        experiment = client.get_experiment_by_name(experiment_name)
    except MlflowException:
        experiment = None

    if experiment is None:
        # The experiment does not exist, create a new one
        client.create_experiment(experiment_name)
    elif experiment.lifecycle_stage != "active":
        # The experiment exists but is deleted, restore it
        client.restore_experiment(experiment.experiment_id)

    pipeline_runner.config.pipeline_name = "test_experiment"


@patch("src.pipelines.term_extraction.pipeline_runner.get_project_preview")
@patch("src.pipelines.term_extraction.pipeline_runner.save_results")
@patch("src.pipelines.term_extraction.pipeline_runner.calculate_metrics")
@patch("src.pipelines.term_extraction.pipeline.Pipeline.build_project_preview")
def test_run(
    mock_build_project_preview: Mock,
    mock_calculate_metrics: Mock,
    mock_save_results: Mock,
    mock_get_project_preview: Mock,
    pipeline_runner: PipelineRunner,
) -> None:
    """Test that the run method runs the term_extraction correctly."""
    mock_build_project_preview.return_value = pd.DataFrame(
        {
            "Key Items": ["term1", "term2"],
            "Predicted Legal Terms": ["legalTerms1", "legalTerms2"],
        }
    )
    mock_get_project_preview.return_value = pd.DataFrame(
        {"Key Items": ["term1", "term2"], "Legal Terms": ["legalTerms1", "legalTerms2"]}
    )
    mock_calculate_metrics.return_value = pd.DataFrame(
        {"Key Items": ["term1", "term2"], "metric": [0.8, 0.9]}
    )

    set_valid_test_pipeline_name("test_experiment", pipeline_runner)
    mock_metrics_total = pd.DataFrame(
        {"metric": [0.85], "file_name": [None], "key_item": [None]}
    )
    mock_results_df_name = "results.csv"
    pd.DataFrame().to_csv(mock_results_df_name, index=False)
    mock_save_results.return_value = (mock_metrics_total, mock_results_df_name)

    pipeline_runner.run()

    mock_get_project_preview.assert_called()
    mock_build_project_preview.assert_called()
    mock_calculate_metrics.assert_called()
    mock_save_results.assert_called()
