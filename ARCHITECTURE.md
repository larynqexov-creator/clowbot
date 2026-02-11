# ARCHITECTURE

## Stack (default)
- FastAPI (Core API)
- PostgreSQL (multi-tenant via `tenant_id`)
- Redis + Celery (workers)
- Qdrant (vector memory)
- MinIO (object store)
- Docker Compose
- GitHub Actions CI

## Modules (MVP)
- `app/main.py` — FastAPI app + health
- `app/api/routers/*` — HTTP API
- `app/models/*` — SQLAlchemy tables
- `app/domain/science/grants/*` — grants workflow (mock)

## Jarvis layer (in progress)
- Approvals Queue (`pending_actions` + `/actions/*`)
- Outbox (`outbox_messages` + `/outbox`)
- Custom Mindmaps (saved in `documents` with `doc_type=mindmap_custom`)

## Security model
- GREEN: автономно
- YELLOW: автономно + лог/очередь
- RED: только через approval (confirmation_token)
