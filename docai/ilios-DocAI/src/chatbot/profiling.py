import asyncio
import cProfile
import time

from src.chatbot.config import ChatbotConfig
from src.chatbot.modules.base import ChatbotBase
from src.gen_ai.gen_ai import get_llm


def init_chatbot() -> ChatbotBase:
    """Initialize the chatbot and store as singleton to load only once."""
    chatbot = ChatbotBase(
        config=ChatbotConfig(
            max_documents=5,
            use_clarification=False,
        ),
        site_id=22,
        company_id=14,
        llm=get_llm(model_type="CLAUDE"),
    )
    return chatbot


chatbot = init_chatbot()


def main() -> None:
    from main import chatbot

    test_set = [
        "Can you please help me to identify all the key items and the risks in interconnection agreement?",  # noqa
        "Give me effective date for interconnection agreement from project preview in database",  # noqa
        "Give me risks for Operating Agreement",
        "Give me risks for Loan Agreement",
        "Retrieve for me all force majeure sections available for agreement types",
        "Retrieve for me effective date for Site Lease and Interconnection Agreement, and provider for Operating Agreement",  # noqa
        "Retrieve for me effective date for Site Lease and Interconnection Agreement, and provider for Operating Agreement",  # noqa
    ]

    time_elapsed = []
    for test in test_set:
        start_time = time.time()
        asyncio.run(chatbot.invoke({"human_input": test}))
        end_time = time.time()

        time_elapsed.append(end_time - start_time)

    print(f"Total time taken for {len(test_set)} queries: {sum(time_elapsed)} seconds")
    print(
        f"Average time taken for each query: {sum(time_elapsed)/len(test_set)} seconds"
    )
    for i, test in enumerate(test_set):
        print(f"    Time taken for query {i+1}: {time_elapsed[i]} seconds")
    print(f"Minimum time taken for a query: {min(time_elapsed)} seconds")
    print(f"Maximum time taken for a query: {max(time_elapsed)} seconds")


def profile_async_func() -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    main()
    profiler.disable()
    profiler.dump_stats("profile_output.prof")


if __name__ == "__main__":
    profile_async_func()
