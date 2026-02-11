# STATUS

Последнее обновление: 2026-02-11

## Сейчас (MVP → Jarvis слой)
- [x] Репозиторий содержит self-host MVP (FastAPI + Postgres + Redis + Qdrant + MinIO + Celery)
- [x] Science grants workflow (mock) — запуск через API
- [x] Добавлен контракт Jarvis Mode: `CLOWDBOT_SUPERMISSION.md`
- [ ] Approvals Queue (RED actions): таблица + API + воркер-исполнение
- [ ] Outbox (YELLOW send queue): таблица + API + воркер-отправка/лог
- [x] Custom Mindmaps: endpoints save/load (пока хранение в `documents`)
- [x] Mindmap overview endpoint

## Следующие шаги (конкретно)
1) ToolRegistry v1 (STUB): enforcement GREEN/YELLOW/RED + audit_log на каждый TOOL_CALL/TOOL_RESULT.
2) Worker executor: Celery task `process_pending_actions` (APPROVED → ToolRegistry → DONE/FAILED).
3) Outbox dispatcher (STUB): отдельная таска на будущее (пока только QUEUED список).
4) Добавить `skills/` + первые skill cards.
5) Weekly review шаблон + поддержка портфеля (PORTFOLIO.md уже добавлен).
