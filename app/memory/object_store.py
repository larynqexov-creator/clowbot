from __future__ import annotations

import time
from typing import Callable, TypeVar

from minio import Minio

from app.core.config import settings

T = TypeVar("T")


def _client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def _with_retry(fn: Callable[[], T], *, attempts: int = 3, sleep_s: float = 0.3) -> T:
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if i == attempts - 1:
                raise
            time.sleep(sleep_s * (2**i))
    raise last_exc or RuntimeError("minio error")


def minio_ready() -> bool:
    try:
        c = _client()
        _with_retry(lambda: c.bucket_exists(settings.MINIO_BUCKET), attempts=1)
        return True
    except Exception:
        return False


def ensure_minio_bucket() -> None:
    def _op() -> None:
        c = _client()
        if not c.bucket_exists(settings.MINIO_BUCKET):
            c.make_bucket(settings.MINIO_BUCKET)

    _with_retry(_op, attempts=3)
