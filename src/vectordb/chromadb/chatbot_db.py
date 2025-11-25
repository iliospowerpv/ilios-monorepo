import logging
import os
from pathlib import Path
from typing import List

import chromadb
from chromadb import Settings
from langchain_community.vectorstores.chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter, TextSplitter

from src.settings import LOCAL_VECTOR_STORE_PATH


logger = logging.getLogger(__name__)


class ChromaDBChatbot:
    def __init__(
        self,
        k: int = 20,
        chunk_size: int = 6000,
        embedding_model: str = "text-embedding-005",
        persistent_client: bool = True,
        db_path: Path = LOCAL_VECTOR_STORE_PATH,
        metadata_key: str = "doc_id",
    ) -> None:
        """Initializes the VectorDB with a k value for the retriever."""
        self.k = k
        self.chunk_size = chunk_size
        self.metadata_key = metadata_key
        self.persistent_client = persistent_client
        self.db_path = db_path
        self.embedding_model = embedding_model
        self.text_splitter = self.get_text_splitter()
        self.embeddings = self.get_embeddings()
        self.vector_store = self.get_vector_store()

    def get_embeddings(self) -> Embeddings:
        """Get the embeddings to be used for the VectorDB."""
        return VertexAIEmbeddings(
            model_name=self.embedding_model,
            project="prj-ilios-ai",
            location=os.environ["LOCATION"],
        )

    def get_text_splitter(self) -> TextSplitter:
        """Get the text splitter to be used for the VectorDB."""
        text_splitter = CharacterTextSplitter(
            separator=".\n",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_size // 3,
            keep_separator=True,
        )
        return text_splitter

    def get_vector_store(self) -> Chroma:
        """Get the vector store to be used for the VectorDB."""
        if self.persistent_client:
            client = chromadb.PersistentClient(
                path=self.db_path.as_posix(),
                settings=Settings(anonymized_telemetry=False),
            )
            chroma = Chroma(
                collection_name="chatbot",
                embedding_function=self.embeddings,
                client=client,
                persist_directory=self.db_path.as_posix(),
                collection_metadata={"hnsw:space": "ip"},
            )
            logger.info(f"Using persistent client: {self.db_path.as_posix()}")
        else:
            chroma = Chroma(
                collection_name="chatbot",
                embedding_function=self.embeddings,
                collection_metadata={"hnsw:space": "ip"},
            )
            logger.info("Setting up new ChromaDB")
        return chroma

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        self.vector_store.add_documents(documents)
