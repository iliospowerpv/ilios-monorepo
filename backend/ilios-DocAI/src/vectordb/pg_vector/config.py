import os

from pydantic import dataclasses

from src.deployment.cloud_run_job.key_value_extraction.env_enum import Env


@dataclasses.dataclass
class PGVectorConfig:
    """Configuration for the PostgreSQL vector store. Base class contains configuration
    for local environment."""

    chatbot_documents_table_name: str = "document_embeddings"
    database_name: str = "chatbot-documents"
    user: str = "chatbot"
    vector_store_instance_name: str = "chatbot-vector-store"
    region: str = "us-west1"
    project: str = "prj-ilios-ai"
    host: str = "/cloudsql/prj-ilios-ai:us-west1:chatbot-vector-store"
    ip_type: str = "PUBLIC"

    def get_project_id(self) -> str:
        """Get the project ID based on the environment."""
        if os.environ.get("ENV") in [Env.DEV, Env.QA, Env.UAT]:
            return self.project
        else:
            try:
                return os.environ["PROJECT_ID"]
            except KeyError:
                raise KeyError("Project ID not found in environment variables.")


@dataclasses.dataclass
class PGVectorConfigDev(PGVectorConfig):
    """Configuration for the PostgreSQL vector store in the DEV environment."""

    region: str = "us-west1"
    vector_store_instance_name: str = "chatbot-vector-store-dev"
    project: str = "prj-dev-base-e61d"
    host: str = "/cloudsql/prj-dev-base-e61d:us-west1:chatbot-vector-store-dev"
    ip_type: str = "PRIVATE"


@dataclasses.dataclass
class PGVectorConfigQA(PGVectorConfig):
    """Configuration for the PostgreSQL vector store in the QA environment."""

    region: str = "us-central1"
    vector_store_instance_name: str = "chatbot-vector-store-qa"
    project: str = "prj-qa-base-23d1"
    host: str = "/cloudsql/prj-qa-base-23d1:us-central1:chatbot-vector-store-qa"
    ip_type: str = "PRIVATE"


@dataclasses.dataclass
class PGVectorConfigUAT(PGVectorConfig):
    """Configuration for the PostgreSQL vector store in the UAT environment."""

    region: str = "us-central1"
    vector_store_instance_name: str = "chatbot-vector-store-uat"
    project: str = "prj-uat-base-70ab"
    host: str = "/cloudsql/prj-uat-base-70ab:us-central1:chatbot-vector-store-uat"
    ip_type: str = "PRIVATE"
