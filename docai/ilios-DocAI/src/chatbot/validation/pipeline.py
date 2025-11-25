"""
Run validation Pipeline for Chatbot using Two example files: Site Lease
agreement and Interconnection Agreement. For those types we have a set of questions and
answers provided by the IliOS Team - this would be used as a baseline validation set.
"""

import logging.config
import os
import pathlib
from typing import List

import mlflow
import pandas as pd
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate

from src.chatbot.config import ChatbotConfig
from src.chatbot.modules.base import ChatbotBase
from src.chatbot.prompt_templates.base import base_system_prompt
from src.chatbot.validation.llm_validation import validation_prompt
from src.chatbot.validation.metrics import calculate_chatbot_metrics, llm_evaluation
from src.gen_ai.gen_ai import get_llm
from src.settings import CHATBOT_VALIDATION
from src.vectordb.chromadb.chatbot_db import ChromaDBChatbot


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


mlflow.set_tracking_uri(uri=os.environ["MLFLOW_TRACKING_URI"])


def main() -> None:
    experiment_name = "chatbot_validation"
    mlflow.set_experiment(experiment_name)
    logger.info("Starting Chatbot Validation Pipeline")
    db_site_lease = ChromaDBChatbot(
        db_path=pathlib.Path("data/chatbot/validation_set/site_lease")
    )
    db_interconnection = ChromaDBChatbot(
        db_path=pathlib.Path("data/chatbot/validation_set/interconnection")
    )
    db_pvsyst = ChromaDBChatbot(
        db_path=pathlib.Path("data/chatbot/validation_set/pvsyst")
    )
    logger.info("Langchain chain setup success.")
    prompt = PromptTemplate(
        template=validation_prompt,
        input_variables=["question", "reference_answer", "new_answer"],
    )
    validation_chain = LLMChain(
        llm=get_llm(model_type="CLAUDE"),
        prompt=prompt,
        verbose=True,
    )
    # load data
    logger.info("Loading Chatbot Validation Data")
    site_lease_agreement = pd.read_csv(
        CHATBOT_VALIDATION / "site_lease/chatbot_site_lease_qa.csv", sep=";"
    )
    interconnection_agreement = pd.read_csv(
        CHATBOT_VALIDATION / "interconnection/chatbot_ia_qa.csv", sep=";"
    )
    interconnection_agreement = interconnection_agreement[
        interconnection_agreement.Question.notna()
    ]
    pvsyst_agreement = pd.read_csv(
        CHATBOT_VALIDATION / "pvsyst/chatbot_pvsyst_qa.csv", sep=","
    )

    def calculate_answers(qa_samples: pd.DataFrame, chain: LLMChain) -> pd.DataFrame:
        logger.info("Initializing Chatbot")
        chatbot = ChatbotBase(
            config=ChatbotConfig(use_sql_context=False),
            site_id=1,
            company_id=14,
            llm=get_llm(model_type="CLAUDE", system_prompt=base_system_prompt),
        )
        # run pipeline
        logger.info("Running responses for Site Lease")
        responses: List[str] = []
        for _, row in qa_samples.iterrows():
            response = chatbot.invoke({"human_input": row["Question"]})
            responses.append(response)  # type: ignore
            chatbot.clear_memory()
        qa_samples["Response"] = responses
        metrics = calculate_chatbot_metrics(
            qa_samples,
            metrics=[
                "levenshtein_score",
                "bleu_score",
                "meteor_score",
                "rouge1_f1_score",
                "rouge1_precision_score",
            ],
        )
        metrics["LLM_VALIDATION"] = [
            llm_evaluation(
                question=row["Question"],
                reference_answer=row["Answer"],
                new_answer=row["Response"],
                llm_chain=chain,
            )
            for _, row in qa_samples.iterrows()
        ]
        return metrics

    all_metrics = [
        calculate_answers(qa_samples, validation_chain)
        for db, qa_samples in zip(
            [db_site_lease, db_interconnection, db_pvsyst],
            [site_lease_agreement, interconnection_agreement, pvsyst_agreement],
        )
    ]

    total_metrics = pd.concat(all_metrics)
    total_metrics.to_csv(
        CHATBOT_VALIDATION / f"chatbot_validation_{experiment_name}.csv"
    )
    with mlflow.start_run():
        mlflow.log_artifact(
            str(CHATBOT_VALIDATION / f"chatbot_validation_{experiment_name}.csv")
        )


if __name__ == "__main__":
    main()
