import enum


class ChatbotState(str, enum.Enum):
    """Chatbot response status indication - passed to the User"""

    READY = "Chatbot Ready"
    ANALYZING = "Analyzing your question"
    COLLECTING_INPUTS = "Gathering Information"
    CHECKING_PP = "Checking Project Previews"
    CHECKING_DOCS = "Checking Documents"
    ANALYZING_RISK = "Analyzing Potential Risks"
    COMBINING_CONTEXT = "Summarizing Findings"
    RESPONSE_PREP = "Crafting your response"
    RESPONSE_SEND = "Sending your response"
    ERROR = "Something went wrong"


class ResponseStatus(enum.Enum):
    """Response status for the chatbot"""

    AWAITING_DATA = "Waiting for query"
    COMPLETE = "Complete"
    IN_PROGRESS = "In Progress"
    ERROR = "Error"
