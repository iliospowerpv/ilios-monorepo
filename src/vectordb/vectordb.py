import logging
import uuid
from typing import Dict, List, Optional

import pandas as pd
from langchain.retrievers import EnsembleRetriever
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryByteStore
from langchain.text_splitter import CharacterTextSplitter, TextSplitter
from langchain_community.retrievers import TFIDFRetriever
from langchain_community.vectorstores import Chroma
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.doc_ai.file_sequence import FileSequence


logger = logging.getLogger(__name__)


class VectorDB:
    def __init__(
        self,
        k: int = 20,
        chunk_size: int = 600,
        add_tables: bool = True,
        overlap_factor: int = 3,
    ) -> None:
        """Initializes the VectorDB with a k value for the retriever."""
        self.overlap_factor = overlap_factor
        self.k = k
        self.chunk_size = chunk_size
        self.add_tables = add_tables
        self.text_splitter = self.get_text_splitter()
        self.embeddings = self.get_embeddings()

    @staticmethod
    def get_embeddings() -> Embeddings:
        """Get the embeddings to be used for the VectorDB."""
        return VertexAIEmbeddings(
            model_name="text-embedding-005", project="prj-ilios-ai"
        )

    def get_text_splitter(self) -> TextSplitter:
        """Get the text splitter to be used for the VectorDB."""
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_size // self.overlap_factor,
            keep_separator=True,
        )
        logger.info(f"CHUNK_SIZE: {self.chunk_size}")

        return text_splitter

    def retriever_from_file_sequence(
        self, file_sequence: FileSequence
    ) -> BaseRetriever:
        """Creates a retriever from a given text."""
        docs = self.text_docs_from_file_sequence(file_sequence)

        if self.add_tables:
            retriever = TFIDFRetriever.from_documents(docs)
            table_docs = self.table_docs_from_file_sequence(file_sequence)
            if not table_docs:
                return retriever
            tables_retriever = self.multi_vector_retriever_from_documents(table_docs)
            ensemble_retriever = EnsembleRetriever(
                retrievers=[retriever, tables_retriever], weights=[0.95, 0.05]
            )
            return ensemble_retriever
        else:
            return CustomRetriever(documents=docs, k=self.k)

    def text_docs_from_file_sequence(
        self, file_sequence: FileSequence
    ) -> List[Document]:
        """Creates a list of documents from the text in the file sequence."""
        text = file_sequence.get_all_text()
        docs = self.text_splitter.create_documents([text])
        logger.info(f"CHUNK_LENGTHS: {[len(doc.page_content) for doc in docs]}")
        return docs

    @staticmethod
    def dataframe_to_string(df: pd.DataFrame) -> str | pd.DataFrame:
        """Converts a dataframe to a string."""
        return df.to_string(index=False)

    def table_docs_from_file_sequence(
        self, file_sequence: FileSequence
    ) -> List[Document]:
        """Creates a list of documents from the tables in the file sequence."""
        tables = [
            self.dataframe_to_string(table) for table in file_sequence.get_tables()
        ]
        docs = [Document(table) for table in tables]
        return docs

    def multi_vector_retriever_from_documents(
        self, docs: List[Document]
    ) -> MultiVectorRetriever:
        """Creates a MultiVectorRetriever from a list of documents."""
        vectorstore = Chroma(
            collection_name="full_documents", embedding_function=self.embeddings
        )
        # The storage layer for the parent documents
        store = InMemoryByteStore()
        id_key = "doc_id"
        # The retriever (empty to start)
        retriever = MultiVectorRetriever(
            vectorstore=vectorstore,
            byte_store=store,
            docstore=store,  # type: ignore
            id_key=id_key,
        )
        doc_ids = [str(uuid.uuid4()) for _ in docs]

        # The splitter to use to create smaller chunks
        child_text_splitter = RecursiveCharacterTextSplitter(
            chunk_overlap=100, chunk_size=500
        )
        sub_docs = []
        for i, doc in enumerate(docs):
            _id = doc_ids[i]
            _sub_docs = child_text_splitter.split_documents([doc])
            for _doc in _sub_docs:
                _doc.metadata[id_key] = _id
            sub_docs.extend(_sub_docs)
        retriever.vectorstore.add_documents(sub_docs)
        retriever.docstore.mset(list(zip(doc_ids, docs)))

        return retriever


class CustomRetriever(BaseRetriever):
    """A custom retriever that retrieves documents based on a user query.

    This retriever only implements the sync method _get_relevant_documents.

    If the retriever were to involve file access or network access, it could benefit
    from a native async implementation of `_aget_relevant_documents`.

    As usual, with Runnables, there's a default async implementation that's provided
    that delegates to the sync implementation running on another thread.
    """

    documents: List[Document]
    """List of documents to retrieve from."""
    k: int
    """Number of top results to return"""

    docstore: Optional[Dict[str, Document]] = None

    retriever: Optional[TFIDFRetriever] = None

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    def __init__(self, *args, **kwargs) -> None:  # type: ignore # noqa: E501
        """Initializes the ToyRetriever."""
        super().__init__(*args, **kwargs)

        doc_ids = [str(uuid.uuid4()) for _ in self.documents]

        for doc_id, doc in zip(doc_ids, self.documents):
            doc.metadata["doc_id"] = doc_id

        self.docstore = dict(zip(doc_ids, self.documents))

        # The splitter to use to create smaller chunks
        child_text_splitter = RecursiveCharacterTextSplitter(
            chunk_overlap=50, chunk_size=500
        )
        sub_docs_all = []
        for i, doc in enumerate(self.documents):
            doc_id = doc_ids[i]
            sub_docs = child_text_splitter.split_documents([doc])
            for sub_doc in sub_docs:
                sub_doc.metadata["doc_id"] = doc_id
                sub_doc.metadata["sub_doc_id"] = f"{doc_id}_{i}"
            sub_docs_all.extend(sub_docs)

        self.retriever = TFIDFRetriever.from_documents(
            sub_docs_all + self.documents
        )  # noqa: E501 # type: ignore
        self.retriever.k = self.k * 5

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Returns the top k documents that contain the user query."""

        subdocs = self.retriever.invoke(query)  # type: ignore

        uqnique_full_doc_ids = set()
        for subdoc in subdocs:
            uqnique_full_doc_ids.add(subdoc.metadata["doc_id"])
            if len(uqnique_full_doc_ids) == self.k:
                break

        return [
            self.docstore[doc_id] for doc_id in uqnique_full_doc_ids  # type: ignore
        ]  # noqa: E501
