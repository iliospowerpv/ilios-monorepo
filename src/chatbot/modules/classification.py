"""
Classification module for the chatbot.
"""

import logging.config
from typing import Any, List

from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

from src.chatbot.utils import get_agreement_types_key_items_str


logger = logging.getLogger(__name__)


class Classifier:
    """
    Classification module for the chatbot.
    """

    def __init__(
        self,
        llm: Any,
        classification_template: str,
        classification_system_prompt: str,
        binary: bool = False,
    ) -> None:
        """
        Initialize the Classifier.
        :param llm:
        :param classification_template:
        :param classification_system_prompt:
        :param binary:
        """
        self.llm = llm
        self.sources_classification_template = classification_template
        self.sources_classification_system_prompt = classification_system_prompt
        self.binary = binary

    async def invoke(
        self,
        user_message: str,
        memory: Any,
        other_agreement_type_document_names: List[str],
    ) -> Any:
        """
        Invoke the classification.
        Main function to classify the sources.
        :param other_agreement_type_document_names:
        :param user_message:
        :param memory:
        :return:
        """

        agreement_types_key_items_str = get_agreement_types_key_items_str(
            other_agreement_type_document_names
        )
        classification_question = self.sources_classification_template.replace(
            "<<<agreement_types_key_items>>>", agreement_types_key_items_str
        )

        chat_answer_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=self.sources_classification_system_prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template(classification_question),
            ]
        )

        answer_chain = chat_answer_prompt | self.llm

        response = await answer_chain.ainvoke(
            {
                "user_message": user_message,
                "history": memory,
            }
        )
        return (
            self.parse_response(response.content)
            if not self.binary
            else self.parse_response_binary(response.content)
        )

    @staticmethod
    def parse_response(res: Any) -> list[str]:
        """
        Parse the response from the classification model.
        Output should be a list of strings.
        Expected structure:
        ["Site Lease", "Effective Date",
        "Interconnection Agreement", "Effective Date",
        "Operating Agreement", "Parties", "Named Manager"]
        :param res:
        :return:
        """
        try:
            rtext = res
            logger.debug(f"Raw response: {rtext}")
            try:
                ans: list[str] = eval(rtext)
                return ans
            except ValueError:
                print("Error evaluating chat output, trying to parse it:")
                items = (
                    rtext.replace("[", "")
                    .replace("]", "")
                    .replace('"', "")
                    .replace("'", "")
                    .split(",")
                )
                return [x.strip() for x in items]
        except Exception as e:
            print("Error parsing chat output:")
            print(e)
            print("Classifier output:", res.content)
            return []

    @staticmethod
    def parse_response_binary(res: Any) -> bool | None:
        """
        Parse the response from the binary classification model.
        :param res:
        :return:
        """
        try:
            return bool(eval(res))
        except Exception as e:
            print("Error parsing chat output:")
            print(e)
            print("Classifier output:", res)
            return None
