import contextlib
import functools
import hashlib
import random
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone

from . import firestore
from .constants import CLOUD, LOCK_CACHE_TTL, TELEMETRY_CACHE_COLLECTION_ID, TOKEN_CACHE_TTL


def cache_token(fetch_token: Callable[[str], str]) -> Callable[[str], str]:
    if not CLOUD:
        return fetch_token

    @functools.wraps(fetch_token)
    def wrapper(token: str) -> str:
        cache_key = "token:" + hashlib.sha256(token.encode("utf-8")).hexdigest()

        with cache_lock(cache_key):
            document = firestore.database.get_document(TELEMETRY_CACHE_COLLECTION_ID, cache_key)

            if document is None or document.data["expire_ts"] < datetime.now(tz=timezone.utc):
                cache_value = {
                    "token": fetch_token(token),
                    "expire_ts": datetime.now(tz=timezone.utc) + timedelta(seconds=TOKEN_CACHE_TTL),
                }
                firestore.database.set_document(TELEMETRY_CACHE_COLLECTION_ID, cache_key, cache_value)
            else:
                assert document.id == cache_key
                cache_value = document.data

        return cache_value["token"]

    return wrapper


@contextlib.contextmanager
def cache_lock(cache_key: str) -> Iterator[None]:
    while not _acquire_cache_lock(cache_key):
        time.sleep(random.random())
    try:
        yield
    finally:
        _release_cache_lock(cache_key)


def _acquire_cache_lock(cache_key: str) -> bool:
    lock_cache_key = "_lock:" + cache_key

    lock_document_ref = firestore.database.document(TELEMETRY_CACHE_COLLECTION_ID, lock_cache_key)

    lock_document = lock_document_ref.get()

    if lock_document.exists and lock_document.to_dict()["expire_ts"] < datetime.now(tz=timezone.utc):
        # Prevent deadlock by forcibly releasing the acquired lock once it has expired.
        lock_document_ref.delete()

    lock_cache_value = {"expire_ts": datetime.now(tz=timezone.utc) + timedelta(seconds=LOCK_CACHE_TTL)}

    try:
        lock_document_ref.create(lock_cache_value)
        return True
    except Exception:
        return False


def _release_cache_lock(cache_key: str) -> None:
    lock_cache_key = "_lock:" + cache_key

    lock_document_ref = firestore.database.document(TELEMETRY_CACHE_COLLECTION_ID, lock_cache_key)

    lock_document_ref.delete()
