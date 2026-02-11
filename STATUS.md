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
1) Закончить Outbox Contract v1: миграция 0003 + запись payload/idempotency_key в outbox_messages.
2) Завершить Preview Pack: запись raw preview artifacts в MinIO + object_keys в meta.preview.
3) Skill Runner v0: расширить submit_article_package (manuscript_doc_id support + attachments) + добавить /tasks/{id}/run_skill (binding).
4) Добавить allowlist document (doc_type=policy_allowlist) вместо env-only.
