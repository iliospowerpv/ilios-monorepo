import logging
import time
from pathlib import Path
from typing import Any, Dict, List

import click
import mlflow
import pandas as pd
from langchain.globals import set_debug
from sklearn.metrics import balanced_accuracy_score, classification_report, f1_score

from src.deployment.fast_api.models.input import CoterminousInputItem, CoterminousSource
from src.deployment.fast_api.models.output import (
    ComparisonStatus,
    CoterminousOutputItem,
)
from src.pipelines.co_terminus_check.base import CoTerminusCheck


logger = logging.getLogger(__name__)


def flatten_dict(
    d: Dict[Any, Any], parent_key: str = "", sep: str = "_"
) -> Dict[Any, Any]:
    items: List[Any] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@click.command(context_settings={"ignore_unknown_options": True})
@click.option("-d", "--debug", is_flag=True, help="Enable debug mode")
def main(debug: bool) -> None:
    """
    Main function to run the co-terminus check pipeline.
    :param debug:
    :return:
    """
    # Set debug mode based on the argument
    set_debug(debug)
    mlflow.set_experiment("co-terminus-check")
    folder_path = Path("src/pipelines/co_terminus_check")
    with mlflow.start_run():
        test_data = pd.read_csv(folder_path / "test-data.csv")
        columns = [
            "Document Name 1",
            "Key Item 1",
            "Value 1",
            "Document Name 2",
            "Key Item 2",
            "Value 2",
        ]
        X = test_data[columns]
        y = test_data["ans"]

        co_terminus_check = CoTerminusCheck()

        co_terminus_input_items = get_co_terminus_input_items(X)
        pred_items = co_terminus_check.run_batch_validate(co_terminus_input_items)
        pred = get_co_terminus_output_items(pred_items)

        # Classification report
        report_df = test_data.copy()
        report_df["pred"] = pred
        # format the time
        report_path = (
            folder_path / f"report-"
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}.csv"
        )
        report_df.to_csv(report_path, index=False)

        metrics = flatten_dict(classification_report(y, pred, output_dict=True))
        metrics["f1_weighted"] = f1_score(y, pred, average="macro")
        metrics["balanced_accuracy_score"] = balanced_accuracy_score(y, pred)

        logger.info(f"Metrics: {metrics}")

        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(report_path))


def get_co_terminus_output_items(pred: List[CoterminousOutputItem]) -> List[bool]:
    return [item.status == ComparisonStatus.EQUAL for item in pred]


def get_co_terminus_input_items(X: pd.DataFrame) -> List[CoterminousInputItem]:
    return [
        CoterminousInputItem(
            name=str(idx),
            sources=[
                CoterminousSource(
                    document_name=row["Document Name 1"],
                    key_item=row["Key Item 1"],
                    value=row["Value 1"],
                ),
                CoterminousSource(
                    document_name=row["Document Name 2"],
                    key_item=row["Key Item 2"],
                    value=row["Value 2"],
                ),
            ],
        )
        for idx, row in X.iterrows()
    ]


if __name__ == "__main__":
    main()
