VERSION=0.0.71

IMAGE_NAME=docai-poc
IMAGE_NAME_CLOUD_RUN=docai-poc-cloud-run
IMAGE_NAME_FASTAPI=docai-fastapi
INTERROGATE_THRESHOLD=50
GCP_PROJECT=prj-ilios-ai

install:
	poetry install --no-root

export_requirements_key_extraction:
	poetry export --without-hashes --format requirements.txt --output requirements_key_extraction.txt

export_requirements_fastapi:
	poetry export --with chatbot --without-hashes --format requirements.txt --output requirements.txt

notebook:
	poetry run jupyter notebook

mypy:
	poetry run mypy --incremental --show-error-codes --pretty src

lint:
	poetry run flakehell lint src

isort:
	poetry run isort src

black:
	poetry run black --config pyproject.toml src

interrogate:
	poetry run interrogate --fail-under=${INTERROGATE_THRESHOLD} src

test:
	pytest -s -vv --pyargs src/test

format: isort black

check: format lint mypy interrogate

pre-commit: check test export_requirements_fastapi export_requirements_key_extraction

run_pipeline:
	poetry run python -m src.pipelines.term_extraction.main

docker_build:
	docker build --platform linux/amd64 -t "${IMAGE_NAME}" .

docker_run:
	docker run \
		-e GOOGLE_API_KEY=${GOOGLE_API_KEY} \
		-e PROJECT_ID=${PROJECT_ID} \
        -e DOC_AI_LOCATION=${DOC_AI_LOCATION} \
        -e DOC_AI_PROCESSOR_ID=${DOC_AI_PROCESSOR_ID} \
        -e GOOGLE_APPLICATION_CREDENTIALS=/app/notebooks/prj-ilios-ai.json \
        -e PYTHONPATH=/app \
        -e PWD=/app \
        -e LOCATION=${LOCATION} \
        -e GCS_VECTOR_STORE_BUCKET=${GCS_VECTOR_STORE_BUCKET} \
        -e VECTOR_STORE_INDEX_ENDPOINT_ID=${VECTOR_STORE_INDEX_ENDPOINT_ID} \
        -e VECTOR_STORE_INDEX_ID=${VECTOR_STORE_INDEX_ID} \
        -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
        -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
		-d --name ${IMAGE_NAME}-container \
		-p 8080:8080 ${IMAGE_NAME}

docker_remove:
	docker rm --force "${IMAGE_NAME}-container"

docker_reset: export_requirements_fastapi docker_remove docker_build docker_run

run_ui:
	poetry run streamlit run src/user_interface/Welcome.py

docker_auth:
	gcloud auth configure-docker us-east1-docker.pkg.dev

tag:
	docker tag "${IMAGE_NAME}" us-east1-docker.pkg.dev/prj-ilios-ai/docai-registry/${IMAGE_NAME}:${VERSION}

push:
	docker push us-east1-docker.pkg.dev/prj-ilios-ai/docai-registry/${IMAGE_NAME}:${VERSION}

docker_deploy: export_requirements_fastapi docker_build tag push

create_vector_store:
	poetry run python -m src.vectordb.gcp_vector_search.transform_and_load ${FILE_DIR}

docker_build_cloud_run_job:
	docker build --platform linux/amd64 -f src/deployment/cloud_run_job/key_value_extraction/Dockerfile -t "${IMAGE_NAME_CLOUD_RUN}" .

tag_cloud_run_job:
	docker tag "${IMAGE_NAME_CLOUD_RUN}" us-east1-docker.pkg.dev/prj-ilios-ai/docai-registry/${IMAGE_NAME_CLOUD_RUN}:${VERSION}

push_cloud_run_job:
	docker push us-east1-docker.pkg.dev/prj-ilios-ai/docai-registry/${IMAGE_NAME_CLOUD_RUN}:${VERSION}

docker_deploy_cloud_run_job: export_requirements_key_extraction docker_build_cloud_run_job tag_cloud_run_job push_cloud_run_job

docker_run_cloud_run_job:
	docker run \
		--env-file src/deployment/cloud_run_job/key_value_extraction/.envrc \
		-d --name ${IMAGE_NAME}-container \
		-p 8080:8080 ${IMAGE_NAME_CLOUD_RUN}\
		--agreement_type="Site Lease" \
		--detect_poison_pills=1 \
		--file_url="gs://doc_ai_storage/site-lease/documents/Brixmor-Blue Sky Felicita Plaza Lease - 7_17_19 (BSU Sig_ Deed Included).pdf" \
		--file_id=123

docker_reset_cloud_run_job: export_requirements_key_extraction docker_remove docker_build_cloud_run_job docker_run_cloud_run_job

run_fastapi: export_requirements_fastapi docker_build_fastapi
	docker rm --force "${IMAGE_NAME_FASTAPI}-container"
	docker build --platform linux/amd64 -f src/deployment/fast_api/Dockerfile -t "${IMAGE_NAME_FASTAPI}" .
	docker run \
		-e GOOGLE_API_KEY=${GOOGLE_API_KEY} \
		-e PROJECT_ID=${PROJECT_ID} \
        -e DOC_AI_LOCATION=${DOC_AI_LOCATION} \
        -e DOC_AI_PROCESSOR_ID=${DOC_AI_PROCESSOR_ID} \
        -e GOOGLE_APPLICATION_CREDENTIALS=/app/notebooks/prj-ilios-ai.json \
        -e PYTHONPATH=/app \
        -e PWD=/app \
        -e LOG_LEVEL=DEBUG \
        -e LOCATION=${LOCATION} \
        -e GCS_VECTOR_STORE_BUCKET=${GCS_VECTOR_STORE_BUCKET} \
        -e VECTOR_STORE_INDEX_ENDPOINT_ID=${VECTOR_STORE_INDEX_ENDPOINT_ID} \
        -e VECTOR_STORE_INDEX_ID=${VECTOR_STORE_INDEX_ID} \
        -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
        -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
        -e ENV=LOCAL \
        -e BACKEND_URL=https://backend-dot-prj-dev-base-e61d.uw.r.appspot.com/api/internal/co-terminus-checks/{record_id}/results \
        -e BACKEND_API_KEY=${BACKEND_API_KEY} \
        -e VECTOR_DB_INSTANCE=${VECTOR_DB_INSTANCE} \
        -e VECTOR_DB_USER=${VECTOR_DB_USER} \
        -e VECTOR_DB_PASSWORD=${VECTOR_DB_PASSWORD} \
        -e VECTOR_DB_NAME=${VECTOR_DB_NAME} \
        -e DB_USER=${DB_USER} \
        -e DB_PASSWORD=${DB_PASSWORD} \
        -e DB_HOST=${DB_HOST} \
        -e DB_NAME=${DB_NAME} \
        -e ML_API_KEY=${ML_API_KEY} \
		-d --name ${IMAGE_NAME_FASTAPI}-container \
		-p 8080:8080 ${IMAGE_NAME_FASTAPI}

docker_build_fastapi:
	docker build --platform linux/amd64 -f src/deployment/fast_api/Dockerfile -t "${IMAGE_NAME_FASTAPI}" .

tag_fastapi:
	docker tag "${IMAGE_NAME_FASTAPI}" us-east1-docker.pkg.dev/prj-ilios-ai/docai-registry/${IMAGE_NAME_FASTAPI}:${VERSION}

push_fastapi:
	docker push us-east1-docker.pkg.dev/prj-ilios-ai/docai-registry/${IMAGE_NAME_FASTAPI}:${VERSION}

deploy_fastapi: export_requirements_fastapi docker_build_fastapi tag_fastapi push_fastapi

chatbot_validation:
	poetry run python -m src.chatbot.validation.pipeline

run_chatbot_local:
	poetry run python -m src.chatbot.main
