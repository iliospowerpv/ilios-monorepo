# Transform files into chunks of text, embed, dump as JSONline files, and load into
# VectorDB in GCP
import json
import logging.config
import os
import time
from pathlib import Path
from typing import Any, Generator, List

import click
import pandas as pd
from google.cloud import aiplatform, storage
from google.cloud.storage import Client
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter, TextSplitter
from tqdm import tqdm
from vertexai.language_models import TextEmbeddingModel

from src.doc_ai.file_sequence import FileSequence
from src.doc_ai.processor import DocAIProcessor
from src.doc_ai.utils import dataframe_to_string, dict_to_string
from src.settings import PROJECT_ROOT_PATH


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


def get_text_splitter() -> TextSplitter:
    """Get the text splitter to be used for the VectorDB."""
    text_splitter = CharacterTextSplitter(
        separator=".\n",
        chunk_size=600,
        chunk_overlap=600 // 2,
    )
    return text_splitter


def document_chunking(
    file_sequence: FileSequence,
    add_tables_and_form_fields: bool = True,
    split_tables_and_form_fields: bool = False,
) -> List[Document]:
    """Chunk the document into smaller pieces for the vector database."""
    text = file_sequence.get_all_text()
    text_splitter = get_text_splitter()
    tables = [dataframe_to_string(table) for table in file_sequence.get_tables()]
    form_fields = [dict_to_string(fields) for fields in file_sequence.get_form_fields()]

    docs = text_splitter.create_documents([text])
    if add_tables_and_form_fields:
        if split_tables_and_form_fields:
            docs.extend(text_splitter.create_documents(tables))
            docs.extend(text_splitter.create_documents(form_fields))
        else:
            docs.extend(Document(table) for table in tables)
            docs.extend(Document(form_field) for form_field in form_fields)
    return docs


def single_text_embedding(
    text: str, model_name: str = "text-embedding-005"
) -> Any:
    """get single text embedding with a Large Language Model.
    Returns: List[float]: Embedding of the text."""
    model: TextEmbeddingModel = TextEmbeddingModel.from_pretrained(model_name)
    embeddings: Any = model.get_embeddings([text])
    return embeddings[0].values


def batch_embeddings(
    texts: List[str], model_name: str = "text-embedding-005"
) -> List[List[float]]:
    """Get batch text embeddings with a Large Language Model."""
    model: TextEmbeddingModel = TextEmbeddingModel.from_pretrained(model_name)
    embeddings: Any = model.get_embeddings(texts)
    return [embedding.values for embedding in embeddings]


def create_folder(
    bucket_name: str, destination_folder_name: str, client: Client
) -> None:
    """Create a folder in the bucket."""
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(destination_folder_name)

    blob.upload_from_string("")

    print("Created {} .".format(destination_folder_name))


def upload_blob(
    bucket_name: str,
    source_file_name: str | Path,
    destination_folder: str,
    destination_file_name: str,
) -> str:
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    create_folder(bucket_name, destination_folder, storage_client)
    bucket = storage_client.bucket(bucket_name)
    destination_path = destination_folder + "/" + destination_file_name
    blob = bucket.blob(destination_path)

    blob.upload_from_filename(source_file_name)

    logger.info(f"File {source_file_name} uploaded to {blob.name}.")
    blob_name = "gs://" + bucket_name + "/" + destination_path
    return str(blob_name)


def get_file_names(path: str | Path) -> Generator[str, None, None]:
    """
    Get the file names from the given directory.
    Returns only file names without the path
    """
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)) and not file.startswith("."):
            yield file


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("file_dir", nargs=1, type=click.Path())
def main(file_dir: str) -> None:
    """Main function to process the documents and load them into the VectorDB."""
    version = time.strftime("%Y%m%d-%H%M%S")
    suffix = "_site_lease"
    chunks_filename = f"chunks_working{suffix}.json"
    index_display_name = f"chatbot_docs_working{suffix}"
    endpoint_display_name = f"chatbot_docs_endpoint_working{suffix}"
    # Choose directory to load files from
    file_names: List[str] = list(get_file_names(file_dir))
    document_paths: List[Path] = [
        PROJECT_ROOT_PATH / f"data/documents/{file_name}" for file_name in file_names
    ]
    chunks: pd.DataFrame = pd.DataFrame(
        data={"id": [], "file_name": [], "text": [], "embedding": []}
    )
    processor = DocAIProcessor(
        location=os.environ["DOC_AI_LOCATION"],
        project_id=os.environ["PROJECT_ID"],
        processor_id=os.environ["DOC_AI_PROCESSOR_ID"],
    )
    i = 1
    for document_path, file_name in tqdm(
        zip(document_paths, file_names), desc="Processing documents"
    ):
        doc_sequence = processor.process_documents(document_list=[document_path])
        docs = document_chunking(doc_sequence)
        chunks = pd.concat(
            [
                chunks,
                pd.DataFrame(
                    data={
                        "id": [int(i + j) for j in range(len(docs))],
                        "text": [doc.page_content for doc in docs],
                        "file_name": [file_name for _ in docs],
                        "embedding": batch_embeddings(
                            [doc.page_content for doc in docs]
                        ),
                    }
                ),
            ]
        )
        i += len(docs)
    chunks["id"] = chunks["id"].astype(int)
    output_path = PROJECT_ROOT_PATH / "data" / chunks_filename

    with open(output_path, "w") as f:
        embeddings_formatted = [
            json.dumps(
                {
                    "id": str(index),
                    "filename": str(row.file_name),
                    "text": row.text,
                    "embedding": [str(value) for value in row.embedding],
                }
            )
            + "\n"
            for index, row in chunks.iterrows()
        ]
        f.writelines(embeddings_formatted)

    blob_url = upload_blob(
        "cloud-ai-platform-458b4ded-772b-441a-9faf-173c984099b6",
        output_path,
        f"chatbot/chunks_dump{version}/",
        destination_file_name=chunks_filename,
    )
    aiplatform.init(project=os.environ["PROJECT_ID"], location=os.environ["LOCATION"])
    new_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=index_display_name,
        contents_delta_uri=blob_url.replace(blob_url.split("/")[-1], ""),
        dimensions=768,
        approximate_neighbors_count=10,
    )
    my_index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=endpoint_display_name, public_endpoint_enabled=True
    )
    my_index_endpoint = my_index_endpoint.deploy_index(
        index=new_index, deployed_index_id=endpoint_display_name
    )

    logger.info(f"Deployed index on endpoint: {my_index_endpoint.deployed_indexes}")


if __name__ == "__main__":
    main()
