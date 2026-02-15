from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, TypeVar

from minio import Minio

from app.core.config import settings


def put_text(*, object_key: str, text: str, content_type: str = "text/plain; charset=utf-8") -> str:
    """Write text into object store. Best-effort.

    Primary backend: MinIO.
    Fallback backend (offline/tests): local filesystem directory.
    """

    data = text.encode("utf-8")
    return put_bytes(object_key=object_key, data=data, content_type=content_type)


def put_bytes(*, object_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Write bytes into object store. Best-effort.

    Primary backend: MinIO.
    Fallback backend (offline/tests): local filesystem directory.
    """

    import io

    def _op() -> str:
        c = _client()
        if not c.bucket_exists(settings.MINIO_BUCKET):
            c.make_bucket(settings.MINIO_BUCKET)
        c.put_object(
            settings.MINIO_BUCKET,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return object_key

    try:
        return _with_retry(_op, attempts=2)
    except Exception:
        # In unit tests / offline mode we fall back to local filesystem storage.
        _put_local(object_key=object_key, data=data)
        return object_key


def get_bytes(*, object_key: str) -> bytes | None:
    """Read bytes from object store. Best-effort.

    Returns None if object is not available.
    """

    def _op() -> bytes:
        c = _client()
        res = c.get_object(settings.MINIO_BUCKET, object_key)
        try:
            return res.read()
        finally:
            try:
                res.close()
                res.release_conn()
            except Exception:
                pass

    try:
        return _with_retry(_op, attempts=2)
    except Exception:
        return _get_local(object_key=object_key)


T = TypeVar("T")


def _client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def _local_root() -> Path:
    root = Path(settings.LOCAL_OBJECT_STORE_DIR)
    # If configured as relative path, anchor it to the current working directory.
    return root


def _put_local(*, object_key: str, data: bytes) -> None:
    path = _local_root() / object_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _get_local(*, object_key: str) -> bytes | None:
    path = _local_root() / object_key
    try:
        return path.read_bytes()
    except Exception:
        return None


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
