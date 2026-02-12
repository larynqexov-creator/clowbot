# BOOTSTRAP (Source of Truth)

This file defines how Clowbot *wakes up*.

## Source of Truth files (repo)
Clowbot must treat these as canonical and refresh them into DB `documents` before doing any work:

- `CLOWDBOT_SUPERMISSION.md`  → `doc_type=mission`
- `STATUS.md`                → `doc_type=status`
- `NEXT.md`                  → `doc_type=next`
- `BACKLOG.md`               → `doc_type=backlog`
- `MINDMAP.md`               → `doc_type=mindmap_dev`
- `BOOTSTRAP.md`             → `doc_type=bootstrap`

## Session handshake ritual
For every new session / run:
1) Ensure bootstrap is fresh: call `POST /memory/bootstrap` (or detect it is fresh via `/memory/bootstrap/status`).
2) Print **CURRENT STATE** (10–20 lines) from `mission/status/next`.
3) Confirm **NEXT STEP (single)** from `NEXT.md`.
4) Only then execute skills / tasks.

## Guard rule
Any operation that changes the world MUST be blocked unless bootstrap is fresh:
- `/skills/run`
- `/tasks/{id}/run_skill`
- worker ticks (pending action executor / outbox dispatcher)

If required documents are missing or bootstrap is older than 24h → return/emit `BOOTSTRAP_REQUIRED`.
