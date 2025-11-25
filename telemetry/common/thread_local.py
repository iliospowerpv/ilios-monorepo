import threading
from collections.abc import Callable
from typing import Any

ThreadLocal = threading.local  # export


class ThreadLocalProxy[T]:

    def __init__(self, resource_factory: Callable[[], T]) -> None:
        self._thread_local = ThreadLocal()
        self._resource_factory = resource_factory

    def __getattr__(self, name: str) -> Any:
        return getattr(self.resource, name)

    @property
    def resource(self) -> T:
        resource: T | None = getattr(self._thread_local, "resource", None)

        if resource is None:
            resource = self._thread_local.resource = self._resource_factory()

        return resource
