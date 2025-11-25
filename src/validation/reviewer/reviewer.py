from typing import Any, List

from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate

from src.gen_ai.gen_ai import get_llm
from src.validation.reviewer.prompts import reviewer_prompt


class Reviewer:
    def __init__(self, model_type: str) -> None:
        """Initialize the reviewer."""
        self.model_type: str = model_type
        self.llm: Any = get_llm(model_type="CLAUDE")
        self.chain: LLMChain = self._build_chain()

    def _build_chain(self) -> LLMChain:
        """Build the LLM chain."""
        prompt = PromptTemplate(
            template=reviewer_prompt,
            input_variables=["key_name", "description", "chunk"],
        )
        review_chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            verbose=True,
        )
        return review_chain

    def run(
        self, key_name: List[str], description: List[str], chunk: List[str]
    ) -> List[str]:
        """
        Run the reviewer.
        """
        responses = self.chain.batch(
            [
                {"key_name": key, "description": description, "chunk": chunk}
                for key, description, chunk in zip(key_name, description, chunk)
            ]
        )
        return [
            response["text"]
            .replace("```json", "")
            .replace("```", "")
            .replace("json", "")
            .strip()
            for response in responses
        ]
