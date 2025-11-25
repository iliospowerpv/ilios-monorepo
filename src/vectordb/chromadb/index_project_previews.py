import logging.config
import pathlib
import uuid
from pathlib import Path
from typing import List

import click
import pandas as pd
from langchain_core.documents import Document
from tqdm import tqdm

from src.vectordb.chromadb.chatbot_db import ChromaDBChatbot
from src.vectordb.gcp_vector_search.transform_and_load import get_file_names


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("input_dir", nargs=1, type=click.Path())
def main(input_dir: pathlib.Path | str) -> None:
    """Main function"""
    logger.info(f"Provided path: {input_dir}")
    file_names: List[str] = list(get_file_names(input_dir))
    logger.info(f"Found {len(file_names)} files")
    logger.info(f"Files: {file_names}")
    document_paths: List[Path] = [
        pathlib.Path(input_dir) / file_name for file_name in file_names
    ]
    documents: list[Document] = []
    for document_path, file_name in tqdm(
        zip(document_paths, file_names), desc="Processing documents"
    ):
        logger.info(f"Processing document: {file_name}")
        pp_data = pd.read_excel(document_path, sheet_name="Project Preview")
        pp_data.dropna(inplace=True)
        documents.extend(
            [
                Document(
                    row["Legal Terms"],
                    metadata={
                        "doc_id": str(uuid.uuid4()),
                        "file_name": file_name,
                        "key_item": row["Key Items"],
                        "value": row["Value"],
                    },
                )
                for _, row in pp_data.iterrows()
            ]
        )

    logger.info("Documents processed")
    chroma_db = ChromaDBChatbot()
    logger.info("Saving documents to ChromaDB")
    logger.info(f"Docs in Chroma: {len(chroma_db.vector_store.get()['documents'])}")
    chroma_db.add_documents(documents)
    logger.info(
        f"Docs in Chroma after add: {len(chroma_db.vector_store.get()['documents'])}"
    )
    logger.info("Pipeline finished")


if __name__ == "__main__":
    main()
