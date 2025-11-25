import logging
import os

from pydantic.v1 import BaseSettings

from src.deployment.cloud_run_job.key_value_extraction.env_enum import Env
from src.vectordb.pg_vector.config import (
    PGVectorConfig,
    PGVectorConfigDev,
    PGVectorConfigQA,
    PGVectorConfigUAT,
)


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    secret_key: str = str(os.environ.get("SECRET_KEY"))
    api_key: str = str(os.environ.get("ML_API_KEY"))

    @staticmethod
    def get_pg_vector_config() -> PGVectorConfig:
        """Return the vector database configuration, PGVectorConfig,
        based on the environment."""
        pg_config: PGVectorConfig
        if os.environ.get("ENV") == Env.DEV:
            pg_config = PGVectorConfigDev()
        elif os.environ.get("ENV") == Env.QA:
            pg_config = PGVectorConfigQA()
        elif os.environ.get("ENV") == Env.UAT:
            pg_config = PGVectorConfigUAT()
        elif os.environ.get("ENV") == Env.LOCAL:
            pg_config = PGVectorConfig()
        else:
            logger.info("Environment unrecognised. Using default PGVectorConfig")
            pg_config = PGVectorConfig()
        return pg_config


settings = Settings()
