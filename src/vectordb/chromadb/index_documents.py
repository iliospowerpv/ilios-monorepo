import logging.config
import os
import pathlib
import uuid
from pathlib import Path
from typing import List

import click
from langchain_core.documents import Document

from src.doc_ai.processor import DocAIProcessor
from src.user_interface.pages.Keyword_extraction import agreement_type
from src.vectordb.chromadb.chatbot_db import ChromaDBChatbot
from src.vectordb.gcp_vector_search.transform_and_load import get_file_names


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("file_dir", nargs=1, type=click.Path())
@click.argument("agreement_type", nargs=1, type=click.STRING)
def main(file_dir: str | Path) -> None:
    """Process documents and put into the local ChromaDB storage."""
    file_names: List[str] = list(get_file_names(file_dir))
    document_paths: List[Path] = [
        pathlib.Path(file_dir) / file_name
        for file_name in file_names
        if file_name.endswith(".pdf")
    ]
    logger.info(f"Processing {len(document_paths)} documents")
    processor = DocAIProcessor(
        location=os.environ["DOC_AI_LOCATION"],
        project_id=os.environ["PROJECT_ID"],
        processor_id=os.environ["DOC_AI_PROCESSOR_ID"],
    )
    # chroma_db = ChromaDBChatbot(db_path=pathlib.Path("src/chatbot/validation"))
    chroma_db = ChromaDBChatbot()
    documents: List[Document] = []
    for document_path, file_name in zip(document_paths, file_names):

        doc_sequence = processor.process_documents(document_list=[document_path])
        doc_text = doc_sequence.get_all_text()
        # The metadata for the document
        metadata = {
            "doc_id": str(uuid.uuid4()),
            "file_name": file_name,
            "agreement_type": agreement_type,
        }
        doc_chunks = chroma_db.text_splitter.create_documents([doc_text], [metadata])

        # Create a Document instance
        documents.extend(doc_chunks)

    logger.info("Saving documents to ChromaDB")
    logger.info(f"Docs in Chroma: {len(chroma_db.vector_store.get()['documents'])}")
    chroma_db.add_documents(documents)
    chroma_db.vector_store.persist()
    logger.info(
        f"Docs in Chroma after add: {len(chroma_db.vector_store.get()['documents'])}"
    )
    logger.info("Pipeline finished")


if __name__ == "__main__":
    main()
