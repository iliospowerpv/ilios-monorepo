import logging
import os
import pathlib
import subprocess
from typing import Any, Dict, List
from urllib.parse import urlparse

import docx2pdf
import pandas as pd
from google.cloud import storage
from requests import put, status_codes

from src.deployment.cloud_run_job.key_value_extraction.response_status import Status
from src.pipelines.constants import AgreementType


def get_example_pp_data(agreement_type: AgreementType) -> Any:
    """Get example project preview data."""
    main_data_path = (
        pathlib.Path(str(os.environ["PWD"]))
        / "src/deployment/cloud_run_job/key_value_extraction/test_outputs"
    )

    if agreement_type == AgreementType.SITE_LEASE:
        return (
            pd.read_csv(main_data_path / "project_preview_example_sl.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.INTERCONNECTION_AGREEMENT:
        return (
            pd.read_csv(main_data_path / "project_preview_example_ia.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.OM_AGREEMENT:
        return (
            pd.read_csv(main_data_path / "project_preview_example_om.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.EPC:
        return (
            pd.read_csv(main_data_path / "project_preview_example_epc.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.PPA:
        return (
            pd.read_csv(main_data_path / "project_preview_example_ppa.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.SUBSCRIBER_MANAGEMENT_AGREEMENT:
        return (
            pd.read_csv(main_data_path / "project_preview_example_subsc_mgmnt.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.LOAN_AGREEMENT:
        return (
            pd.read_csv(main_data_path / "project_preview_example_loan_agr.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.PHASE_1_ESA:
        return (
            pd.read_csv(main_data_path / "project_preview_example_phase_1_esa.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.OPERATING_AGREEMENT:
        return (
            pd.read_csv(main_data_path / "project_preview_example_operating_agr.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.PV_SYST:
        return (
            pd.read_csv(main_data_path / "project_preview_example_pv_syst.csv")
            .fillna("N/A")
            .to_dict(orient="records")
        )
    elif agreement_type == AgreementType.OM_PRODUCTION_GUARANTEE:
        return (
            pd.read_csv(
                main_data_path / "project_preview_example_production_guarantee.csv"
            )
            .fillna("N/A")
            .to_dict(orient="records")
        )
    else:
        raise ValueError(f"Unsupported agreement type: {agreement_type}")


def send_data(
    endpoint_path: str,
    status: Status,
    agreement_type: AgreementType,
    ai_model_version: str,
    result: List[Dict[str, Any]],
) -> Any:
    if status == Status.COMPLETED:
        status_code = status_codes.codes.ok
    else:
        status_code = status_codes.codes.internal_server_error
    put_request_result = put(
        endpoint_path,
        params={"api_key": os.environ.get("BACKEND_API_KEY")},
        json={
            "status": str(status.value),
            "ai_model_version": str(ai_model_version),
            "ai_app_version": str(os.environ.get("AI_APP_VERSION")),
            "status_code": status_code,
            "agreement_type": str(agreement_type),
            "result": result,
        },
    )
    return put_request_result


def timeout_handler(signum, frame) -> None:  # type: ignore
    raise TimeoutError("Cloud Run Job Timeout")


def convert_docx_to_pdf_if_needed(file_url: str) -> str:
    """
    Convert docx to pdf if needed.
    :param file_url:
    :return:
    """
    if file_url.endswith(".docx"):
        parsed_url = urlparse(file_url)
        bucket_name = parsed_url.netloc
        file_uri = parsed_url.path.lstrip("/")
        docx_file_name = parsed_url.path.split("/")[-1]

        client = storage.Client()
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(file_uri)
        blob.download_to_filename(docx_file_name)

        return convert(docx_file_name)

    return file_url


def convert(docx_file_name: str) -> str:
    """
    Convert docx to pdf. For three platforms: macos, windows, and linux.
    :param docx_file_name:
    :return:
    """
    pdf_file_name = docx_file_name.replace(".docx", ".pdf")
    try:
        docx2pdf.convert(docx_file_name, pdf_file_name)
    except NotImplementedError:
        logging.info("Using linux OS, switching to libreoffice to convert docx to pdf.")
        subprocess.check_output(["libreoffice", "--convert-to", "pdf", docx_file_name])
    return pdf_file_name
