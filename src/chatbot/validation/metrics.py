import logging
from typing import Dict, List

import nltk
import numpy as np
import pandas as pd
from langchain.chains.llm import LLMChain
from Levenshtein import distance

from src.validation.rouge_score import RougeScore
from src.validation.validation import (
    bleu_score_calculation,
    levenshtein_score,
    meteor_score_calculation,
    rouge_score_calculation,
)


logger = logging.getLogger(__name__)


def calculate_chatbot_metrics(
    predicted_actual: pd.DataFrame, metrics: List[str]
) -> pd.DataFrame:
    """Calculate metrics for the chatbot validation pipeline."""
    try:
        nltk.download("wordnet")
    except Exception as e:
        print(f"Error: {e}")

    metrics_results = []
    for _, row in predicted_actual.iterrows():
        correct_legal_terms = row["Answer"]
        predicted_legal_terms = row["Response"]

        if (
            pd.isna(correct_legal_terms)
            or pd.isna(predicted_legal_terms)
            or predicted_legal_terms == ""
        ):
            metrics_results.append({metric: np.nan for metric in metrics})
            continue

        metric_functions = {
            "levenshtein_distance": lambda: distance(
                correct_legal_terms, predicted_legal_terms
            ),
            "levenshtein_score": lambda: levenshtein_score(
                correct_legal_terms, predicted_legal_terms
            ),
            "bleu_score": lambda: bleu_score_calculation(
                correct_legal_terms, predicted_legal_terms
            ),
            "meteor_score": lambda: meteor_score_calculation(
                correct_legal_terms, predicted_legal_terms
            ),
            "rouge1_f1_score": lambda: rouge_score_calculation(
                correct_legal_terms, predicted_legal_terms, score_type=RougeScore.ROUGE1
            ).fmeasure,
            "rouge1_precision_score": lambda: rouge_score_calculation(
                correct_legal_terms, predicted_legal_terms, score_type=RougeScore.ROUGE1
            ).precision,
            "rouge1_recall_score": lambda: rouge_score_calculation(
                correct_legal_terms, predicted_legal_terms, score_type=RougeScore.ROUGE1
            ).recall,
            "rougeL_f1_score": lambda: rouge_score_calculation(
                correct_legal_terms, predicted_legal_terms, score_type=RougeScore.ROUGEL
            ).fmeasure,
            "rougeL_precision_score": lambda: rouge_score_calculation(
                correct_legal_terms, predicted_legal_terms, score_type=RougeScore.ROUGEL
            ).precision,
            "rougeL_recall_score": lambda: rouge_score_calculation(
                correct_legal_terms, predicted_legal_terms, score_type=RougeScore.ROUGEL
            ).recall,
        }

        metrics_result = {}
        for metric in metrics:
            if metric in metric_functions:
                metrics_result[metric] = metric_functions[metric]()
            else:
                metrics_result[metric] = np.nan

        metrics_results.append(metrics_result)
    results_df = pd.DataFrame(
        metrics_results, index=predicted_actual["Question"]
    ).reset_index()
    results_df["Response"] = predicted_actual["Response"]
    results_df["Answer"] = predicted_actual["Answer"]

    return results_df


def llm_evaluation(
    question: str, reference_answer: str, new_answer: str, llm_chain: LLMChain
) -> int:
    """Evaluate the new response based on the reference response."""
    logger.info("Langchain chain setup success.")
    response = llm_chain.invoke(
        {
            "question": question,
            "reference_answer": reference_answer,
            "new_answer": new_answer,
        }
    )["text"]
    parsed_response: Dict[str, int] = eval(response)
    try:
        parsed_response["evaluation"]
    except ValueError:
        logger.info(f"Error parsing response: {parsed_response}")

    return parsed_response["evaluation"]
