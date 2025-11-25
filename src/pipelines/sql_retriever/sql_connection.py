import logging
import os
from typing import Any, Optional, Sequence
from urllib.parse import quote

import pandas as pd
import yaml
from sqlalchemy import create_engine, text

from src.deployment.cloud_run_job.key_value_extraction.env_enum import Env
from src.deployment.fast_api.settings import settings
from src.user_interface.auth import get_secret


logger = logging.getLogger(__name__)


class SQLEngine:
    """
    Singleton class for the SQL connection.
    """

    _instance: Optional["SQLEngine"] = None

    def __new__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        if cls._instance is None:
            cls._instance = super(SQLEngine, cls).__new__(cls)
        assert cls._instance is not None
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "engine"):
            self.engine = self.get_engine()

    @staticmethod
    def get_engine() -> Any:
        """
        Get the engine for the SQL connection.
        :return:
        """
        if os.environ.get("ENV") == Env.LOCAL:
            return create_engine(
                f"postgresql://{os.environ['DB_USER']}:"
                f"{quote(os.environ['DB_PASSWORD'])}"
                f"@{os.environ['DB_HOST']}/{os.environ['DB_NAME']}"
            )

        config = settings.get_pg_vector_config()
        parsed_data = yaml.safe_load(
            get_secret(config.get_project_id(), "app-values-creds")
        )

        db_user = quote(parsed_data["env_variables"]["db_user"])
        db_password = quote(parsed_data["env_variables"]["db_password"])
        db_host = f"{config.project}:{config.region}:test-db"
        db_name = quote(parsed_data["env_variables"]["db_name"])

        return create_engine(
            f"postgresql+psycopg2://{db_user}:{db_password}"
            f"@/{db_name}?host=/cloudsql/{db_host}"
        )


class SQLConnector:
    def __init__(self) -> None:
        self.engine = SQLEngine().get_engine()

    def execute_query(self, query: str) -> Any:
        """
        Execute a query and return the result as a pandas DataFrame.
        :param query:
        :return:
        """
        # Connect to the database and ensure the connection is closed after use
        with self.engine.connect() as connection:
            # Execute a query
            return connection.execute(text(query))

    def get_project_preview_values(
        self, site_id: int, document_names: Sequence[str]
    ) -> pd.DataFrame:
        """
        Get a preview of the project data for a given site and document.
        :param site_id:
        :param document_names:
        :return:
        """
        logger.info(f"Chosen documents for SQL query: {document_names}")
        query = self.project_preview_values_sql_query(site_id, document_names)
        ans = self.execute_query(query)

        # Get the column names from the result
        column_names = ans.keys()

        # Convert the rows into a pandas DataFrame
        ans = pd.DataFrame(ans, columns=column_names)

        ans = ans.rename({"name": "Key Items", "value": "Value"}, axis=1)
        return ans

    @staticmethod
    def project_preview_values_sql_query(
        site_id: int, document_names: Sequence[str]
    ) -> str:
        document_names_str: str = ", ".join(
            [f"'{document_name}'" for document_name in document_names]
        )
        query = f"""SELECT 
        dk.document_id, 
        dk.name, 
        dk.value,
        d.name AS document_name, 
        d.site_id, 
        d.section_id, 
        s1.name AS section_name, 
        s1.parent_section_id, 
        s2.name AS parent_section_name,
        f.filepath AS file_path,
        f.filename AS file_name
        FROM (
            SELECT * 
            FROM "public"."document_keys" 
            WHERE document_id IN (
                SELECT id 
                FROM "public"."documents" 
                WHERE site_id = {site_id}
                AND name IN ({document_names_str})
            )
        ) AS dk
        LEFT JOIN "public"."documents" AS d ON dk.document_id = d.id
        LEFT JOIN "public"."document_sections" AS s1 ON d.section_id = s1.id
        LEFT JOIN "public"."document_sections" AS s2 ON s1.parent_section_id = s2.id
        LEFT JOIN "public"."files" AS f ON dk.document_id = f.document_id
        WHERE f.is_actual = TRUE;"""
        return query

    @staticmethod
    def get_ai_parsing_results(site_id: int, document_name: str) -> Any:
        """
        Get a preview of the project data for a given site and document.
        :param site_id:
        :param document_name:
        :return:
        """
        SQLConnector.ai_parsing_results_sql_query()

        raise NotImplementedError("Implement this method")

    @staticmethod
    def ai_parsing_results_sql_query() -> Any:
        query = f"""  
        SELECT result FROM
      "public"."ai_parsing_results"
      WHERE file_id = (SELECT DISTINCT id FROM
      "public"."files"
      WHERE document_id = (SELECT DISTINCT document_id FROM
      "public"."document_keys"
      WHERE document_id = (SELECT DISTINCT id FROM
      "public"."documents"
      WHERE site_id = 33
      AND name = 'subscriber_management_agreement'
      ))
      AND is_actual = TRUE
      )
      AND status = 'completed'
      ORDER BY created_at DESC
      LIMIT 1
      ;"""  # noqa

        raise NotImplementedError("Implement this method")
