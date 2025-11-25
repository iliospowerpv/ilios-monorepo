import logging
from collections.abc import Callable, Sequence

import tenacity

from . import cloud_logging

logger = cloud_logging.get_logger(__name__)

type SingleOrMultiple[T] = T | Sequence[T]


# fmt: off
def retry_on_exception[**P, R](
    exception_types: SingleOrMultiple[type[Exception]],
    *,
    max_retries: int,
    factor: float = 1,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    assert max_retries >= 0
    assert factor > 0

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        return tenacity.retry(
            retry=tenacity.retry_if_exception_type(exception_types),
            stop=tenacity.stop_after_attempt(1 + max_retries),
            wait=tenacity.wait_random_exponential(multiplier=factor),
            before=tenacity.before_log(logger, logging.DEBUG),  # noqa
            after=tenacity.after_log(logger, logging.WARNING),  # noqa
            before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),  # noqa
            reraise=True,
        )(function)

    return decorator
# fmt: on
