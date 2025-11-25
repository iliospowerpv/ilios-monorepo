import os
from typing import Any, List

from langchain_google_vertexai import VertexAIEmbeddings


class VertexAIEmbedder:
    def __init__(self, embedding_model: str = "text-embedding-005") -> None:
        """Initialize the VertexAIEmbedder."""
        self.embedding_client: VertexAIEmbeddings = VertexAIEmbeddings(
            model_name=embedding_model,
            project="prj-ilios-ai",
            location=os.environ["LOCATION"],
        )

    def get_single_embedding(self, text: str, **kwargs: Any) -> List[float]:
        """Get the embedding for a single text."""
        return self.embedding_client.embed([text], **kwargs)[0]

    def get_batch_embeddings(
        self, texts: List[str], **kwargs: Any
    ) -> List[List[float]]:
        """Get the embeddings for a batch of texts."""
        return self.embedding_client.embed(texts, **kwargs)
