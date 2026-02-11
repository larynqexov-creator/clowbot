# STATUS

Последнее обновление: 2026-02-11

## Сейчас (MVP → Jarvis слой)
- [x] Репозиторий содержит self-host MVP (FastAPI + Postgres + Redis + Qdrant + MinIO + Celery)
- [x] Science grants workflow (mock) — запуск через API
- [x] Контракт Jarvis Mode: `CLOWDBOT_SUPERMISSION.md` (v3)
- [x] Approvals Queue (RED actions): таблица + API + worker executor
- [x] Outbox (YELLOW send queue): таблица + API + STUB dispatcher
- [x] Custom Mindmaps: endpoints save/load (хранение в `documents`)
- [x] Mindmap overview endpoint

## Следующие шаги (конкретно)
1) Добавить endpoint `POST /tasks/{id}/run_skill` (binding TaskType → skill) + хранение TaskType в tasks.meta.
2) Добавить allowlist document (doc_type=policy_allowlist) вместо env-only.
3) Реализовать второй runnable skill: `sales_outreach_sequence` (создаёт 3–5 outbox telegram/email сообщений).
4) Улучшить идемпотентность dispatcher на Postgres: `FOR UPDATE SKIP LOCKED`.
