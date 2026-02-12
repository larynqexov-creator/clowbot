from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.tables import OutboxMessage
from app.schemas.outbox_v1 import OutboxPayloadV1


@dataclass(frozen=True)
class SendResult:
    status: str  # SENT | DRY_RUN_SENT | FAILED
    external_id: str | None = None
    external_url: str | None = None
    raw_response: dict | None = None
    retryable: bool = False
    reason: str | None = None


class SenderAdapter(Protocol):
    kind: str

    def send(self, *, payload: OutboxPayloadV1, outbox_row: OutboxMessage) -> SendResult: ...
