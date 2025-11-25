import time
from typing import Any, Self


class Timer:

    def __init__(self) -> None:
        self._start_time_ns = 0
        self._end_time_ns = 0

    def __enter__(self) -> Self:
        self._start_time_ns = self._end_time_ns = time.perf_counter_ns()  # reset
        return self

    def __exit__(self, *args: Any) -> None:
        self._end_time_ns = time.perf_counter_ns()

    @property
    def elapsed_ns(self) -> int:
        return self._end_time_ns - self._start_time_ns

    @property
    def elapsed_ms(self) -> int:
        return round(self.elapsed_ns / 1_000_000)
