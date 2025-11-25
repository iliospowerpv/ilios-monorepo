import logging.config
import os

import mlflow

from src.pipelines.constants import NOT_PROVIDED_STR
from src.pipelines.term_extraction.pipeline_config import PipelineConfig
from src.pipelines.term_extraction.pipeline_runner import mlflow_metrics
from src.pipelines.term_extraction.utils import get_project_preview, save_results
from src.pipelines.term_summary.base import TermSummaryPipelineFactory
from src.validation.validation import calculate_metrics


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


mlflow.set_tracking_uri(uri=os.environ["MLFLOW_TRACKING_URI"])


class ShortTermsPipelineRunner:
    """Pipeline runner for building project previews."""

    def __init__(self, pipeline_config: PipelineConfig):
        """Initialize the term_extraction runner."""
        self.pipeline = TermSummaryPipelineFactory.create_pipeline(pipeline_config)
        self.config = pipeline_config

    def run(self) -> None:
        """Run the term_extraction.

        Pipeline steps:
        1. Load the correct project preview.
        2. Build the project preview using our model.
            1.1. Load the document.
            1.2. Process the document with DocAI service (extract text).
            1.3. Build the RAG system on the provided document text.
            1.4. Execute LLM within the RAG system to generate legal terms.
            1.5. Build the project preview.
        3. Compare the predicted and actual project previews.
        4. Calculate the metrics.
        5. Save the results.

        Note: The term_extraction is run for each file in the term_extraction config.
        """

        logger.info("STARTING PIPELINE")
        results = []
        mlflow.set_experiment(self.config.pipeline_name)
        with mlflow.start_run():
            for file_name in self.config.get_file_names():
                logger.info("PROCESSING FILE: %s", file_name)
                logger.info("PULLING CORRECT PROJECT PREVIEW: %s", file_name)
                correct_project_preview = get_project_preview(
                    self.config.get_project_previews_path(), file_name
                )
                logger.info("BUILDING PROJECT PREVIEW: %s", file_name)

                correct_project_preview = correct_project_preview.rename(
                    {"Legal Terms": "Predicted Legal Terms"}, axis=1
                )
                correct_project_preview = correct_project_preview[
                    correct_project_preview["Key Items"].isin(
                        self.config.get_terms_and_instructions()["Key Items"]
                    )
                ]
                correct_project_preview["Value"] = correct_project_preview[
                    "Value"
                ].replace(NOT_PROVIDED_STR, "N/A")
                predicted_project_preview = self.pipeline.run(
                    correct_project_preview[["Key Items", "Predicted Legal Terms"]]
                )
                predicted_project_preview = predicted_project_preview.rename(
                    {"Term Summary": "Predicted Value"}, axis=1
                )
                logger.info("COMPARE: %s", file_name)
                predicted_actual = predicted_project_preview[
                    ["Key Items", "Predicted Value"]
                ].merge(correct_project_preview, on="Key Items", how="outer")
                logger.info("CALCULATE METRICS: %s", file_name)
                metrics = calculate_metrics(
                    predicted_actual,
                    self.config.metrics,
                    long_terms=False,
                )
                predicted_actual_metrics = predicted_actual.merge(
                    metrics, on="Key Items", how="outer"
                )
                if type(file_name) is list:
                    results.append(
                        predicted_actual_metrics.assign(file_name=file_name[0])
                    )
                else:
                    results.append(predicted_actual_metrics.assign(file_name=file_name))
                logger.info("FINISHED PROCESSING: %s", file_name)
            logger.info(f"SAVING RESULTS TO: {self.config.get_output_results_path()}")
            metrics_total, results_df_name = save_results(
                results,
                self.config.get_output_results_path(),
                self.config.metrics,
                long_terms=False,
            )
            mlflow.set_tag("Type", "Short Terms Extraction")
            mlflow_metrics(self.config, metrics_total, results_df_name)
            logger.info("PIPELINE SUCCEEDED")
