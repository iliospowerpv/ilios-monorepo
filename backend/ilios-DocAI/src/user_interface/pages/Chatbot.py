import asyncio
import logging
from typing import Any

import streamlit as st

from src.chatbot.config import ChatbotConfig
from src.chatbot.modules.base import ChatbotBase
from src.chatbot.prompt_templates.base import base_system_prompt
from src.gen_ai.gen_ai import get_llm
from src.user_interface.auth import check_password


logger = logging.getLogger(__name__)


@st.cache_resource
def init_chatbot() -> ChatbotBase:
    """Initialize the chatbot and store as singleton to load only once."""
    chatbot = ChatbotBase(
        site_id=22,
        config=ChatbotConfig(),
        company_id=14,
        llm=get_llm(model_type="CLAUDE", system_prompt=base_system_prompt),
    )
    return chatbot


chatbot = init_chatbot()

if not check_password():
    st.stop()


def generate_response(question: str) -> Any:
    """Generate a response for a given prompt."""
    try:
        chatbot_response = asyncio.run(chatbot.invoke({"human_input": question}))
    except Exception as e:
        logger.error(f"Error in chatbot invocation: {e}")
        chatbot_response = (
            "I'm sorry, there was an error processing your request. Please try again."
        )
    return chatbot_response


if not check_password():
    st.stop()  # Do not continue if check_password is not True.


project = "Bullrock Lakeville"

st.title("IliOS Chatbot App 🤖")
st.markdown(f"You can ask me about information related to {project} project.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input(
    f"Hi! What would you like to know about {project} project?",
):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Let me think..."):
        response = generate_response(prompt)
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

reset_button = st.button("Clear conversation")
if reset_button:
    st.session_state.messages = []
    chatbot.clear_memory()
    st.rerun()
