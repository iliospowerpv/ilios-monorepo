"""
Memory Summarization Module for the Chatbot.
"""

import json
import queue
from typing import Any, Dict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.chatbot.prompt_templates.base import mem_summary_template


class MemorySummarizer:
    """
    Memory Summarizer module for the chatbot.
    """

    def __init__(
        self,
        size: int,
        llm: Any,
        ai_role: str = "assistant",
        human_role: str = "user",
        return_messages: bool = True,
        summary_max_len: int = 500,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the SummarizerMemory.
        :param size:
        :param llm:
        :param ai_role:
        :param human_role:
        :param return_messages:
        :param summary_max_len:
        :param kwargs:
        """
        self.size = size
        self.ai_role = ai_role
        self.human_role = human_role
        self.return_messages = return_messages
        self.window = queue.Queue(maxsize=self.size)  # type: ignore
        self.summary = ""
        self.summary_max_len = summary_max_len
        self.llm = llm
        self.model_kwargs = kwargs

    def clear(self) -> None:
        self.window = queue.Queue(maxsize=self.size)
        self.summary = ""

    def _msg_to_str(self, inputs: Dict[str, Any]) -> str:
        return (
            f"{self.human_role}: {inputs.get(self.human_role)}"
            f"\n{self.ai_role}: {inputs.get(self.ai_role)}\n"
        )

    def _msg_to_msg(self, inputs: Dict[str, Any]) -> tuple[BaseMessage, BaseMessage]:
        human_message = HumanMessage(
            content=inputs.get(self.human_role)  # type: ignore
        )
        ai_message = AIMessage(content=inputs.get(self.ai_role))  # type: ignore
        return human_message, ai_message

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        input = inputs.pop(self.human_role)
        input_kwargs = inputs

        output = outputs.pop(self.ai_role)
        output_kwargs = outputs

        payload = {
            self.human_role: input,
            self.ai_role: output,
        }

        if input_kwargs:
            payload.update({f"{self.human_role}_kwargs": input_kwargs})

        if output_kwargs:
            payload.update({f"{self.ai_role}_kwargs": output_kwargs})
        if not self.window.full():
            self.window.put(payload)
            return

        oldest = self.window.get()
        self.window.put(payload)
        self._extend_summary(oldest)

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        messages = []
        if self.summary:
            if self.return_messages:
                prompt = HumanMessage(
                    content="Provide a summary of earlier conversation"
                )
                summary = AIMessage(content=self.summary)
                messages.extend([prompt, summary])
            else:
                summary = f"Summary of earlier messages: {self.summary}"  # type: ignore
                messages.append(summary)

        for msg in list(self.window.queue):
            if self.return_messages:
                messages.extend(self._msg_to_msg(msg))
                continue
            messages.append(self._msg_to_str(msg))  # type: ignore

        if inputs:
            print(inputs)
            if self.return_messages and inputs.get(self.human_role):
                messages.append(
                    HumanMessage(content=inputs.get(self.human_role))  # type: ignore
                )
            elif inputs.get(self.human_role):
                messages.append(
                    f"{self.human_role}:"
                    f" {inputs.get(self.human_role)}"  # type: ignore
                )

        return {"history": messages}

    def _extend_summary(self, oldest: Dict[str, Any]) -> None:
        prompt = (
            mem_summary_template.replace("<<<n_words>>>", str(self.summary_max_len))
            .replace("<<<summary>>>", self.summary)
            .replace("<<<message>>>", self._msg_to_str(oldest))
        )

        messages = [{"role": "user", "content": prompt}]

        body = json.dumps(
            {
                "messages": messages,
                "system": "You are a specialist in text summarization",
                **self.model_kwargs,
            }
        )

        response = self.llm.invoke(body)
        self.summary = response.content
        return
