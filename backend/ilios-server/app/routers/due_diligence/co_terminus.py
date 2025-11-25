import logging
from itertools import groupby

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.co_terminus_check import CoTerminusCheckCRUD
from app.db.object_utils import as_dict
from app.db.session import get_session
from app.helpers.authorization.custom.diligence_overview_page import DiligenceOverviewPagePermissions
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.cloud_function_client import AIServerClient
from app.helpers.common import get_utc_now
from app.helpers.configs.co_terminus_helper import CoTerminusHandler
from app.models.file import FileParsingStatuses
from app.models.site import Site
from app.schema.co_terminus_checks import (
    CoTerminusCheckResultsList,
    CoTerminusCheckStatus,
    CoTerminusProcessAbortingSuccess,
    CoTerminusStartSuccess,
)
from app.settings import settings
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, HTTP_409_RESPONSE, CoTerminusMessages
from app.static.co_terminus_checks import CoTerminusComparisonStatuses

logger = logging.getLogger(__name__)
co_terminus_router = APIRouter()


@co_terminus_router.get(
    "/check",
    response_model=CoTerminusCheckResultsList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Retrieve the most recent co-terminus check results with summary (if check was completed)",
    dependencies=[Depends(DiligenceOverviewPagePermissions())],
)
async def get_check_results(site: Site = Depends(get_authorized_site), db_session: Session = Depends(get_session)):
    items, execution_status = [], None
    if site.co_terminus_check:
        db_items, execution_status = site.co_terminus_check.result, site.co_terminus_check.status
        items = CoTerminusHandler(db_session).filter_against_config(db_items)
    summary = []
    if items and execution_status and execution_status == FileParsingStatuses.completed:
        # calculate summary only if processing was completed, sort to make group-by work properly
        items_sorted = sorted(items, key=lambda x: x["status"])
        summary = [
            {"status": key, "count": len(list(group))} for key, group in groupby(items_sorted, lambda x: x["status"])
        ]
    return {"items": items, "summary": summary}


@co_terminus_router.post(
    "/check",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CoTerminusStartSuccess,
    responses={
        **HTTP_403_RESPONSE,
        **HTTP_404_RESPONSE,
        **HTTP_409_RESPONSE(message=CoTerminusMessages.check_is_running.value),
    },
    description="""Init the check (if there is no check in progress):
    \n1. Run BE comparison for the full-match
    \n2. Trigger AI comparison (for the items which were not matched by BE)""",
    dependencies=[Depends(DiligenceOverviewPagePermissions())],
)
async def init_check(site: Site = Depends(get_authorized_site), db_session: Session = Depends(get_session)):
    # validate there is no running check
    if site.co_terminus_check and site.co_terminus_check.status == FileParsingStatuses.processing:
        logger.warning(f"The co-terminus check is running for the site {site.id}")
        raise HTTPException(status.HTTP_409_CONFLICT, detail=CoTerminusMessages.check_is_running)

    # create check instance if it doesn't exist
    if not site.co_terminus_check:
        CoTerminusCheckCRUD(db_session).create_item({"site_id": site.id})

    # set start time and processing status
    site.co_terminus_check.start_time = get_utc_now()
    site.co_terminus_check.status = FileParsingStatuses.processing
    # clean end time and actuality flag for previous runs
    site.co_terminus_check.end_time = None
    site.co_terminus_check.is_actual = True

    co_terminus_handler = CoTerminusHandler(db_session)
    co_termius_config = co_terminus_handler.read()

    # retrieve unique agreements names to be processed
    source_agreements_names = set(
        [agreement_name for key_locations in co_termius_config.values() for agreement_name in key_locations.keys()]
    )
    # retrieve agreements, which should be analyzed, and their existing keys to simplify further processing
    source_agreements = {
        document.name.value: {key.name: key.value for key in document.keys}
        for document in site.documents
        if document.name.value in source_agreements_names
    }

    # based on the config, retrieve existing keys according to their locations
    results_structure = []
    ai_payload = []
    for key_name, key_locations in co_termius_config.items():
        existing_keys = {}
        ai_payload_sources = []
        for agreement_name, key_alias in key_locations.items():
            ai_payload_item = {"document_name": agreement_name, "key_item": key_alias, "value": None}
            agreement_existing_keys = source_agreements.get(agreement_name)
            if not agreement_existing_keys:
                existing_keys[agreement_name] = None
                ai_payload_sources.append(ai_payload_item)
                continue
            agreement_existing_key = agreement_existing_keys.get(key_alias)
            existing_keys[agreement_name] = agreement_existing_key
            ai_payload_item["value"] = agreement_existing_key
            ai_payload_sources.append(ai_payload_item)

        comparison_status = co_terminus_handler.define_comparison_status(existing_keys.values())
        result_item = {"name": key_name, "sources": existing_keys, "status": comparison_status}
        results_structure.append(result_item)

        if comparison_status == CoTerminusComparisonStatuses.pending.value:
            ai_payload.append({"name": key_name, "sources": ai_payload_sources})

    # set intermediate result
    site.co_terminus_check.result = results_structure

    # if AI payload is empty (all the values were processed by full-text match) - set end time and completed status
    if not ai_payload:
        site.co_terminus_check.end_time = get_utc_now()
        site.co_terminus_check.status = FileParsingStatuses.completed
    else:
        ai_trigger_payload = {"id": site.co_terminus_check.id, "items": ai_payload}
        try:
            response = AIServerClient(func_url=settings.co_terminus_function_url).post(
                payload=ai_trigger_payload, use_api_key=True
            )
            if not response.ok:
                response.raise_for_status()
        except Exception as exc:
            logger.error(f"The co-terminus check for site {site.id} was unable to start due to the error: {str(exc)}")
            # complete processing with error
            for check_item in results_structure:
                if check_item["status"] == CoTerminusComparisonStatuses.pending.value:
                    check_item["status"] = CoTerminusComparisonStatuses.error.value
            site.co_terminus_check.result = results_structure
            site.co_terminus_check.end_time = get_utc_now()
            site.co_terminus_check.status = FileParsingStatuses.processing_start_failed
            db_session.commit()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"An error occurred during AI processing: {str(exc)}")

    # save changes
    db_session.commit()

    return {"code": status.HTTP_202_ACCEPTED, "message": CoTerminusMessages.check_start_success}


@co_terminus_router.get(
    "/status",
    response_model=CoTerminusCheckStatus,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Retrieve details of the most recent co-term check execution",
    dependencies=[Depends(DiligenceOverviewPagePermissions())],
)
async def get_check_execution_status(
    site: Site = Depends(get_authorized_site),
):
    co_terminus_response = site.co_terminus_check if site.co_terminus_check else {}
    # if co-terminus object exists, additional handling for stick processing
    if co_terminus_response and co_terminus_response.status == FileParsingStatuses.processing:
        # calculate exact duration of the execution
        duration = get_utc_now() - co_terminus_response.start_time
        # check if it can be interpreted as processing which stuck
        is_stuck = duration.seconds > settings.co_terminus_stuck_threshold
        # transform to dict to extend with extra statics field
        co_terminus_response = as_dict(co_terminus_response)
        co_terminus_response.update(
            {
                "is_stuck": is_stuck,
                "duration": duration.seconds,
            }
        )
    return co_terminus_response


@co_terminus_router.get(
    "/stop",
    response_model=CoTerminusProcessAbortingSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Abort execution of the co-terminus check",
    dependencies=[Depends(DiligenceOverviewPagePermissions())],
)
async def stop_check_execution(site: Site = Depends(get_authorized_site), db_session: Session = Depends(get_session)):
    if not site.co_terminus_check:
        logger.warning(f"The co-terminus check is not running for the site {site.id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=CoTerminusMessages.check_is_not_started)
    if site.co_terminus_check.status != FileParsingStatuses.processing:
        logger.warning(f"Unable to stop check in status {site.co_terminus_check.status.value} ({site.id=})")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=CoTerminusMessages.check_is_not_running)
    site.co_terminus_check.status = FileParsingStatuses.processing_timeout
    site.co_terminus_check.end_time = get_utc_now()
    db_session.commit()
    return {"code": status.HTTP_202_ACCEPTED, "message": CoTerminusMessages.check_is_aborted}
