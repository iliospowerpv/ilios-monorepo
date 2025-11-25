import functools
import logging as std_logging
import sys
from typing import Any, Final, Self

import orjson
from google.cloud import logging as gcp_logging

from .settings import settings


class StructuredLoggerAdapter:
    STACK_LEVEL_DEFAULT: Final[int] = 2
    EXTRA_CONTEXT_FIELD: Final[str] = "json_fields"

    def __init__(self, logger: std_logging.Logger, **context: Any) -> None:
        self.logger = logger
        self.context = context

    def bind(self, **context: Any) -> Self:
        return type(self)(self.logger, **(self.context | context))

    def log(self, level: int, message: str, *args: Any, **context: Any) -> None:
        kwargs = self._build_kwargs_from_context(context)
        self.logger.log(level, message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **context: Any) -> None:
        kwargs = self._build_kwargs_from_context(context)
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **context: Any) -> None:
        kwargs = self._build_kwargs_from_context(context)
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **context: Any) -> None:
        kwargs = self._build_kwargs_from_context(context)
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **context: Any) -> None:
        kwargs = self._build_kwargs_from_context(context)
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **context: Any) -> None:
        kwargs = self._build_kwargs_from_context(context)
        self.logger.critical(message, *args, **kwargs)

    def _build_kwargs_from_context(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "exc_info": context.pop("exc_info", False),
            "stack_info": context.pop("stack_info", False),
            "stacklevel": context.pop("stacklevel", self.STACK_LEVEL_DEFAULT),
            "extra": context.pop("extra", {}) | {self.EXTRA_CONTEXT_FIELD: self.context | context},
        }


def get_logger(name: str | None = None) -> StructuredLoggerAdapter:
    logger = std_logging.getLogger(name)
    return StructuredLoggerAdapter(logger)


class OptimizedJsonEncoderAdapter:

    def __init__(self, **kwargs: Any) -> None:
        pass

    @staticmethod
    def encode(obj: Any) -> str:
        option = orjson.OPT_NON_STR_KEYS
        return orjson.dumps(obj, option=option).decode("utf-8")


class LocalContextFormatter(std_logging.Formatter):
    EXTRA_CONTEXT_FIELD: Final[str] = "json_fields"

    def format(self, record: std_logging.LogRecord) -> str:
        record.context = getattr(record, self.EXTRA_CONTEXT_FIELD, {})
        return super().format(record)


@functools.cache
def setup() -> None:
    if settings.use_cloud_logger:
        client = gcp_logging.Client(project=settings.project_id)
        client.setup_logging(json_encoder_cls=OptimizedJsonEncoderAdapter)

    else:
        formatter = LocalContextFormatter("%(asctime)s | %(levelname)s | %(message)s | %(context)s")

        handler = std_logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(formatter)

        std_logging.basicConfig(level=std_logging.INFO, handlers=[handler], force=True)
