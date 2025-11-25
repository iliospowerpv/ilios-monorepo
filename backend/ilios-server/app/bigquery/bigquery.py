import logging
import textwrap
from collections.abc import Iterator
from datetime import date
from typing import Any

from google.cloud import bigquery
from google.oauth2 import service_account

from app.settings import settings

logger = logging.getLogger(__name__)


class BigQueryReadEngine:

    def __init__(self) -> None:
        self.query_job_id_prefix = settings.telemetry_bq_job_id_prefix
        credentials = service_account.Credentials.from_service_account_file(settings.service_account_key_file_path)
        self._client = bigquery.Client(project=settings.telemetry_bq_project_id, credentials=credentials)
        self.bq_dataset_name = f"platform_{settings.environment_name}"

    def execute_query(self, query: str) -> Iterator[dict[str, Any]]:
        query = textwrap.dedent(query).strip()
        query_job = self._client.query(query, job_id_prefix=self.query_job_id_prefix)

        logger.info(f"Executing query in BigQuery query={query}")

        row_iterator = query_job.result()

        # TODO thinking about return list on this level, rather than wrap each and every call into list
        return map(self._row_to_dict, row_iterator)

    @staticmethod
    def _row_to_dict(row: bigquery.Row) -> dict[str, Any]:
        return dict(row.items())


class BigQueryWriteEngine(BigQueryReadEngine):
    """Implements write BQ operations"""

    def get_bq_record(self, table_id: str, condition: str):
        """Retrieve BQ record by specific conditions"""
        query = f"SELECT * FROM `{table_id}` WHERE {condition}"
        queryset = list(self.execute_query(query))
        return queryset[0] if queryset else None

    @staticmethod
    def _get_bq_query_param(value):
        """Map Python types to BigQuery parameter types and corresponding query functions.
        Handle only data types that are supported by the <characteristics> tables."""
        if isinstance(value, str):
            return "STRING", bigquery.ScalarQueryParameter
        elif isinstance(value, int):
            return "INT64", bigquery.ScalarQueryParameter
        elif isinstance(value, float):
            return "FLOAT64", bigquery.ScalarQueryParameter
        elif isinstance(value, date):
            return "DATE", bigquery.ScalarQueryParameter
        elif isinstance(value, list):
            if all(isinstance(v, (int, float)) for v in value):
                return "FLOAT64", bigquery.ArrayQueryParameter
        else:  # pragma: no cover
            logger.warning(f"Unsupported type {type(value)}")
            raise ValueError(f"Unsupported value type: {type(value)}")

    def insert_bq_record(self, table_id: str, record: dict):
        """Insert BQ record"""
        # build the parameterized query, to handle diversity of types using BQ scalar parameter feature
        columns = ", ".join(record.keys())
        values_placeholders = ", ".join([f"@{field_name}" for field_name in record.keys()])
        query = f"INSERT INTO `{table_id}` ({columns}) VALUES ({values_placeholders})"

        # prepare query parameters to specify each field type
        query_params = self._generate_query_params(record, is_update=False)
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        query_job = self._client.query(query, job_config=job_config)
        # wait BQ job to complete, to return results directly to user
        query_job.result()

    def update_bq_record(self, table_id: str, record: dict, condition: str):
        """Update BQ record. Uses similar to the <insert_bq_record> method query-parametrized job approach,
        see comments in the <insert_bq_record> function for implementation details."""
        set_clause = ", ".join([f"{field_name} = @update_{field_name}" for field_name in record.keys()])
        query = f"UPDATE `{table_id}` SET {set_clause} WHERE {condition}"

        query_params = self._generate_query_params(record, is_update=True)
        job_config = bigquery.QueryJobConfig()
        job_config.query_parameters = query_params

        query_job = self._client.query(query, job_config=job_config)
        query_job.result()

    def _generate_query_params(self, record, is_update=False):
        query_params = []
        for field_name, field_value in record.items():
            param_type, param_func = self._get_bq_query_param(field_value)
            param_name = f"update_{field_name}" if is_update else field_name
            query_params.append(param_func(param_name, param_type, field_value))
        return query_params
