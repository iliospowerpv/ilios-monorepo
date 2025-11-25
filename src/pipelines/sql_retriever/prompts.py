# flake8: noqa
from typing import List

from langchain.prompts import Prompt


def get_agreement_type_prompt(agreement_types: List[str]) -> Prompt:
    agreement_types_string = "\n".join(
        f"- {agreement_type}" for agreement_type in agreement_types
    )

    return Prompt.from_template(
        f"""
### TASK ###
IDENTIFY which agreement type best corresponds to the provided question based on the available options.

### INPUT ###
Question: {{question}}

### AGREEMENT TYPES ###
{agreement_types_string}

### OUTPUT ###
AGREEMENT TYPE: [Please specify the agreement type that matches the question]

### INSTRUCTIONS ###
- REVIEW the given question.
- ANALYZE the content and identify the context of the question.
- MATCH the question to the most relevant agreement type listed above.
- PROVIDE the corresponding agreement type in the output.
- If there’s ambiguity, select the most plausible agreement type based on common industry usage.

### WHAT NOT TO DO ###
- DO NOT provide multiple agreement types—choose only one.
- DO NOT return an unrelated agreement type.
- DO NOT guess without sufficient information.
"""
    )


def get_key_items_prompt(available_key_items: List[str]) -> Prompt:
    key_items_string = "\n".join(f"- {key_item}" for key_item in available_key_items)
    return Prompt.from_template(
        f"""
### TASK ###
IDENTIFY which key items best corresponds to the provided question based on the available options.

### INPUT ###
Question: {{question}}

### KEY ITEMS ###
{key_items_string}

### OUTPUT ###
KEY ITEMS: [Please specify the list of key items that matches the question, key_item_1, key_item_2, ... ]

### INSTRUCTIONS ###
- REVIEW the given question.
- ANALYZE the content and identify the context of the question.
- MATCH the question to the most relevant key items listed above.
- PROVIDE the corresponding key items type in the output.
- If there’s ambiguity, select the most plausible key items based on common industry usage.

### WHAT NOT TO DO ###
- DO NOT return an unrelated key items.
- DO NOT guess without sufficient information.
"""
    )


def get_agreement_type_prompt_with_history(agreement_types: List[str]) -> Prompt:
    agreement_types_string = "\n".join(
        f"- {agreement_type}" for agreement_type in agreement_types
    )

    return Prompt.from_template(
        f"""
### TASK ###
IDENTIFY which agreement type best corresponds to the provided question based on the available options.

### INPUT ###
Question: {{question}}

### AGREEMENT TYPES ###
{agreement_types_string}

### OUTPUT ###
AGREEMENT TYPE: [Please specify the agreement type that matches the question]

### INSTRUCTIONS ###
- REVIEW the given question.
- ANALYZE the content and identify the context of the question.
- MATCH the question to the most relevant agreement type listed above.
- PROVIDE the corresponding agreement type in the output.
- If there’s ambiguity, select the most plausible agreement type based on common industry usage.

### WHAT NOT TO DO ###
- DO NOT provide multiple agreement types—choose only one.
- DO NOT return an unrelated agreement type.
- DO NOT guess without sufficient information.
"""
    )


agreement_type_classification_system_prompt = """
You are a robust and well-trained intent classifier designed to identify which agreement types are needed to user.
Your task is to analyze the provided user message and return a list of agreement types, that can provide value with contextual search. Analyze chat history to understand the context.
"""

agreement_type_classification_template = """
You are a robust and well-trained intent classifier designed to identify which agreement types to use for accurate response. 

<task>
Your task is to analyze the provided user message and return agreement types, that can provide value with contextual search. Analyze chat history to understand the context.
- Query can be classified with one agreement type.
- Return the agreement type in a Python list. Example: ["Site Lease Agreement"]
- If NONE of the agreement types are relevant, return an empty list: []
</task>

Use list of agreement types to guide you.
<agreement_types>
{agreement_types_string}
</agreement_types> 

<formatting>
Return only the Python list. Do not return anything else.
</formatting>

Conversation history:
<conversation_history>
{history}
</conversation_history>

Use message:
{user_message}
"""

key_items_classification_system_prompt = """
You are a robust and well-trained intent classifier designed to identify which key items are needed to user.
Your task is to analyze the provided user message and return a list of key items, that can provide value with contextual search. Analyze chat history to understand the context.
"""

key_items_classification_template = """
You are a robust and well-trained intent classifier designed to identify which key items to use for accurate response. 

<task>
Your task is to analyze the provided user message and return key items, that can provide value with contextual search. Analyze chat history to understand the context.
- Return the key items in a Python list. Example: ["Lessor", "Provider", ...]
- If NONE of the key items are relevant, return an empty list: []
</task>

Use list of key items to guide you.
<key_items>
{key_items_string}
</key_items> 

<formatting>
Return only the Python list. Do not return anything else.
</formatting>

Conversation history:
<conversation_history>
{history}
</conversation_history>

Use message:
{user_message}
"""


def get_key_items_prompt_with_history(available_key_items: List[str]) -> Prompt:
    key_items_string = "\n".join(f"- {key_item}" for key_item in available_key_items)
    return Prompt.from_template(
        f"""
### TASK ###
IDENTIFY which key items best corresponds to the provided question based on the available options.

### INPUT ###
Question: {{question}}

### KEY ITEMS ###
{key_items_string}

### OUTPUT ###
KEY ITEMS: [Please specify the list of key items that matches the question, key_item_1, key_item_2, ... ]

### INSTRUCTIONS ###
- REVIEW the given question.
- ANALYZE the content and identify the context of the question.
- MATCH the question to the most relevant key items listed above.
- PROVIDE the corresponding key items type in the output.
- If there’s ambiguity, select the most plausible key items based on common industry usage.

### WHAT NOT TO DO ###
- DO NOT return an unrelated key items.
- DO NOT guess without sufficient information.
"""
    )
