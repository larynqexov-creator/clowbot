# Project Library v1 (Capture)

Goal: send materials (text/photo/pdf/audio/voice) to ClowBot **per project** with minimal friction.

Principles:
- Single simple entry channel: `/inbox` (API). Telegram bridge is optional.
- Multi-tenant: all storage and search must be tenant-scoped.
- No external tokens required for ingestion/processing.

## Bootstrap rule
Most endpoints are guarded by the SoT bootstrap guard.

Required bootstrap flow:
- `POST /memory/bootstrap`
- `GET /memory/bootstrap/status`

Exception: `/inbox/*` is intentionally **not hard-blocked** by bootstrap (simple entry), but anything that depends on SoT (skills/executors) still requires a fresh bootstrap.

## Data model
### projects
- `tenant_id, id, slug, title, status, created_at`

### inbox_items
- `tenant_id, id, project_id (nullable), kind, title, text, object_key, content_type, status, tags[], source, created_at`

### project_assets
- `tenant_id, id, project_id, inbox_item_id (nullable), filename, content_type, object_key, sha256, size_bytes, created_at`

### project_decisions
- `tenant_id, id, project_id, title, decision, rationale, links[], created_at`

## Storage keys
Binary assets are stored to object_store with key:

`{tenant_id}/projects/{project_id}/assets/{asset_id}/{filename}`

## API endpoints
### Projects
- `POST /projects` `{slug,title}`
- `GET /projects`

### Inbox
- `POST /inbox/text` `{project_id|project_slug optional, title, text, tags[], source}`
- `POST /inbox/file` `multipart/form-data`
  - `file` (UploadFile)
  - `project_id` or `project_slug` (optional)
  - `title` (optional)
  - `tags` (optional; CSV)
  - `source` (optional)

- `GET /inbox/unassigned`

### Library
- `GET /projects/{id}/library`
- `GET /projects/{id}/library/index` (markdown index document)

### Mindmap
- `GET /mindmap/project/{id}` → `{mermaid,map_index}`

## Processing pipeline
After `POST /inbox/file`:
- Creates `inbox_items` row (status=QUEUED)
- Stores file bytes in object_store
- Enqueues Celery task `process_inbox_item(inbox_item_id)`

Task `process_inbox_item`:
- On Postgres: uses `FOR UPDATE SKIP LOCKED` row lock (best-effort)
- Idempotent:
  - If inbox item is already DONE → returns ok
  - Will not create duplicate `Document(doc_type=extracted_text)` for the same inbox item
- PDF:
  - Extracts text via `pypdf`
  - Creates `Document(domain=project, doc_type=extracted_text)` with `meta.inbox_item_id`
  - Best-effort vector upsert (tenant filter enforced by vector_store)
- Audio/Image:
  - STUB (no transcription/OCR in v1)

## Mindmap linking
A project mindmap is stored as:
- `Document(domain=mindmap, doc_type=project_mindmap)`

Response from `GET /mindmap/project/{project_id}`:
- `mermaid`: overview map (counts + top 7 recent items)
- `map_index`: `node_id -> {type,title, asset_id/doc_id/inbox_item_id, api_link}`

Mindmap + library index are regenerated after:
- new inbox text
- new inbox file processing completion
- new project decision

## Tests
- Text ingest stored + mindmap updated
- PDF ingest stored + extracted_text doc exists + mindmap index exists
- Works without TELEGRAM_BOT_TOKEN

## Outbox references
Outbox contract and preview specs:
- `docs/outbox_payload_spec_v1.md`
- `docs/outbox_preview_pack_spec_v1.md`
