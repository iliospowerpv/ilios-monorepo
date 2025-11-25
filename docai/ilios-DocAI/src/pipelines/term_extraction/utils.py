import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd
import sklearn
from pandas.errors import ParserError

from src.pipelines.constants import NOT_PROVIDED_STR


logger = logging.getLogger(__name__)


def merge_dicts(dict1: Dict[Any, Any], dict2: Dict[Any, Any]) -> Dict[Any, Any]:
    """Merge two dictionaries."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result:
            result[key].extend(value)
        else:
            result[key] = value
    return result


def read_old_project_preview(
    file_path: str, terms_correspondence_path: str
) -> pd.DataFrame:
    """Reads the old project preview and merges it with the terms correspondence."""
    terms_correspondence = pd.read_csv(terms_correspondence_path)
    old = pd.read_csv(file_path)
    new = terms_correspondence.merge(old, on="Key Items (Historical)", how="left")
    new["Value"] = new["Information"]
    new["Legal Terms"] = new["Information"]
    return new[["Key Items", "Value", "Legal Terms"]]


def get_project_preview(
    project_preview_dir: str, file_name: str | Sequence[str]
) -> pd.DataFrame:
    """Get project preview from file."""
    if type(file_name) is list:
        file_name = file_name[0]
    file_path = project_preview_dir + file_name.replace(".pdf", ".csv")  # type: ignore
    try:
        pp = pd.read_csv(file_path).fillna(NOT_PROVIDED_STR)
    except ParserError:
        logger.info(
            f"Exception reading {file_path} with default separator ','. "
            f"Reading with ';'"
        )
        pp = pd.read_csv(file_path, sep=";").fillna(NOT_PROVIDED_STR)
    return pp


def get_terms_and_definitions(terms_and_definitions_path: str) -> pd.DataFrame:
    """Load the terms and definitions from the csv file."""
    terms_and_definitions = pd.read_csv(terms_and_definitions_path)
    terms_and_definitions = terms_and_definitions[
        (~terms_and_definitions["Key Items"].isna())
        & (~terms_and_definitions["Definitions"].isna())
    ]
    return terms_and_definitions


def get_terms_and_instructions(terms_and_definitions_path: str) -> pd.DataFrame:
    """Load the terms and definitions from the csv file."""
    terms_and_definitions = pd.read_csv(terms_and_definitions_path)
    terms_and_definitions = terms_and_definitions[
        (~terms_and_definitions["Key Items"].isna())
        & (~terms_and_definitions["Instructions"].isna())
    ]
    return terms_and_definitions


def classification_metrics(y_true: pd.Series, y_pred: pd.Series) -> str:
    """
    Compute classification metrics. Return a string with the metrics.
    Confusion matrix, F1, Fbeta, Precision, Recall.
    """
    cm = sklearn.metrics.confusion_matrix(y_true, y_pred)

    f1_score = sklearn.metrics.f1_score(y_true, y_pred)
    fbeta_score = sklearn.metrics.fbeta_score(y_true, y_pred, beta=0.5)

    precision = sklearn.metrics.precision_score(y_true, y_pred)
    recall = sklearn.metrics.recall_score(y_true, y_pred)

    return (
        f"TP: {cm[1][1]}"
        f" FP: {cm[0][1]}"
        f" FN: {cm[1][0]}"
        f" TN: {cm[0][0]}\n"
        f" F1: {np.round(f1_score, 2)}"
        f" Fbeta: {np.round(fbeta_score, 2)}\n"
        f" Precision: {np.round(precision, 2)}"
        f" Recall: {np.round(recall, 2)}"
    )


def get_confusion_matrix_and_true_positive_metric(
    results_df: pd.DataFrame, metrics: List[str], long_terms: bool = True
) -> pd.DataFrame:
    """Compute confusion matrix."""

    if long_terms:
        true_col = "Legal Terms"
        pred_col = "Predicted Legal Terms"
    else:
        true_col = "Value"
        pred_col = "Predicted Value"

    results_df = results_df.copy().dropna(subset=[true_col, pred_col])
    not_provided_value = NOT_PROVIDED_STR if long_terms else "N/A"
    y_true = results_df[true_col] != not_provided_value
    y_pred = results_df[true_col] != not_provided_value

    ture_positives = y_true & y_pred
    metrics_on_true_positive: pd.DataFrame = pd.DataFrame(
        results_df[metrics][ture_positives].mean()
    ).T
    metrics_on_true_positive["file_name"] = np.nan
    metrics_on_true_positive["key_item"] = np.nan

    metrics_on_true_positive[true_col] = np.nan
    metrics_on_true_positive[pred_col] = np.nan

    return metrics_on_true_positive


def save_results(
    results: Any, path: str, metrics: List[str], long_terms: bool = True
) -> tuple[pd.DataFrame, str]:
    """Save pipeline results to a csv file."""

    cols = [
        "file_name",
        "key_item",
    ]
    cols += (
        [
            "Legal Terms",
            "Predicted Legal Terms",
        ]
        if long_terms
        else [
            "Value",
            "Predicted Value",
            "Predicted Legal Terms",
        ]
    )
    cols += metrics

    results = [
        metrics.reset_index().rename({"Key Items": "key_item"}, axis=1)
        for metrics in results
    ]

    results_df = pd.concat(results, ignore_index=True)

    confusion_matrix_and_true_positive_metric = (
        get_confusion_matrix_and_true_positive_metric(
            results_df, metrics, long_terms=long_terms
        )
    )

    metrics_total: pd.DataFrame = pd.DataFrame(results_df[metrics].mean()).T
    metrics_total["file_name"] = np.nan
    metrics_total["key_item"] = np.nan

    metrics_grouped_by_key_items: pd.DataFrame = (
        results_df.groupby("key_item")[metrics].mean().reset_index()
    )
    metrics_grouped_by_key_items["file_name"] = np.nan

    metrics_grouped_by_file_name: pd.DataFrame = (
        results_df.groupby("file_name")[metrics].mean().reset_index()
    )
    metrics_grouped_by_file_name["key_item"] = np.nan

    results_df = pd.concat(
        [
            confusion_matrix_and_true_positive_metric,
            metrics_total,
            metrics_grouped_by_key_items,
            metrics_grouped_by_file_name,
            results_df,
        ],
        ignore_index=True,
    )[cols]

    if not long_terms:
        results_df = results_df.rename({"Predicted Legal Terms": "Legal Terms"}, axis=1)

    results_df_name = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{path}"
    results_df.to_csv(results_df_name, index=False)

    return metrics_total, results_df_name


def add_units(row: pd.Series) -> Any:
    """Add units to the Value column."""
    value = row["Legal Terms"]
    if pd.isna(row["units"]):
        return value
    if ", " in value:
        return ", ".join(f"{v} {row['units']}" for v in value.split(", "))
    return f"{value} {row['units']}"


def retrieve_section_numbers(text: str) -> List[str]:
    """Retrieve section numbers from text."""

    pattern = r"Section\s\d+(\.\d+)?"

    # Use `re.finditer()` to get the full matched strings
    return [match.group(0) for match in re.finditer(pattern, text)]
