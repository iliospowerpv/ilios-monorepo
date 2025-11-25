import textwrap
from collections.abc import Iterable, Iterator
from io import BytesIO
from typing import Any, Final

import orjson
from google.cloud import bigquery

from . import cloud_logging
from .constants import PROJECT_ID
from .thread_local import ThreadLocalProxy
from .timer import Timer

logger = cloud_logging.get_logger(__name__)

SchemaField = bigquery.SchemaField  # export


class Engine:
    QUERY_JOB_ID_PREFIX: Final[str] = "telemetry-query-job-"
    LOAD_JOB_ID_PREFIX: Final[str] = "telemetry-load-job-"

    def __init__(self) -> None:
        self._client = bigquery.Client(project=PROJECT_ID)

    def execute_query(self, query: str) -> Iterator[dict[str, Any]]:
        query = textwrap.dedent(query).strip()

        query_job = self._client.query(query, job_id_prefix=self.QUERY_JOB_ID_PREFIX)

        sub_logger = logger.bind(job_id=query_job.job_id)

        sub_logger.info("Executing query in BigQuery", query=query)

        with Timer() as timer:
            row_iterator = query_job.result()

        statistics = {
            "queried_rows": row_iterator.total_rows or 0,
            "affected_rows": row_iterator.num_dml_affected_rows or 0,
            "processed_bytes": query_job.total_bytes_processed or 0,
            "billed_bytes": query_job.total_bytes_billed or 0,
        }

        duration = timer.elapsed_ms / 1_000

        sub_logger.info("Executed query in BigQuery", statistics=statistics, duration=duration)

        return map(self._row_to_dict, row_iterator)

    def replace_table(self, table_id: str, schema: list[SchemaField], rows: Iterable[dict[str, Any]]) -> None:
        load_job_config = bigquery.LoadJobConfig()

        load_job_config.schema = schema

        load_job_config.create_disposition = bigquery.CreateDisposition.CREATE_IF_NEEDED
        load_job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE

        load_job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON

        file = BytesIO(self._rows_to_jsonl(rows))

        load_job = self._client.load_table_from_file(
            file,
            table_id,
            job_id_prefix=self.LOAD_JOB_ID_PREFIX,
            job_config=load_job_config,
        )

        sub_logger = logger.bind(job_id=load_job.job_id)

        sub_logger.info("Replacing table in BigQuery", table_id=table_id)

        with Timer() as timer:
            load_job.result()

        statistics = {
            "output_rows": load_job.output_rows or 0,
            "output_bytes": load_job.output_bytes or 0,
        }

        duration = timer.elapsed_ms / 1_000

        sub_logger.info("Replaced table in BigQuery", statistics=statistics, duration=duration)

    @staticmethod
    def _row_to_dict(row: bigquery.Row) -> dict[str, Any]:
        return dict(row.items())

    @staticmethod
    def _rows_to_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
        return b"\n".join(map(orjson.dumps, rows))


engine = ThreadLocalProxy(Engine)
