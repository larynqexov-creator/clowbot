from __future__ import annotations

from pydantic import TypeAdapter

from app.schemas.outbox_v1 import OutboxPayloadV1, compute_idempotency_key


def test_valid_email_payload_validates():
    payload = {
        "schema": "clowbot.outbox.v1",
        "kind": "email",
        "idempotency_key": "",
        "context": {"source": "test"},
        "policy": {"risk": "YELLOW", "requires_approval": False, "allowlist": {"emails": ["a@b.com"]}},
        "message": {
            "from": {"name": "X", "email": "x@b.com"},
            "to": [{"email": "a@b.com", "name": "A"}],
            "subject": "S",
            "body": {"text": "Hi"},
        },
        "attachments": [],
    }
    payload["idempotency_key"] = compute_idempotency_key(payload)
    obj = TypeAdapter(OutboxPayloadV1).validate_python(payload)
    assert obj.kind == "email"


def test_invalid_payload_fails():
    bad = {"schema": "clowbot.outbox.v1", "kind": "email", "idempotency_key": "x"}
    try:
        TypeAdapter(OutboxPayloadV1).validate_python(bad)
        assert False, "expected validation error"
    except Exception:
        assert True
