import logging
from typing import Any, Dict, List
from urllib.parse import quote

from sqlalchemy import create_engine, text
from typing_extensions import LiteralString

from src.user_interface.auth import get_secret
from src.vectordb.pg_vector.config import PGVectorConfig
from src.vectordb.pg_vector.sql import insert_sql


logger = logging.getLogger(__name__)


class PGVectorConnector:
    """Class used to connect to the PGVector database."""

    def __init__(self, config: PGVectorConfig) -> None:
        """Initialize the PGVectorConnector with the given configuration."""
        self.config: PGVectorConfig = config
        logger.info(f"PGVectorConnector initialized with config: {config.__dict__}")
        self.engine = self.get_engine()

    def get_engine(self) -> Any:
        """
        Get the engine for the SQL connection.
        :return:
        """
        db_user = quote(self.config.user)
        db_password = quote(
            get_secret(self.config.get_project_id(), "chatbot-database-creds")
        )
        db_host = quote(self.config.host)
        db_name = quote(self.config.database_name)

        return create_engine(
            f"postgresql+psycopg2://{db_user}:{db_password}"
            f"@/{db_name}?host={db_host}"
        )

    def execute_retrieval_query(
        self, sql: LiteralString, params: Dict[str, str]
    ) -> Any:
        """Run the given query."""
        try:
            logger.info(f"Executing query: {sql}")
            logger.info(f"Params: {params}")
            with self.engine.connect() as connection:
                # Execute a query
                result = connection.execute(text(sql), params).fetchall()
                logger.info(f"Result: {result}")
            logger.info("Query executed successfully.")
        except Exception as e:
            logger.info(f"An error occurred: {e}")
            result = []
        return result

    def store_documents(
        self, documents: List[Dict[str, Any]], sql_statement: LiteralString = insert_sql
    ) -> None:
        """Store the documents in the Vector Database."""
        try:
            with self.engine.connect() as connection:
                for document in documents:
                    connection.execute(text(sql_statement), document)
                connection.commit()
        except Exception as e:
            print(f"An error occurred: {e}")

    def mark_actual(self, file_id: int, actual: bool) -> None:
        """Mark the file as actual or not actual."""
        try:
            sql_stmt = text(
                f"UPDATE {self.config.chatbot_documents_table_name}"
                f" SET actual = :actual"
                f" WHERE file_id = :file_id"
            )
            with self.engine.connect() as connection:
                connection.execute(sql_stmt, {"actual": actual, "file_id": file_id})
                connection.commit()
        except Exception as e:
            logger.error(f"Error marking actual document: {e}")
            raise e

    def delete_document(self, file_id: int) -> None:
        """Delete the file from the Vector Database."""
        try:
            sql_stmt = text(
                f"DELETE FROM {self.config.chatbot_documents_table_name}"
                f" WHERE file_id = :file_id"
            )

            with self.engine.connect() as connection:
                connection.execute(sql_stmt, {"file_id": file_id})
                connection.commit()
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise e

    def execute_query(self, query: str) -> Any:
        """Select documents from the Vector Database."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query)).fetchall()
        except Exception as e:
            logger.info(f"An error occurred: {e}")
            result = []
        return result
