import logging
import re

from app.static.due_diligence_bq_keys import (
    DD_BQ_ESTIMATED_GENERATION_FIELD_NAME,
    DD_YEAR_METRICS_KEYS_MONTH_ORDER,
    DD_YEAR_METRICS_KEYS_VALUES,
    DueDiligenceBQKeys,
)

logger = logging.getLogger(__name__)


def prepare_keys_sync_payload(crud_handler, document, key) -> dict:
    """To avoid extra BQ calls, ensure yearly production metrics includes latest snapshot of current DB data"""
    if key.name not in DD_YEAR_METRICS_KEYS_VALUES:
        # wrap key as a dict with name changes to supported by BQ
        sync_payload = {DueDiligenceBQKeys(key.name).name: key.value}
        return sync_payload
    # retrieve all the key values from the DB
    db_keys = crud_handler.get_document_keys_by_names(document_id=document.id, keys_names=DD_YEAR_METRICS_KEYS_VALUES)
    # transform to the dict and parse generation amount
    db_keys = {DueDiligenceBQKeys(db_key.name).name: _parse_estimated_generation(db_key.value) for db_key in db_keys}
    # sort values by month
    sorted_values = [db_keys.get(month, 0) for month in DD_YEAR_METRICS_KEYS_MONTH_ORDER]
    sync_payload = {DD_BQ_ESTIMATED_GENERATION_FIELD_NAME: sorted_values}
    return sync_payload


def _parse_estimated_generation(input_value):
    """For some of the due diligence keys user can input values with their units,
    thus need to extract the numeric value of the string and transform to kw:
        400 KW -> 400
        2 mw -> 2000
        100w -> 0.1
        twenty items per cell -> None"""
    match = re.match(r"^\s*(\d*\.?\d+)\s*(wh|kwh|mwh)\b", input_value.lower())

    if not match:
        logger.warning(f"Cannot transform to KWh: {input_value=}")
        # return 0 since BQ doesn't support null
        return 0

    value, unit = float(match.group(1)), match.group(2)

    # Convert to kilowatts
    conversion_factors = {"wh": 0.001, "kwh": 1, "mwh": 1000}
    return value * conversion_factors[unit]
