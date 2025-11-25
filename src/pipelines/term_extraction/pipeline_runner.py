import logging.config
import os
from typing import Optional

import mlflow
import pandas as pd

from src.pipelines.term_extraction.pipeline import PipelineFactory
from src.pipelines.term_extraction.pipeline_config import PipelineConfig
from src.pipelines.term_extraction.utils import (
    add_units,
    get_project_preview,
    save_results,
)
from src.validation.validation import calculate_metrics


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)

mlflow.set_tracking_uri(uri=os.environ["MLFLOW_TRACKING_URI"])


def mlflow_metrics(
    config: PipelineConfig, metrics_total: pd.DataFrame, results_df_name: str
) -> None:
    """
    Log metrics to mlflow.
    :param config:
    :param metrics_total:
    :param results_df_name:
    :return:
    """
    mlflow.log_params(config.__dict__)
    mlflow.log_metrics(metrics_total.iloc[0].drop(["file_name", "key_item"]).to_dict())
    mlflow.log_artifact(results_df_name)


class PipelineRunner:
    """Pipeline runner for building project previews."""

    def __init__(
        self, pipeline_config: PipelineConfig, experiment: Optional[str] = None
    ):
        """Initialize the term_extraction runner."""
        self.pipeline = PipelineFactory.create_pipeline(pipeline_config)
        self.config = pipeline_config
        self.override_mlflow_experiment(experiment)
        self.result_metrics = None

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

        with mlflow.start_run():
            for file_name in self.config.get_file_names():
                logger.info("PROCESSING FILE: %s", file_name)
                logger.info("PULLING CORRECT PROJECT PREVIEW: %s", file_name)
                correct_project_preview = get_project_preview(
                    self.config.get_project_previews_path(), file_name
                )
                if self.config.pipeline_name == "pv-syst":
                    correct_project_preview["Legal Terms"] = correct_project_preview[
                        "Value"
                    ].copy()
                    correct_project_preview["units"] = (
                        self.config.get_terms_and_instructions()["unit"]
                    )
                    correct_project_preview["Legal Terms"] = (
                        correct_project_preview.apply(add_units, axis=1)
                    )

                logger.info("BUILDING PROJECT PREVIEW: %s", file_name)
                if type(file_name) is list:
                    predicted_project_preview = self.pipeline.build_project_preview(
                        [
                            self.config.get_documents_path() + attachment
                            for attachment in file_name
                        ]
                    )
                else:
                    predicted_project_preview = self.pipeline.build_project_preview(
                        [self.config.get_documents_path() + file_name]  # type: ignore
                    )
                logger.info("COMPARE: %s", file_name)
                predicted_actual = predicted_project_preview.merge(
                    correct_project_preview, on="Key Items", how="outer"
                )
                logger.info("CALCULATE METRICS: %s", file_name)
                metrics = calculate_metrics(predicted_actual, self.config.metrics)
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
                results, self.config.get_output_results_path(), self.config.metrics
            )
            self.result_metrics = (
                metrics_total.iloc[0].drop(["file_name", "key_item"]).to_dict()
            )
            mlflow.set_tag("Type", "Legal Terms Extraction")
            mlflow_metrics(self.config, metrics_total, results_df_name)
            logger.info("PIPELINE SUCCEEDED")

    def override_mlflow_experiment(self, experiment: str | None) -> None:
        """Override the mlflow experiment if experiment name is provided"""
        if experiment:
            mlflow.set_experiment(experiment)
        else:
            mlflow.set_experiment(self.config.pipeline_name)
