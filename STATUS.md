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
1) Добавить минимальный worker-loop: обработка `pending_actions` со статусом APPROVED → DONE/FAILED (пока stub ToolRegistry).
2) Добавить первичную структуру Skill Library (`skills/`) + 1 пример skill card.
3) Добавить PORTFOLIO.md (шаблон таблицы на 50 проектов) + weekly-review шаблон.
4) Протянуть Memory Notes + Search API (если этого ещё нет в коде репо).
