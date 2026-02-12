# MINDMAP

Эта карта должна быть “читаемой глазами”: цели → ветки → что готово/что дальше.

Легенда:
- ✅ СДЕЛАНО
- 🟡 В РАБОТЕ
- ⬜ ПЛАН

```mermaid
mindmap
  root((Clowbot / JARVIS MODE))

    ✅ MVP baseline
      ✅ Docker Compose (api/worker/postgres/redis/qdrant/minio)
      ✅ Health endpoint
      ✅ Science grants workflow (mock)

    ✅ Jarvis execution layer
      ✅ Mindmap endpoints
        ✅ /mindmap/overview
        ✅ /mindmap/custom (save/latest)

      ✅ Approvals
        ✅ pending_actions table
        ✅ /actions/pending
        ✅ /actions/{id}/approve
        ✅ /actions/{id}/reject

      ✅ Outbox
        ✅ outbox_messages table
        ✅ /outbox list
        ✅ Outbox dispatcher (stub → preview)
        ✅ Telegram adapter (real send if allowlisted)

      ✅ ToolRegistry (stub)
        ✅ GREEN/YELLOW/RED enforcement
        ✅ audit_log (TOOL_CALL/TOOL_RESULT)
        ✅ action: telegram.send_message (default chat)
        ✅ action: outbox.send (approval gate)

      ✅ Outbox Contract v1
        ✅ Pydantic schemas + exported JSON Schema
        ✅ Idempotency key + uniqueness (tenant_id, idempotency_key)
        ✅ Allowlist enforcement (auto-upgrade to RED+approval)

      ✅ Preview Pack v1
        ✅ Preview Document (outbox_preview)
        ✅ Raw preview artifacts (MinIO best-effort)

      ✅ Skill Runner v0
        ✅ /skills/run
        ✅ Skill: submit_article_package
          ✅ creates cover letter + checklist
          ✅ creates outbox email payload
          ✅ creates pending_action outbox.send
          ✅ BLOCKED if missing inputs (creates tasks)

    ✅ Next (Roadmap)
      ✅ /tasks/{id}/run_skill (TaskType binding)
      ✅ Allowlist as document in DB (policy_allowlist)
      ✅ Skill: sales_outreach_sequence (runner)
      ✅ Dispatcher locking: FOR UPDATE SKIP LOCKED

    ✅ Portfolio Manager
      ✅ Weekly review skill
      ✅ Active set 3–7 + scoring

    ✅ Bootstrap / Never Forget
      ✅ Repo SoT files: BOOTSTRAP.md / NEXT.md / BACKLOG.md
      ✅ POST /memory/bootstrap (SoT → DB documents + vector best-effort)
      ✅ GET /memory/bootstrap/status
      ✅ GET /memory/next
      ✅ Hard guard: BOOTSTRAP_REQUIRED (/skills/run, /tasks/{id}/run_skill)
      ✅ Context version in audit (SKILL_RUN_STARTED / EXECUTOR_TICK / OUTBOX_DISPATCH_ATTEMPT)
      ✅ Tests
```
