import contextlib
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta

from ..common import firestore
from ..common.constants import (
    CLOUD,
    DATA_PROVIDER_POINT_TAG_MAPS,
    MAX_FETCH_INTERVAL_DAYS,
    MAX_HISTORY_DEPTH_YEARS,
    TELEMETRY_CACHE_COLLECTION_ID,
)
from ..common.enums import DataProvider, PointTag, TelemetryCategory


@contextlib.contextmanager
def next_fetch_telemetry_points_intervals_map(
    data_provider: DataProvider,
    site_id: str,
    device_id: str,
) -> Iterator[dict[PointTag, list[tuple[datetime, datetime]]]]:
    cache_key = f"{data_provider}:{site_id}:{device_id}:{TelemetryCategory.POINTS}"

    document = firestore.database.get_document(TELEMETRY_CACHE_COLLECTION_ID, cache_key)

    point_tag_map = DATA_PROVIDER_POINT_TAG_MAPS[data_provider]

    start_ts = datetime.now(tz=timezone.utc) - relativedelta(years=MAX_HISTORY_DEPTH_YEARS)

    start_ts_map = {point_tag: start_ts for point_tag in point_tag_map.keys()}

    if document is None:
        cache_value = {"last_fetch_ts": {}}
    else:
        assert document.id == cache_key
        cache_value = document.data

    start_ts_map.update(cache_value["last_fetch_ts"])

    end_ts = datetime.now(tz=timezone.utc)

    end_ts_map = {point_tag: end_ts for point_tag in point_tag_map.keys()}

    yield {
        point_tag: _split_into_intervals(start_ts_map[point_tag], end_ts_map[point_tag])
        for point_tag in point_tag_map.keys()
    }

    cache_value["last_fetch_ts"].update(end_ts_map)

    if CLOUD:
        firestore.database.set_document(TELEMETRY_CACHE_COLLECTION_ID, cache_key, cache_value)


@contextlib.contextmanager
def next_fetch_telemetry_alerts_interval(
    data_provider: DataProvider,
    site_id: str,
    device_id: str,
) -> Iterator[tuple[datetime, datetime]]:
    cache_key = f"{data_provider}:{site_id}:{device_id}:{TelemetryCategory.ALERTS}"

    document = firestore.database.get_document(TELEMETRY_CACHE_COLLECTION_ID, cache_key)

    start_ts = datetime.now(tz=timezone.utc) - relativedelta(years=MAX_HISTORY_DEPTH_YEARS)

    if document is None:
        cache_value = {"last_fetch_ts": start_ts}
    else:
        assert document.id == cache_key
        cache_value = document.data

    start_ts = cache_value["last_fetch_ts"]

    end_ts = datetime.now(tz=timezone.utc)

    yield (start_ts, end_ts)

    cache_value["last_fetch_ts"] = end_ts

    if CLOUD:
        firestore.database.set_document(TELEMETRY_CACHE_COLLECTION_ID, cache_key, cache_value)


def _split_into_intervals(start_ts: datetime, end_ts: datetime) -> list[tuple[datetime, datetime]]:
    intervals = []

    delta = timedelta(days=MAX_FETCH_INTERVAL_DAYS)

    next_start_ts = start_ts

    while next_start_ts < end_ts:
        next_end_ts = min(next_start_ts + delta, end_ts)

        intervals.append((next_start_ts, next_end_ts))

        next_start_ts = next_end_ts

    return intervals
