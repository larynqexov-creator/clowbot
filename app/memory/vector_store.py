from __future__ import annotations

import hashlib
import time
from typing import Any, Callable, TypeVar

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import settings

T = TypeVar("T")


def _client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL, timeout=2.0)


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
    raise last_exc or RuntimeError("qdrant error")


def qdrant_ready() -> bool:
    try:
        _with_retry(lambda: _client().get_collections(), attempts=1)
        return True
    except Exception:
        return False


def ensure_qdrant_collection() -> None:
    def _op() -> None:
        c = _client()
        name = settings.QDRANT_COLLECTION
        existing = {col.name for col in c.get_collections().collections}
        if name in existing:
            return
        c.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=8, distance=qm.Distance.COSINE),
        )

    _with_retry(_op, attempts=3)


def upsert_memory_vectors(*, tenant_id: str, points: list[dict[str, Any]]) -> None:
    def _op() -> None:
        c = _client()
        qpoints: list[qm.PointStruct] = []
        for p in points:
            payload = dict(p["payload"])
            payload["tenant_id"] = tenant_id
            qpoints.append(qm.PointStruct(id=p["id"], vector=p["vector"], payload=payload))
        c.upsert(collection_name=settings.QDRANT_COLLECTION, points=qpoints)

    _with_retry(_op, attempts=3)


def search_memory(*, tenant_id: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
    def _op() -> list[dict]:
        c = _client()
        must = [qm.FieldCondition(key="tenant_id", match=qm.MatchValue(value=tenant_id))]
        res = c.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qm.Filter(must=must),
        )
        return [{"id": r.id, "score": r.score, "payload": r.payload or {}} for r in res]

    return _with_retry(_op, attempts=3)


def _hash_vector8(text: str) -> list[float]:
    """Deterministic 8-dim pseudo-embedding based on sha256.

    This is not a semantic embedding, but it enables consistent vector upserts
    and makes bootstrap logic testable without external embedding services.
    """

    h = hashlib.sha256(text.encode("utf-8")).digest()
    # 8 floats in [0,1]
    vec = [b / 255.0 for b in h[:8]]
    return vec


def upsert_document_text_best_effort(*, tenant_id: str, doc_id: str, domain: str, source_type: str, text: str) -> None:
    """Best-effort vector upsert for a document.

    If Qdrant is unavailable, silently does nothing.
    """

    try:
        if not qdrant_ready():
            return
        ensure_qdrant_collection()
        upsert_memory_vectors(
            tenant_id=tenant_id,
            points=[
                {
                    "id": doc_id,
                    "vector": _hash_vector8(text or ""),
                    "payload": {"domain": domain, "source_type": source_type},
                }
            ],
        )
    except Exception:
        return
