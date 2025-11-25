import logging
from typing import Any, Dict, List, Tuple

import nltk
import numpy as np
import pandas as pd
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from Levenshtein import distance
from nltk.translate.bleu_score import sentence_bleu
from nltk.translate.meteor_score import single_meteor_score
from rouge_score import rouge_scorer
from rouge_score.scoring import Score

from src.gen_ai.gen_ai import get_llm
from src.validation.prompts import validation_prompt, validation_prompt_na
from src.validation.rouge_score import RougeScore


logger = logging.getLogger(__name__)


def calculate_metrics(
    predicted_actual: Any, metrics: List[str], long_terms: bool = True
) -> pd.DataFrame:
    """Calculate metrics for the predicted and actual legal terms
    prediction_type: Legal Terms or Value
    """
    try:
        nltk.download("wordnet")
    except Exception as e:
        print(f"Error: {e}")

    if "llm_validation" in metrics:
        llm_evaluation_chain, llm_evaluation_chain_na = get_evaluation_llm_chain()

    metrics_results = []
    for _, row in predicted_actual.iterrows():
        if long_terms:
            correct_legal_terms = row["Legal Terms"]
            predicted_legal_terms = row["Predicted Legal Terms"]
        else:
            correct_legal_terms = row["Value"]
            predicted_legal_terms = row["Predicted Value"]

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
            "llm_validation": lambda: llm_evaluation(
                reference_answer=correct_legal_terms,
                new_answer=predicted_legal_terms,
                llm_chain=llm_evaluation_chain,
                llm_chain_na=llm_evaluation_chain_na,
            ),
        }

        metrics_result = {}
        for metric in metrics:
            if metric in metric_functions:
                metrics_result[metric] = metric_functions[metric]()
            else:
                metrics_result[metric] = np.nan

        metrics_results.append(metrics_result)

    results = pd.DataFrame(
        metrics_results, index=predicted_actual["Key Items"]
    ).reset_index()

    results["llm_validation_binary"] = results["llm_validation"].apply(
        lambda x: np.nan if pd.isna(x) else 1 if x >= 1.0 else 0
    )

    return results


def get_evaluation_llm_chain() -> Tuple[LLMChain, LLMChain]:
    """Get the evaluation langchain chain."""

    prompt = PromptTemplate(
        template=validation_prompt,
        input_variables=["reference_answer", "new_answer"],
    )
    prompt_na = PromptTemplate(
        template=validation_prompt_na,
        input_variables=["new_answer"],
    )
    validation_chain = LLMChain(
        llm=get_llm(model_type="CLAUDE"),
        prompt=prompt,
    )
    validation_chain_na = LLMChain(
        llm=get_llm(model_type="CLAUDE"),
        prompt=prompt_na,
    )

    return validation_chain, validation_chain_na


def is_number(reference_answer: str) -> bool:
    """
    Check if the reference answer is a number
    :param reference_answer:
    :return:
    """
    try:
        float(reference_answer)
        return True
    except ValueError:
        return False


def llm_evaluation(
    reference_answer: str, new_answer: str, llm_chain: LLMChain, llm_chain_na: LLMChain
) -> float:
    """Evaluate the new response based on the reference response."""

    if pd.isna(reference_answer) or pd.isna(new_answer):
        return np.nan

    if reference_answer == "Not provided." and new_answer == "Not provided.":
        return 2.0
    if reference_answer != "Not provided." and new_answer == "Not provided.":
        return 0.0

    if is_number(reference_answer) and is_number(new_answer):
        return 2.0 if float(reference_answer) == float(new_answer) else 0.0

    if reference_answer == "Not provided." and new_answer != "Not provided.":
        response = llm_chain_na.invoke(
            {
                "new_answer": new_answer,
            }
        )["text"]
    else:
        response = llm_chain.invoke(
            {
                "reference_answer": reference_answer,
                "new_answer": new_answer,
            }
        )["text"]
    try:
        if response.startswith("```json"):
            return float(eval(response.strip("```json").strip())["evaluation"])
        parsed_response: Dict[str, int] = eval(response)
        return parsed_response["evaluation"]
    except (SyntaxError, ValueError):
        logger.info(f"Error parsing response: {response}")
        return np.nan


def levenshtein_score(str1: str, str2: str) -> float:
    """Calculate the Levenshtein score between two strings.
    Scaled Levenshtein distance by the maximum length of the two strings.
    Inverted the distance to make it a similarity score."""
    lev_distance = distance(str1, str2)
    max_distance = max(len(str1), len(str2))
    return 1.0 - lev_distance / max_distance


def bleu_score_calculation(target_str: str, predicted_str: str) -> float:
    """Calculate the BLEU score between two strings

    :param target_str: The target sentence string
    :param predicted_str: The predicted sentence string
    """
    score: float = sentence_bleu([target_str.split()], predicted_str.split())
    return score


def rouge_score_calculation(
    target_str: str, predicted_str: str, score_type: RougeScore = RougeScore.ROUGE1
) -> Score:
    """
    Calculate the ROUGE score between two strings

    :param target_str: The target sentence string
    :param predicted_str: The predicted sentence string
    :param score_type: Type of ROUGE score to calculate
    :return: A dictionary containing the ROUGE score for the given type
    """
    scorer = rouge_scorer.RougeScorer([score_type.value], use_stemmer=False)
    scores: Dict[str, Score] = scorer.score(target_str, predicted_str)
    return scores[score_type.value]


def meteor_score_calculation(target_str: str, predicted_str: str) -> float:
    """
    Calculate the METEOR score between two strings

    :param target_str: The target sentence string
    :param predicted_str: The predicted sentence string
    :return:
    """
    score: float = single_meteor_score(target_str.split(), predicted_str.split())
    return score


if __name__ == "__main__":
    # str1 = """Tenant may extend the Initial Term for three (3) additional five (5)
    # years periods."""
    # str2 = """(b) Tenant may extend the Initial Term for three (3) additional five
    # (5) years periods (each a Renewal Term" and collectively, the
    # “Renewal Terms")""".replace(
    #     "\n", " "
    # )
    # print(
    #     f"The Levenshtein distance between '{str1}' and '{str2}' is "
    #     f"{levenshtein_score(str1, str2)}"
    # )

    df = pd.read_csv(
        "/Users/odeine/PycharmProjects/ilios-DocAI/output-best/"
        "v11-prompt-tuned-for-each-key/2024-05-01_12-23-37_output-site-lease.csv"
    ).tail(20)

    chain, chain_na = get_evaluation_llm_chain()
    df["ll_validation_11"] = [
        llm_evaluation(
            row["Legal Terms"], row["Predicted Legal Terms"], chain, chain_na
        )
        for _, row in df.iterrows()
    ]
    df.to_csv(
        "/Users/odeine/PycharmProjects/ilios-DocAI/output-best/"
        "v11-prompt-tuned-for-each-key/2024-05-01_12-23-37_output-site-lease-1.csv",
        index=False,
    )
