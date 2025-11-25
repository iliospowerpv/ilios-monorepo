from pydantic.dataclasses import dataclass


@dataclass
class ChatbotConfig:
    """
    Main configuration class for the chatbot.
    """

    max_documents: int = 5
    use_sql_context: bool = True
    use_clarification: bool = True
    sources_clarification: bool = True
    agreement_type_clarification: bool = True
    clarification_max_retries: int = 1
