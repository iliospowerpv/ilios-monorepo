"""
Clarification module for the chatbot.
"""

import logging.config
import re
from typing import Any, List

from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

from src.chatbot.prompt_templates.base import (
    dialog_examples,
    list_of_topics,
    rag_context_prompt,
    risks_context_prompt,
    sql_context_prompt,
)
from src.chatbot.prompt_templates.clarification import (
    available_context,
    clarification_sys_prompt,
    clarification_template,
    previous_knowledge_agreement_types,
    previous_knowledge_sources,
)
from src.chatbot.utils import get_agreement_types_key_items_str


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Clarifier:
    """
    Clarification module for the chatbot.
    """

    def __init__(self, llm: Any) -> None:
        """
        Initialize the Clarifier.
        :param llm:
        """
        self.llm = llm
        self.base_system_prompt = clarification_sys_prompt
        self.clarification_template = clarification_template

    async def clarify(
        self,
        user_message: str,
        messages: Any,
        other_agreement_type_document_names: List[str],
        possible_sources: Any = None,
        possible_agreement_types_key_items: Any = None,
        sql_context: Any = None,
        rag_context: Any = None,
        risks_context: Any = None,
    ) -> tuple[bool, list[str]]:
        """
        Clarify the user's message.
        :param other_agreement_type_document_names:
        :param user_message:
        :param messages:
        :param possible_sources:
        :param possible_agreement_types_key_items:
        :param sql_context:
        :param rag_context:
        :param risks_context:
        :return:
        """

        system_message_template = self.base_system_prompt.replace(
            """<<<data_sources>>>""",
            dialog_examples,
        ).replace(
            "<<<topics>>>",
            list_of_topics,
        )

        any_context = any([sql_context, rag_context, risks_context])

        human_message_template = (
            self.clarification_template.replace(
                "<<<agreement_types_key_items>>>",
                get_agreement_types_key_items_str(other_agreement_type_document_names),
            )
            .replace(
                "<<<previous_knowledge_agreement_types>>>",
                (
                    previous_knowledge_agreement_types
                    if possible_agreement_types_key_items
                    else "Unknown agreement types and key items."
                ),
            )
            .replace(
                "<<<previous_knowledge_sources>>>",
                previous_knowledge_sources if possible_sources else "",
            )
            .replace(
                "<<<available_context>>>", available_context if any_context else ""
            )
            .replace(
                "<<<sql_context>>>",
                (sql_context_prompt if possible_sources else ""),
            )
            .replace("<<<rag_context>>>", rag_context_prompt if rag_context else "")
            .replace(
                "<<<risks_context>>>", risks_context_prompt if risks_context else ""
            )
        )

        chat_answer_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_message_template),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template(human_message_template),
            ]
        )

        answer_chain = chat_answer_prompt | self.llm

        input_dict = {
            "user_message": user_message,
            "history": messages,
        }
        input_dict["possible_answer_sources"] = possible_sources

        input_dict["possible_answer_agreement_types_key_items"] = (
            possible_agreement_types_key_items
        )
        if sql_context:
            input_dict["sql_context"] = sql_context
        if rag_context:
            input_dict["rag_context"] = rag_context
        if risks_context:
            input_dict["risks_context"] = risks_context

        logger.debug(f"Human message template: {human_message_template}")
        logger.debug(f"Input dict: {input_dict}")

        response = await answer_chain.ainvoke(input_dict)

        return self.parse_response(response.content)

    @staticmethod
    def parse_response(res: str) -> tuple[bool, list[str]]:
        """
        Parse the response from the clarification model.
        From str to tuple[bool, list[str]].
        If clarification needed, returns flag true and 3 questions in a list.
        The output should look like "True, [Question1, Question2, Question3]".
        If clarification not needed, return flag false an empty list.
        The output should look like "False, []".
        :param res:
        :return:
        """
        # noinspection RegExpDuplicateCharacterInClass
        rx = re.compile(r"(?<!,)[^[,\[]+(?=[,\]][^,\[]*)")
        rx2 = re.compile(r'"(.*?)"')
        try:
            print(f"Raw response: {res}")
            res = res.replace("\n", " ")
            items = re.findall(rx, res)
            flag = items[0].lower().strip() == "true"
            questions = [x.strip() for x in re.findall(rx2, res)]
            print(flag, questions)

            return flag, questions

        except Exception as e:
            print("Error parsing chat output:")
            print(e)
            print("Classifier output:", res)
            return False, []
