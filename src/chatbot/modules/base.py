"""
Base module for the Chatbot.
"""

import asyncio
import logging.config
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from tqdm import tqdm

from src.chatbot.config import ChatbotConfig
from src.chatbot.modules.clarification import Clarifier
from src.chatbot.modules.classification import Classifier
from src.chatbot.modules.memory_summarization import MemorySummarizer
from src.chatbot.modules.state import ConversationState
from src.chatbot.prompt_templates.base import (
    base_prompt_template,
    base_system_prompt,
    dialog_examples,
    formatting_prompt,
    list_of_topics,
    rag_context_prompt,
    risks_context_prompt,
    sql_context_prompt,
)
from src.chatbot.prompt_templates.classification import (
    agreement_types_key_items_classification_system_prompt,
    agreement_types_key_items_classification_template,
    sources_classification_system_prompt_binary,
    sources_classification_template_binary,
)
from src.chatbot.utils import doc_string_template
from src.deployment.fast_api.models.chatbot_status import ChatbotState, ResponseStatus
from src.deployment.fast_api.settings import settings
from src.gen_ai.injections import InjectionClassifier, InjectionError
from src.pipelines.constants import HARMFUL_PLEASE_REPHRASE, AgreementType
from src.pipelines.sql_retriever.base import ProjectPreviewRetriever
from src.vectordb.pg_vector.retriever import PGVectorRetriever
from src.vectordb.pg_vector.sql import insert_sql_chatbot_history


handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


class ChatbotBase:
    """
    Base class for Chatbot
    """

    def __init__(
        self,
        llm: Any,
        site_id: int,
        company_id: int,
        config: ChatbotConfig,
        socket_manager: Any = None,
        websocket: Any = None,
    ) -> None:
        """
        Initialize the Chatbot.
        :param llm:
        :param site_id:
        :param company_id:
        :param config:
        :param socket_manager:
        :param websocket:
        """
        self.site_id = site_id
        self.company_id = company_id
        self.config = config

        self.socket_manager = socket_manager
        self.websocket = websocket

        self.use_sql_context = config.use_sql_context
        self.use_general_clarification = config.use_clarification
        self.sources_clarification = config.sources_clarification
        self.agreement_type_clarification = config.agreement_type_clarification
        self.llm = llm

        # db connectors
        self.project_preview_retriever = ProjectPreviewRetriever(site_id=self.site_id)
        self.retriever = PGVectorRetriever(settings.get_pg_vector_config())

        # memory handling modules
        self.messages_history = ChatMessageHistory()
        self.memory_summarizer = MemorySummarizer(size=3, llm=self.llm)
        self.conversation_state = ConversationState(
            clarification_max_retries=self.config.clarification_max_retries
        )

        # classifiers
        self.sources_classifier_binary = Classifier(
            self.llm,
            sources_classification_template_binary,
            sources_classification_system_prompt_binary,
            binary=True,
        )
        self.agreement_types_classifier = Classifier(
            self.llm,
            agreement_types_key_items_classification_template,
            agreement_types_key_items_classification_system_prompt,
        )

        # clarifier
        self.general_clarifier = Clarifier(self.llm)

        # injection classifier
        self.injection_classifier = InjectionClassifier()

        # chatbot status
        self.status: ChatbotState = ChatbotState.READY

        # utility
        self.other_agreement_type_document_names: List[str] = []

    def check_for_injection(self, user_message: str) -> bool:
        """
        Check for SQL injection or code in the user message.
        :param user_message:
        :return:
        """
        return self.injection_classifier.check_for_injection(user_message)

    def format_rag_context(self, documents: List[Document]) -> str:
        """
        Format the RAG context from the documents for chatbot prompt.
        :param documents:
        :return:
        """
        context = doc_string_template(
            "Document",
            documents[0].metadata["section_name"],
            documents[0].metadata["document_name"],
            documents[0].metadata["file_name"],
            documents[0].metadata["subsection_name"],
        )

        for idx, document in enumerate(documents[: self.config.max_documents]):
            context += f"\n\n{document.page_content}."
        return context

    async def retrieve_documents_from_rag(
        self, question: str, agreement_type: str, document_name: Optional[str] = None
    ) -> List[Any]:
        """Search the matching engine for relevant documentation"""
        filters: Dict[str, Any] = {
            "k": self.config.max_documents,
            "company_id": int(self.company_id),
            "site_id": int(self.site_id),
        }

        if document_name:
            filters["document_name"] = document_name
        else:
            filters["agreement_type"] = agreement_type
        vector_search_response = self.retriever.get_documents(
            question,
            filters,
        )
        return vector_search_response

    async def get_risks_context(
        self, agreement_types: Any
    ) -> Tuple[str | None, List[Document]]:
        """Retrieve the risks from the database"""
        logger.debug(f"Input to get_risks_context agreement_types: {agreement_types}")
        await self.update_status(ChatbotState.ANALYZING_RISK)
        risks_context = ""
        documents_list = []
        for agreement_type in agreement_types:
            documents = self.retriever.get_risks(
                {
                    "company_id": int(self.company_id),
                    "site_id": int(self.site_id),
                    "agreement_type": agreement_type.strip(),
                }
            )
            if not documents:
                continue
            formated_risks = self.format_risks(documents)
            risks_context += formated_risks if formated_risks else ""
            documents_list.extend(documents)

        if not risks_context:
            return None, []

        logger.info(f"Risks context: {risks_context}")
        return risks_context, documents_list

    @staticmethod
    def format_risks(documents: List[Document]) -> str | None:
        """
        Format the risks from the documents for chatbot prompt.
        :param documents:
        :return:
        """
        context = (
            doc_string_template(
                "Risks",
                documents[0].metadata["section_name"],
                documents[0].metadata["document_name"],
                documents[0].metadata["file_name"],
                documents[0].metadata["subsection_name"],
            )
            + "\n Risks: \n"
        )
        for document in documents:
            if not document.page_content:
                continue
            context += f"- {document.page_content}\n"
        if not context:
            return None
        return context

    def memory_update(
        self, user_message: Optional[str], assistant_message: Optional[str]
    ) -> None:
        """
        Update the memory of the chatbot.
        :param user_message:
        :param assistant_message:
        :return:
        """
        assert (
            user_message or assistant_message
        ), "At least one message should be provided"
        if user_message:
            self.messages_history.add_user_message(user_message)
        if assistant_message:
            self.messages_history.add_ai_message(assistant_message)
        if user_message and assistant_message:
            self.memory_summarizer.save_context(
                {"user": user_message}, {"assistant": assistant_message}
            )
        elif user_message:
            self.memory_summarizer.save_context({"user": user_message}, {})
        elif assistant_message:
            self.memory_summarizer.save_context({}, {"assistant": assistant_message})
        else:
            logger.error("No message to save in memory")

    async def classify_sources_binary(self, user_message: str) -> bool:
        """
        Function for classifying the sources from the user message.
        True if the user needs to provide sources, False otherwise.
        :param user_message:
        :return:
        """
        sources: bool = await self.sources_classifier_binary.invoke(
            user_message,
            self.get_history(),
            self.other_agreement_type_document_names,
        )
        return sources

    async def classify_agreement_type_key_items(
        self,
        user_message: str,
    ) -> Any:
        """
        Function for classifying the agreement type and key items from the user message.
        Expected structure of the agreement_type_key_items:
        ["Site Lease", "Effective Date",
        "Interconnection Agreement", "Effective Date",
        "Operating Agreement", "Parties", "Named Manager"]
        Expected structure of the output:
        [['Site Lease', ['Effective Date']],
        ['Interconnection Agreement', ['Effective Date']],
        ['Operating Agreement', ['Parties', 'Named Manager']]]
        :param user_message:
        :return:
        """
        agreement_type_key_items: List[str] = (
            await self.agreement_types_classifier.invoke(
                user_message,
                self.get_history(),
                self.other_agreement_type_document_names,
            )
        )

        agreement_type_key_items_all_dict: Dict[str, List[str]] = {}
        if agreement_type_key_items:
            agreement_type = None
            for item in agreement_type_key_items:
                item = item.strip()
                if item in self.project_preview_retriever.agreements_types + [
                    AgreementType.OTHER
                ] + (self.other_agreement_type_document_names or []):
                    agreement_type = item[::]
                    agreement_type_key_items_all_dict[agreement_type] = []
                elif agreement_type:
                    agreement_type_key_items_all_dict[agreement_type].append(item[::])
                else:
                    continue

        agreement_type_key_items_all = [
            [key, value] for key, value in agreement_type_key_items_all_dict.items()
        ]
        return agreement_type_key_items_all

    def get_history(self) -> Any:
        """
        Get the history of the chatbot.
        :return:
        """
        return self.memory_summarizer.load_memory_variables({})["history"]

    async def invoke(
        self, prompt_input: Dict[str, Any], output_documents: bool = False
    ) -> Any:
        """
        Main function for invoking the chatbot.
        :param prompt_input:
        :param output_documents:
        :return:
        """
        await self.update_status(ChatbotState.ANALYZING)
        try:
            self.check_for_injection(prompt_input["human_input"])
        except InjectionError as e:
            logger.error(f"Injection detected: {e}")
            return HARMFUL_PLEASE_REPHRASE

        user_message = prompt_input["human_input"]
        logger.info(f"Invoke chatbot with input: {user_message}")

        await self.update_status(ChatbotState.COLLECTING_INPUTS)

        self.set_other_agreement_type_document_names()

        sources = self.classify_sources_binary(user_message)
        agreement_type_key_items = self.classify_agreement_type_key_items(user_message)

        sources, agreement_type_key_items = list(
            await asyncio.gather(sources, agreement_type_key_items)
        )
        self.conversation_state.context["sources_binary"] = sources
        print("Predicted sources:", sources)

        sql_context: Optional[str] = None
        sql_documents_list: List[Document] = []

        rag_context: Optional[str] = None
        rag_documents_list: List[Document] = []

        risks_context: Optional[str] = None
        risks_documents_list: List[Document] = []

        if self.conversation_state.context.get("sources_binary"):
            self.conversation_state.context["agreement_type_key_items"] = (
                agreement_type_key_items
            )
            print("Predicted agreement types", agreement_type_key_items)

            sql_context_coroutine = self.get_sql_context(agreement_type_key_items)
            agreement_types = self.get_agreement_types(agreement_type_key_items)

            rag_context_coroutine = self.get_rag_context(user_message, agreement_types)
            risks_context_coroutine = self.get_risks_context(agreement_types)

            sql_context_result, rag_context_result, risks_context_result = list(
                await asyncio.gather(
                    sql_context_coroutine,
                    rag_context_coroutine,
                    risks_context_coroutine,
                )
            )
            sql_context, sql_documents_list = sql_context_result
            rag_context, rag_documents_list = rag_context_result
            risks_context, risks_documents_list = risks_context_result

            self.conversation_state.context["sql_context"] = sql_context
            self.conversation_state.context["rag_context"] = rag_context
            self.conversation_state.context["risks_context"] = risks_context

        if self.use_general_clarification:
            clarification_general_res_coroutine = self.clarify_general(
                user_message,
                sql_context,
                rag_context,
                risks_context,
                possible_sources=self.conversation_state.context.get("sources_binary"),
                possible_agreement_types_key_items=self.conversation_state.context.get(
                    "agreement_type_key_items"
                ),
            )
            response_coroutine = self.invoke_general(
                prompt_input,
                sql_context=sql_context,
                rag_context=rag_context,
                risks_context=risks_context,
                sources_binary=self.conversation_state.context.get("sources_binary"),
            )
            clarification_general_question, response = list(
                await asyncio.gather(
                    clarification_general_res_coroutine, response_coroutine
                )
            )
            if clarification_general_question is not None:
                print("General clarification needed")
                return clarification_general_question
        else:
            response = await self.invoke_general(
                prompt_input,
                sql_context=sql_context,
                rag_context=rag_context,
                risks_context=risks_context,
                sources_binary=self.conversation_state.context.get("sources_binary"),
            )

        print("General clarification not needed")

        print(f"Invoke default with input: {user_message}")

        print(f"Chatbot response: {response}")
        self.memory_update(user_message, response)
        self.conversation_state.reset()
        await self.update_status(ChatbotState.RESPONSE_PREP)
        if output_documents:
            return (
                response,
                sql_documents_list,
                rag_documents_list,
                risks_documents_list,
            )
        print(
            "sql_documents_list",
            sql_documents_list,
            "rag_documents_list",
            rag_documents_list,
            "risks_documents_list",
            risks_documents_list,
        )
        return response

    def set_other_agreement_type_document_names(self) -> None:
        self.other_agreement_type_document_names = (
            self.retrieve_other_agreement_type_file_names()
        )

    @staticmethod
    def get_agreement_types(agreement_type_key_items: Any) -> List[str]:
        """
        Get unique agreement types as list  from the agreement_type_key_items.
        Input structure agreement_type_key_items:
        [["Site Lease", ["Effective Date"]],
        ["Interconnection Agreement", ["Effective Date"]],
        ["Operating Agreement", ["Parties", "Named Manager"]]]
        Output structure:
        ["Site Lease",
        "Interconnection Agreement",
        "Operating Agreement"]
        :param agreement_type_key_items:
        :return:
        """
        return list(
            set(
                [
                    agreement_type_key_item[0].strip()
                    for agreement_type_key_item in agreement_type_key_items
                ]
            )
        )

    async def update_status(
        self,
        chatbot_state: ChatbotState,
        response_status: ResponseStatus = ResponseStatus.IN_PROGRESS,
        sleep_time: int = 0,
    ) -> None:
        """
        Update the status of the chatbot.
        Status is displayed in the UI (FE).
        :param chatbot_state:
        :param response_status:
        :param sleep_time:
        :return:
        """
        if not self.socket_manager:
            return
        await asyncio.sleep(sleep_time)
        await self.socket_manager.send_chatbot_status(
            chatbot_state, response_status, self.websocket
        )

    async def invoke_dev(self, prompt_input: Dict[str, Any]) -> Any:
        """Prop function to test the Chatbot"""
        await self.update_status(ChatbotState.ANALYZING, sleep_time=1)
        await self.update_status(ChatbotState.COLLECTING_INPUTS, sleep_time=1)
        await self.update_status(ChatbotState.CHECKING_DOCS, sleep_time=1)
        await self.update_status(ChatbotState.CHECKING_PP, sleep_time=1)
        await self.update_status(ChatbotState.COMBINING_CONTEXT, sleep_time=1)
        await self.update_status(ChatbotState.RESPONSE_PREP, sleep_time=1)
        return (
            f"This is a test echo response for DEV environment: "
            f"{prompt_input['human_input']}"
        )

    async def clarify_general(
        self,
        user_message: str,
        sql_context: str | None,
        rag_context: str | None,
        risks_context: str | None,
        **kwargs: Any,
    ) -> str | None:
        """
        Main clarification function for the chatbot.
        :param user_message:
        :param sql_context:
        :param rag_context:
        :param risks_context:
        :param kwargs:
        :return:
        """

        if (
            self.conversation_state.clarification_counter
            == self.conversation_state.clarification_max_retries
        ):
            return None

        flag, questions = await self.general_clarifier.clarify(
            user_message,
            self.get_history(),
            self.other_agreement_type_document_names,
            sql_context=sql_context,
            rag_context=rag_context,
            risks_context=risks_context,
            possible_sources=kwargs.get("possible_sources"),
            possible_agreement_types_key_items=kwargs.get(
                "possible_agreement_types_key_items"
            ),
        )
        if not flag or not questions:
            return None

        assistant_message = questions[0]
        self.conversation_state.next()
        self.memory_update(user_message, assistant_message)
        sys.stdout.flush()
        return assistant_message

    async def get_sql_context(self, agreement_type_key_items: Any) -> Any:
        """
        Get the SQL context for the chatbot.
        :param agreement_type_key_items:
        :return:
        """
        logger.debug(f"Input to get_sql_context: {agreement_type_key_items}")
        await self.update_status(ChatbotState.CHECKING_PP)
        sql_context = ""
        documents_list = []
        for agreement_type, key_items in agreement_type_key_items:
            if agreement_type in self.other_agreement_type_document_names:
                documents = []
            else:
                documents = self.project_preview_retriever.get_project_preview_data_by_agreement_type_key_items(  # noqa
                    agreement_type, key_items
                )
            sql_context += self.format_sql_context(agreement_type, documents)
            documents_list.extend(documents)

        if not sql_context:
            sql_context, documents_list = "No project preview data was retrieved.", []

        logger.info(f"SQL context: {sql_context}")
        return (
            sql_context,
            documents_list,
        )

    async def get_rag_context(
        self,
        user_message: str,
        agreement_types: List[str],
    ) -> Optional[str] | Tuple[Optional[str], List[Document]]:
        """
        Get the RAG context for the chatbot.
        :param user_message:
        :param agreement_types:
        :return:
        """
        logger.debug(f"Input to get_rag_context: {user_message}")
        logger.debug(f"Input to get_rag_context agreement_types: {agreement_types}")
        await self.update_status(ChatbotState.CHECKING_DOCS)

        rag_context = ""
        documents_list = []
        for agreement_type in agreement_types:
            documents = await self.retrieve_documents_from_rag(
                user_message,
                agreement_type.strip(),
                document_name=(
                    agreement_type.strip()
                    if agreement_type.strip()
                    in self.other_agreement_type_document_names
                    else None
                ),
            )
            if not documents:
                continue

            rag_context += self.format_rag_context(documents)
            documents_list.extend(documents)
        logger.info(f"RAG context: {rag_context}")
        return rag_context, documents_list

    def clear_memory(self) -> None:
        """Clear the memory of the chatbot"""
        self.messages_history.clear()
        logger.info("Memory cleared.")

    @staticmethod
    def format_dataframe(df: pd.DataFrame) -> Any:
        """
        Convert a DataFrame to a formatted string.
        :param df: DataFrame to format
        :return: Formatted string
        """
        ans = "\n".join([f"{x['Key Items']} - {x['Value']}" for _, x in df.iterrows()])
        return ans

    def format_sql_context(self, agreement_type: Any, documents: Any) -> str:
        """
        Format the SQL context for the chatbot.
        :param agreement_type:
        :param documents:
        :return:
        """
        ans = ""
        for document in documents:
            ans += (
                doc_string_template(
                    "Project Preview",
                    document["section_name"],
                    document["document_name"],
                    document["file_name"],
                    document["subsection_name"],
                )
                + f"\n{self.format_dataframe(document['data'][0])}"
            )

        if not ans:
            return (
                f"Agreement Type: {agreement_type} \n"
                "No data found in the database. \n\n"
            )
        return ans

    async def invoke_general(
        self,
        prompt_input: Any,
        sql_context: Optional[str] = None,
        rag_context: Optional[str] = None,
        risks_context: Optional[str] = None,
        sources_binary: Optional[bool] = None,
    ) -> Any:
        """
        Main function for building the chatbot response.
        :param prompt_input:
        :param sql_context:
        :param rag_context:
        :param risks_context:
        :param sources_binary:
        :return:
        """

        await self.update_status(ChatbotState.COMBINING_CONTEXT)

        system_message_template = base_system_prompt.replace(
            """<<<data_sources>>>""",
            dialog_examples,
        ).replace(
            "<<<topics>>>",
            list_of_topics,
        )

        human_message_template = (
            base_prompt_template.replace(
                "<<<formatting>>>",
                formatting_prompt,
            )
            .replace(
                "<<<sql_context>>>",
                sql_context_prompt if sources_binary else "",
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
            "user_message": prompt_input["human_input"],
            "history": self.get_history(),
        }

        if sql_context:
            input_dict["sql_context"] = sql_context
        if rag_context:
            input_dict["rag_context"] = rag_context
        if risks_context:
            input_dict["risks_context"] = risks_context

        response = await answer_chain.ainvoke(input_dict)
        sys.stdout.flush()
        return response.content

    def persist_history(
        self, user_id: int, company_id: int, site_id: int, conversation_id: str
    ) -> None:
        """Persist the chatbot history in the database."""
        documents = []
        for idx, message in tqdm(
            enumerate(self.messages_history.messages), desc="Storing chatbot history"
        ):
            document = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "company_id": company_id,
                "site_id": site_id,
                "message": message.content,
                "message_type": message.type,
                "message_index": idx,
            }
            documents.append(document)
        self.retriever.db_connector.store_documents(
            documents=documents, sql_statement=insert_sql_chatbot_history
        )
        logger.info("Chatbot history stored successfully.")

    def retrieve_other_agreement_type_file_names(self) -> List[str]:
        """
        Retrieve the other agreement type document names
        to be able to predict document_names for agreements without project preview.
        :return:
        """
        document_names = self.retriever.get_other_agreement_type_document_names(
            self.site_id, self.company_id
        )
        return [document_name[0] for document_name in document_names]
