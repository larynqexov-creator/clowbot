# Skill: grant_application_pipeline

## Purpose
Автоматически пройти цикл: найти гранты → оценить соответствие → создать черновик заявки → поставить дедлайны/таски → подготовить submission package (без внешних токенов).

## Trigger
Когда появляется задача типа GRANT или Project Brief для научного финансирования.

## Default Autonomy Level
A2 (execute GREEN). A4 для отправки/коммуникаций через approvals.

## Risk Profile
- GREEN: анализ, черновики, создание tasks, сохранение документов, создание календарного stub.
- YELLOW: календарь/уведомления (через stub/outbox).
- RED: реальная отправка заявки, контактирование новых людей/организаций.

## Inputs
- keywords (list)
- applicant_profile_text (string)
- constraints (deadline, field, geography) — optional

## Outputs / Required Artifacts
- GRANT_SHORTLIST.json
- MATCH_ANALYSIS.md
- DRAFT_APPLICATION.md
- BUDGET.md (или template)
- DEADLINES.md
- tasks created (>=3)
- outbox message(s) if any communication is needed

## State Machine
NEW → SOURCED → ANALYZED → DRAFTED → SCHEDULED → TASKED → PACKAGED → DONE (or FAILED)

## Steps
1) Source: shortlist (mock or local KB)
2) Analyze: score + pick best 3
3) Draft: create application draft + structure
4) Budget: outline
5) Deadlines: calendar stub/outbox
6) Tasks: outline/budget/submission
7) Package: prepare “submission package” folder/document

## Tools Used (ToolRegistry)
- calendar_stub_create_event (YELLOW)
- notify_stub (YELLOW)
- (later) email_send (YELLOW/RED depending on allowlist)

## Acceptance Criteria
- [ ] Все обязательные артефакты созданы
- [ ] Есть tasks + deadline representation
- [ ] Есть audit trail по шагам

## Tests / Verification
- POST /science/grants/run → status NOTIFIED
- (future) GET artifacts endpoint: документы/таски/артефакты
