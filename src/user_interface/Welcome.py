import logging.config

import streamlit as st

from src.user_interface.auth import check_password


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


def welcome() -> None:
    """Main function for the Streamlit app."""
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.

    st.write("# Welcome to iliOS DocAI Test App! 👋")
    st.sidebar.success("Select a UI to test from the dropdown on the left.")

    st.markdown(
        """
        ### Here are some basic guidelines for Chatbot prompting:

1. **Be Clear and Detailed:** Help Chatbot understand exactly what you need by being 
    specific in your requests.

2. **Know the Limits:** Learn what Chatbot can and can’t do. It can help you with 
    general questions, but it could miss with some calculations.

3. **Keep It Simple:** Use straightforward language to avoid confusion. Clear prompts 
    lead to better answers.

4. **Try, Try Again:** If the first answer isn’t quite right, tweak your question and 
    ask again. Each attempt can help you get closer to what you’re looking for.

5. **Learn from Responses:** Pay attention to how different prompts affect the answers 
    you get. This can teach you how to ask better questions over time.

6. **Provide Context:** Giving a little extra background can help Chatbot give more 
    accurate and relevant responses.

7. **Experiment:** Test out your prompts in different situations to see how well they 
    work across various topics.


Happy chatting!

    """
    )


if __name__ == "__main__":
    welcome()
