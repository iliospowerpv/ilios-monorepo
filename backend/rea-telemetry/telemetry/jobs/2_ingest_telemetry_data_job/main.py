import re
from argparse import ArgumentParser, ArgumentTypeError
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeAlias

import apache_beam as beam
import orjson
from apache_beam.io.gcp.bigquery_tools import RetryStrategy
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions, StandardOptions
from google.cloud import bigquery


def regex_type(pattern: str) -> Callable[[str], str]:

    def validate(value: str) -> str:
        if re.search(pattern, value) is None:
            raise ArgumentTypeError(f"must conform to regex: {pattern}")
        return value

    return validate


class JobOptions(PipelineOptions):

    @classmethod
    def _add_argparse_args(cls, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--subscription_id",
            required=True,
            help=(
                "Pub/Sub subscription for reading input data. Must be a resource identifier in the format: "
                "projects/<project_id>/subscriptions/<subscription_name>"
            ),
            type=regex_type(r"^projects/[a-z][a-z0-9-]{4,28}[a-z0-9]/subscriptions/[a-zA-Z][a-zA-Z0-9_-]{2,254}$"),
        )
        parser.add_argument(
            "--dataset_id",
            required=True,
            help=(
                "BigQuery dataset for writing output data. Must be a resource identifier in the format: "
                "<project_id>:<dataset_name>"
            ),
            type=regex_type(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]:[a-zA-Z0-9_]{1,1024}$"),
        )


Record: TypeAlias = dict[str, Any]


class TransformMessageToRecordsDoFn(beam.DoFn):

    def process(self, element: beam.io.PubsubMessage, record_categories: frozenset[str]) -> Iterable[Record]:  # noqa
        if (record_category := element.attributes.get("category")) in record_categories:
            record: Record = orjson.loads(element.data)
            record["ingest_ts"] = datetime.now(tz=timezone.utc).isoformat()
            record["__category__"] = record_category  # interim
            yield record


Error: TypeAlias = dict[str, Any]


class TransformRecordToErrorsDoFn(beam.DoFn):

    def process(self, element: tuple[str, Record, list[Error]]) -> Iterable[Error]:  # noqa
        table_id, record, errors = element

        for error in errors:
            yield {
                "table_id": table_id,
                "record_json": orjson.dumps(record),
                "error_reason": error["reason"],
                "error_message": error["message"],
            }


Schema: TypeAlias = list[dict[str, Any]]


def main() -> None:
    pipeline_options = PipelineOptions()

    standard_options = pipeline_options.view_as(StandardOptions)
    standard_options.streaming = True

    setup_options = pipeline_options.view_as(SetupOptions)
    setup_options.save_main_session = True

    job_options = pipeline_options.view_as(JobOptions)

    subscription_id: str = job_options.subscription_id
    dataset_id: str = job_options.dataset_id

    def get_table_id(category: str) -> str:
        return f"{dataset_id}.{category}"

    root_path = Path(__file__).parent

    schemas: dict[str, Schema] = orjson.loads((root_path / "schemas.json").read_text())

    # The `beam.io.WriteToBigQuery` transform does not support dynamic `additional_bq_parameters`
    # as a callable function for streaming pipelines. Ensure all tables are created in advance.

    client = bigquery.Client()

    for category, schema in schemas.items():
        time_partitioning = {"type": bigquery.TimePartitioningType.DAY}

        for field in schema:
            if field.pop("_partition", False):
                time_partitioning["field"] = field["name"]

        table = bigquery.Table(get_table_id(category).replace(":", "."))  # noqa

        table.schema = [bigquery.SchemaField.from_api_repr(field) for field in schema]
        table.time_partitioning = bigquery.TimePartitioning.from_api_repr(time_partitioning)

        client.create_table(table, exists_ok=True)

    record_categories = frozenset(schemas.keys() - {"_errors"})

    def get_table_id_callback(record: Record) -> str:
        return get_table_id(record.pop("__category__"))  # discard

    with beam.Pipeline(options=pipeline_options) as pipeline:
        result = (
            pipeline
            | "Read messages from Pub/Sub"
            >> beam.io.ReadFromPubSub(
                subscription=subscription_id,
                with_attributes=True,
            )
            | "Transform messages to records" >> beam.ParDo(TransformMessageToRecordsDoFn(), record_categories)  # noqa
            | "Write records to BigQuery"
            >> beam.io.WriteToBigQuery(
                table=get_table_id_callback,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS,
                insert_retry_strategy=RetryStrategy.RETRY_ON_TRANSIENT_ERROR,
                ignore_insert_ids=True,
                ignore_unknown_columns=True,
                with_auto_sharding=True,
                triggering_frequency=1.0,
                batch_size=1_000,
            )
        )
        (
            result.failed_rows_with_errors
            | "Transform records to errors" >> beam.ParDo(TransformRecordToErrorsDoFn())  # noqa
            | "Write errors to BigQuery"
            >> beam.io.WriteToBigQuery(
                table=get_table_id("_errors"),
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                method=beam.io.WriteToBigQuery.Method.STREAMING_INSERTS,
                insert_retry_strategy=RetryStrategy.RETRY_NEVER,
                ignore_insert_ids=True,
                ignore_unknown_columns=True,
                with_auto_sharding=True,
                triggering_frequency=1.0,
                batch_size=1_000,
            )
        )


if __name__ == "__main__":
    main()
