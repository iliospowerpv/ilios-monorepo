"""
Conversation state module for the chatbot.
"""

from typing import Any, Dict


class ConversationState:
    """
    Class to keep track of the state of the conversation.
    """

    def __init__(self, clarification_max_retries: int = 2) -> None:
        """
        Initialize the ConversationState.
        :param clarification_max_retries:
        """
        super().__init__()
        self.sources_clarification_done = False
        self.agreement_type_clarification_done = False
        self.general_clarification_needed = False
        self.clarification_counter = 0
        self.clarification_max_retries = clarification_max_retries
        self.context: Dict[str, Any] = {}

    def reset(self) -> None:
        """
        Reset the conversation state.
        Used when outputted answer for invoke_general.
        :return:
        """
        self.clarification_counter = 0
        self.general_clarification_needed = False
        self.context = {}

    def next(self) -> None:
        """
        Move to the next state.
        Used whe general clarification was performed
        and we expect to continue with the classification.
        :return:
        """
        self.general_clarification_needed = True
        self.clarification_counter += 1
