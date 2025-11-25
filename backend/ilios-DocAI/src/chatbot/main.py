import asyncio

from src.chatbot.config import ChatbotConfig
from src.chatbot.modules.base import ChatbotBase
from src.chatbot.prompt_templates.base import base_system_prompt
from src.gen_ai.gen_ai import get_llm


def init_chatbot() -> ChatbotBase:
    """Initialize the chatbot and store as singleton to load only once."""
    chatbot = ChatbotBase(
        config=ChatbotConfig(
            max_documents=5,
        ),
        # site_id=22,
        # company_id=14,
        site_id=50,
        company_id=1,
        llm=get_llm(model_type="CLAUDE", system_prompt=base_system_prompt),
    )
    return chatbot


chatbot = init_chatbot()


async def main() -> None:
    for i in range(20):
        question = input("User: ")
        response = await chatbot.invoke({"human_input": question})
        print("AI:", response)
        print()


if __name__ == "__main__":
    asyncio.run(main())
