from concurrent import futures
from typing import Any, Final

import orjson
from google.cloud import pubsub

from . import cloud_logging
from .thread_local import ThreadLocalProxy

logger = cloud_logging.get_logger(__name__)


class Publisher:
    MAX_BYTES: Final[int] = 1_000_000  # 1 MB
    MAX_LATENCY: Final[float] = 0.1  # 100 ms
    MAX_MESSAGES: Final[int] = 1_000

    def __init__(self) -> None:
        batch_settings = pubsub.types.BatchSettings(
            max_bytes=self.MAX_BYTES,
            max_latency=self.MAX_LATENCY,
            max_messages=self.MAX_MESSAGES,
        )

        self._client = pubsub.PublisherClient(batch_settings=batch_settings)
        self._futures: set[futures.Future[str]] = set()

    def publish(self, topic_id: str, payload: Any, **attrs: str) -> futures.Future[str]:
        data = orjson.dumps(payload)

        future = self._client.publish(topic_id, data, **attrs)
        self._futures.add(future)

        if len(self._futures) == self.MAX_MESSAGES:
            self.wait_until_published()
            assert len(self._futures) == 0

        return future

    def wait_until_published(self) -> None:
        for future in futures.as_completed(self._futures):
            try:
                message_id = future.result()
            except Exception as error:
                logger.error("Failed to publish message to Pub/Sub: %r", error)
            else:
                logger.debug("Published message to Pub/Sub: id=%r", message_id)
            finally:
                self._futures.remove(future)


publisher = ThreadLocalProxy(Publisher)
