import os
import pathlib


PROJECT_ROOT_PATH = pathlib.Path(os.environ["PWD"])

GCS_BUCKET_PATH = "gs://doc_ai_storage"

OUTPUT_RESULTS_PATH = "output.csv"

CHATBOT_VALIDATION = PROJECT_ROOT_PATH / "data/chatbot/validation_set"

LOCAL_VECTOR_STORE_PATH = PROJECT_ROOT_PATH / "src/vectordb/chromadb/db"

DATA_FOLDER = PROJECT_ROOT_PATH / "doc_ai_storage"
