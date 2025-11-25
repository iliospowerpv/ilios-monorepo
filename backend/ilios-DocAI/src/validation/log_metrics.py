import os
from typing import Any, Dict

from google.cloud import aiplatform


def log_metrics(
    experiment_name: str,
    run_name: str,
    metrics: Dict[str, float | int | str],
    config: Dict[str, Any],
) -> None:
    """Log metrics to Vertex AI."""
    aiplatform.init(
        experiment=experiment_name,
        project=os.environ["PROJECT_ID"],
        location=os.environ["LOCATION"],
    )

    aiplatform.start_run(run=run_name)

    aiplatform.log_metrics(metrics)
    aiplatform.log_params(config)

    aiplatform.end_run()
