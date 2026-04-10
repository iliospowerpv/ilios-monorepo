import logging
import pickle
from datetime import datetime, timedelta

import pytz

from app.helpers.telemetry.demo_data import get_demo_bq_data, is_demo_mode
from app.redis_cache.cache import get_cache

logger = logging.getLogger(__name__)


class BaseTelemetryBigQuery:
    def __init__(self):
        self._is_demo = is_demo_mode()
        self.cache = get_cache()
        self.time_format = "%Y-%m-%dT%H:%M:%S.%f"
        if not self._is_demo:
            from app.bigquery.bigquery import BigQueryReadEngine
            self.bq_engine = BigQueryReadEngine()
        else:
            self.bq_engine = None
            logger.info("Telemetry running in DEMO mode — BigQuery bypassed")

    def _get_current_time_period(self, timezone):
        """
        Return previous 15 minutes interval of current time
        e.g. current time = 12:31 -> intervals: 12:15 - 12:30
             current time = 12:01 -> intervals: 11:45 - 12:00
        """
        current_time = datetime.now(pytz.timezone(timezone))
        intervals = [(0, 15), (15, 30), (30, 45), (45, 60)]
        prev_intervals = [(45, 60), (0, 15), (15, 30), (30, 45)]
        current_minutes = current_time.minute

        for i, (start, end) in enumerate(intervals):
            if start <= current_minutes < end:
                interval_start_time = current_time.replace(minute=prev_intervals[i][0], second=0, microsecond=0)
                if i == 0:
                    interval_start_time = interval_start_time - timedelta(hours=1)
                interval_end_time = interval_start_time + timedelta(minutes=15)

                return interval_start_time.strftime(self.time_format), interval_end_time.strftime(self.time_format)

    def get_from_cache(self, key_name):
        cached_data = self.cache.get(key_name)
        if cached_data:
            return pickle.loads(cached_data)

    def set_cache(self, key_name, value, expires_seconds):
        self.cache.set(key_name, pickle.dumps(value), ex=expires_seconds)

    def execute_bq_function(
        self,
        function_name: str,
        object_id_name: str,
        object_ids: list,
        interval_start: str,
        interval_end: str,
        timezone: str,
    ):
        if not object_ids:
            return

        if self._is_demo:
            return get_demo_bq_data(function_name, object_id_name, object_ids, interval_start, interval_end, timezone)

        object_ids = ", ".join(map(str, object_ids))
        query = (
            f"SELECT * FROM {self.bq_engine.bq_dataset_name}.{function_name}("
            f"'{interval_start}', '{interval_end}', '{timezone}') WHERE {object_id_name} IN ({object_ids})"
        )
        bq_site_data = list(self.bq_engine.execute_query(query))
        return bq_site_data
