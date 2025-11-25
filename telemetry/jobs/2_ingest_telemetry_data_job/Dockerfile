FROM apache/beam_python3.12_sdk:2.62.0

COPY --from=gcr.io/dataflow-templates-base/python312-template-launcher-base:latest \
    /opt/google/dataflow/python_template_launcher /opt/google/dataflow/python_template_launcher

ARG JOB="ingest_telemetry_data_job"

RUN mkdir -p "/template/${JOB}/"

COPY . "/template/${JOB}/"

RUN pip install --no-cache-dir -U pip -r "/template/${JOB}/requirements.txt"

ENV FLEX_TEMPLATE_PYTHON_PY_FILE="/template/${JOB}/main.py"

ENTRYPOINT ["/opt/apache/beam/boot"]
