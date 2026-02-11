# Outbox Payload Spec v1

This document defines `clowbot.outbox.v1` payload envelope used in `outbox_messages.payload`.

## Envelope
- `schema`: fixed string `clowbot.outbox.v1`
- `kind`: `email | telegram | github_issue` (discriminator)
- `idempotency_key`: deterministic (sha256)
- `context`: {project_id, task_id, workflow_id, source, trace_id}
- `policy`: {risk, requires_approval, allowlist}
- `message`: channel-specific (see below)
- `attachments`: list of object-store references

## Allowlist enforcement
If targets are not allowlisted, the server auto-upgrades:
- `policy.risk=RED`
- `policy.requires_approval=true`

## Idempotency
Uniqueness is enforced by `(tenant_id, idempotency_key)`.

See code: `app/schemas/outbox_v1.py`, `app/core/outbox_policy.py`, `app/outbox/service.py`.
