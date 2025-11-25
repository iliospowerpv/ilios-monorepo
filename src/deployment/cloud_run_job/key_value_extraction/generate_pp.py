import logging
import os

from src.deployment.cloud_run_job.key_value_extraction.env_enum import Env
from src.deployment.cloud_run_job.key_value_extraction.response_status import Status
from src.deployment.cloud_run_job.key_value_extraction.utils import (
    get_example_pp_data,
    send_data,
)
from src.pipelines.constants import AgreementType
from src.pipelines.project_preview_builder import ProjectPreviewBuilder


logger = logging.getLogger(__name__)


def generate_pp(
    agreement_type: AgreementType,
    detect_poison_pills: bool,
    file_url: str,
    file_id: str,
    backend_output_path: str,
) -> None:

    if os.environ.get("ENV") == Env.TEST:
        logger.info("Communication success: Test environment")
        try:
            request_result = send_data(
                backend_output_path,
                Status.COMPLETED,
                agreement_type,
                ai_model_version="test",
                result=[
                    {
                        "key_item": "test",
                        "value": "test",
                        "legal_term": "test",
                        "poison_pill": "test",
                        "poison_pill_detailed": "test",
                        "is_poison_pill": 1,
                    }
                ],
            )
            logger.info(
                f"Backend connection success for Test environment: "
                f"{request_result.json()}"
            )
        except Exception as e:
            logger.info(f"Connection with backend for Test environment: {e}")
            raise Exception(f"Connection with backend failed for test env: {e}")

    elif os.environ.get("ENV") == Env.DEV:
        logger.info("Communication success: Dev environment")
        try:
            request_result = send_data(
                backend_output_path,
                Status.COMPLETED,
                agreement_type,
                ai_model_version="claude3-sonnet",
                result=get_example_pp_data(agreement_type),
            )
            logger.info(
                f"Backend connection success for Dev environment: "
                f"{request_result.json()}"
            )
        except Exception as e:
            logger.info(f"Failed communication for Dev environment: {e}")
            raise Exception(f"PP_BUILD: Failed to build project preview: {e}")

    elif os.environ.get("ENV") in [Env.QA, Env.UAT, Env.PROD]:
        logger.info("Communication success: QA/PROD environment")
        try:
            logger.info(f"Pipeline started for provided file: {file_id}")
            try:
                pp_builder = ProjectPreviewBuilder(
                    file_paths=[file_url],
                    agreement_type=agreement_type,
                    poison_pills_detection=detect_poison_pills,
                )
                pp_dict = pp_builder.get_project_preview_dict()
                logger.info(f"Generated project preview: {pp_dict}")
                logger.info(f"PP_BUILD: Project preview build for file_id: {file_id}")
            except Exception as e:
                logger.info(f"PP_BUILD: Failed to build project preview: {e}")
                raise Exception(f"PP_BUILD: Failed to build project preview: {e}")

            try:
                logger.info(f"PP_SAVE: Saving data to backend: {backend_output_path}")
                request_result = send_data(
                    backend_output_path,
                    Status.COMPLETED,
                    agreement_type,
                    ai_model_version="claude3-sonnet",
                    result=pp_dict,
                )
                try:
                    logger.info(
                        f"PP_SAVE: Save completed - put request results: "
                        f"{request_result.json()}"
                    )
                except Exception as e:
                    logger.info(f"PP_SAVE: Failed to parse request result JSON: {e}")
                    logger.info(f"PP_SAVE: Request result: {request_result}")
                    raise Exception(f"PP_SAVE: Failed to parse request result: {e}")
            except Exception as e:
                logger.info(f"PP_SAVE: Failed to save data to backend: {e}")
                try:
                    logger.info(f"PP_SAVE: Request result: {request_result.json()}")
                except Exception as e:
                    logger.info(f"PP_SAVE: Request result: {request_result}")
                    logger.info(f"PP_SAVE: Failed to parse request result JSON: {e}")
                    raise Exception(f"PP_SAVE: Failed to save result to backend: {e}")

            logger.info(f"Pipeline finished for provided file: {file_id}")
        except Exception as e:
            logger.info(
                f"PP_FAILED: Pipeline failed for provided file: {file_id}. Error: {e}"
            )
            try:
                logger.info(
                    f"PP_FAILED: Sending error to backend: {backend_output_path}"
                )
                request_result = send_data(
                    backend_output_path,
                    Status.PROCESSING_FAILED,
                    agreement_type,
                    ai_model_version="claude3-sonnet",
                    result=[
                        {
                            "message": f"PP_FAILED: Pipeline failed for provided "
                            f"file: {file_id}",
                            "error": f"PP_FAILED: Error: {e}",
                        }
                    ],
                )
            except Exception as e:
                logger.info(f"PP_FAILED: Failed to send error message to backend: {e}")
                raise Exception(f"PP_FAILED: Failed to send error to backend: {e}")
            try:
                logger.info(
                    f"PP_FAILED: Pipeline failed - put request results: "
                    f"{request_result.json()}"
                )
            except Exception as e:
                logger.info(f"PP_FAILED: Failed to parse request result JSON: {e}")
                logger.info(f"PP_FAILED: Request result: {request_result}")
                raise Exception(f"PP_FAILED: Failed to parse request result: {e}")
