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
1) Довести Skills Library до runnable: добавить (минимальный) skill-runner или хотя бы маппинг `TaskType -> skill`.
2) Добавить weekly review skill + шаблон (портфель уже есть).
3) Усилить идемпотентность dispatcher на Postgres (FOR UPDATE SKIP LOCKED) + статус SENDING.
4) (Опционально) endpoint для получения preview outbox сообщения.
