import logging.config
import os
import signal

from src.deployment.cloud_run_job.key_value_extraction.generate_pp import generate_pp
from src.deployment.cloud_run_job.key_value_extraction.response_status import Status
from src.deployment.cloud_run_job.key_value_extraction.utils import (
    convert_docx_to_pdf_if_needed,
    send_data,
    timeout_handler,
)
from src.pipelines.constants import AgreementType


logger = logging.getLogger(__name__)
logging.config.fileConfig("logging.conf", disable_existing_loggers=False)


def main() -> None:
    """Main function to run the term extraction pipeline. It is triggered by
    key-value-extraction-trigger Cloud Function."""
    env = os.environ.get("ENV")
    file_id: str = str(os.environ.get("FILE_ID"))
    file_url = str(os.environ.get("FILE_URL"))
    agreement_type = AgreementType.from_str(str(os.environ.get("AGREEMENT_TYPE")))
    detect_poison_pills = bool(os.environ.get("DETECT_POISON_PILLS"))

    backend_output_path = str(os.environ.get("BACKEND_URL")).format(file_id=file_id)
    logger.info(f"ENV: {env}")
    logger.info(f"Agreement type: {agreement_type}")
    logger.info(f"Detect poison pills: {detect_poison_pills}")
    logger.info(f"Cloud function started for file: {file_id}")
    logger.info(f"File URL: {file_url}")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(1740)  # timeout for 29 minutes
    try:
        try:
            file_url = convert_docx_to_pdf_if_needed(file_url)
        except Exception as e:
            logger.info(f"Error during file conversion: {e}")
            status = Status.UNPROCESSABLE_FILE
            raise e
        try:
            generate_pp(
                agreement_type,
                detect_poison_pills,
                file_url,
                file_id,
                backend_output_path,
            )
            status = Status.COMPLETED
        except Exception as e:
            logger.info(f"Error during pipeline execution: {e}")
            status = Status.PROCESSING_FAILED
            raise e
    except Exception as e:
        if isinstance(e, TimeoutError):
            status = Status.PROCESSING_TIMEOUT
        request_result = send_data(
            backend_output_path,
            status,
            agreement_type,
            ai_model_version="claude3-sonnet",
            result=[
                {
                    "message": f"Pipeline failed for provided " f"file: {file_id}",
                    "error": f"Error details: {e}",
                }
            ],
        )
        logger.info(f"Cloud Run Job failed: {e}")
        logger.info(
            f"Error send to backend. Response from Backend: {request_result.json()}"
        )

    logger.info("END OF FUNCTION")


if __name__ == "__main__":
    main()
