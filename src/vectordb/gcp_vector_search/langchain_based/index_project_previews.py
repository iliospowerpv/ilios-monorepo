import logging.config
import os
import pathlib
from pathlib import Path
from typing import List

import click
import pandas as pd
from google.cloud import aiplatform
from langchain_google_vertexai import VectorSearchVectorStore, VertexAIEmbeddings
from tqdm import tqdm

from src.vectordb.gcp_vector_search.transform_and_load import get_file_names


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("input_dir", nargs=1, type=click.Path())
def main(input_dir: pathlib.Path | str) -> None:
    """Main function"""
    embeddings = VertexAIEmbeddings(
        location=os.environ["LOCATION"], model_name="text-embedding-005"
    )
    logger.info(f"Provided path: {input_dir}")
    file_names: List[str] = list(get_file_names(input_dir))
    logger.info(f"Found {len(file_names)} files")
    logger.info(f"Files: {file_names}")
    document_paths: List[Path] = [
        pathlib.Path(input_dir) / file_name for file_name in file_names
    ]
    texts = []
    metadata = []
    for document_path, file_name in tqdm(
        zip(document_paths, file_names), desc="Processing documents"
    ):
        logger.info(f"Processing document: {file_name}")
        pp_data = pd.read_excel(document_path, sheet_name="Project Preview")
        pp_data.fillna("N/A", inplace=True)
        texts.extend([row["Legal Terms"] for _, row in pp_data.iterrows()])
        metadata.extend(
            [
                {
                    "filename": file_name,
                    "key_item": row["Key Items"],
                    "value": row["Value"],
                }
                for _, row in pp_data.iterrows()
            ]
        )

    logger.info("Documents processed")
    logger.info("Initializing VectorDB")
    aiplatform.init(
        project=os.environ["PROJECT_ID"],
        location=os.environ["LOCATION"],
        staging_bucket=os.environ["GCS_VECTOR_STORE_BUCKET"],
    )
    vector_store = VectorSearchVectorStore.from_components(
        project_id=os.environ["PROJECT_ID"],
        region=os.environ["LOCATION"],
        gcs_bucket_name=os.environ["GCS_VECTOR_STORE_BUCKET"],
        index_id=os.environ["VECTOR_STORE_INDEX_ID"],
        endpoint_id=os.environ["VECTOR_STORE_INDEX_ENDPOINT_ID"],
        embedding=embeddings,
    )
    logger.info("Adding documents to VectorDB")
    vector_store.add_texts(texts=texts, metadata=metadata)


if __name__ == "__main__":
    main()
