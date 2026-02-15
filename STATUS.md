# STATUS

Последнее обновление: 2026-02-12

## Сейчас (MVP → Jarvis слой)
- [x] Репозиторий содержит self-host MVP (FastAPI + Postgres + Redis + Qdrant + MinIO + Celery)
- [x] Local stack runbook + stop/restart scripts (PowerShell)
- [x] Science grants workflow (mock) — запуск через API
- [x] Контракт Jarvis Mode: `CLOWDBOT_SUPERMISSION.md` (v3)
- [x] Approvals Queue (RED actions): таблица + API + worker executor
- [x] Outbox (YELLOW send queue): таблица + API + STUB dispatcher
- [x] Custom Mindmaps: endpoints save/load (хранение в `documents`)
- [x] Mindmap overview endpoint

## Done (Roadmap)
- [x] `POST /tasks/{id}/run_skill` (TaskType binding)
- [x] Allowlist как документ в БД: `Document(domain=policy, doc_type=policy_allowlist)`
- [x] Skill: `sales_outreach_sequence` (Telegram)
- [x] Dispatcher locking на Postgres: `FOR UPDATE SKIP LOCKED`
- [x] Portfolio Manager: `weekly_review` + active set 3–7 + scoring

## Context / Bootstrap (Never Forget)
- [x] Repo SoT файлы: `BOOTSTRAP.md`, `NEXT.md`, `BACKLOG.md` (+ существующие mission/status/mindmap)
- [x] `POST /memory/bootstrap` → апсерт SoT→DB `documents` + vector upsert (best-effort)
- [x] `GET /memory/bootstrap/status`
- [x] `GET /memory/next`
- [x] Hard guard `BOOTSTRAP_REQUIRED` для `/skills/run` и `/tasks/{id}/run_skill`
- [x] `context_version` пишется в audit (`SKILL_RUN_STARTED`, `EXECUTOR_TICK`, `OUTBOX_DISPATCH_ATTEMPT`)

## Next
См. `NEXT.md` (единственный следующий шаг).
