# Skill: submit_article_package

## Purpose
Сделать “submission package” статьи так, чтобы остался только approve/send (или copy/paste из outbox).

## Trigger
Задача типа ARTICLE: “Отправить статью в редакцию/журнал”.

## Default Autonomy Level
A2 (готовит пакет). A4 для отправки через approval.

## Risk Profile
- GREEN: форматирование, чеклисты, cover letter, metadata, пакет.
- YELLOW: отправка в allowlist редакции/журнала (если интеграция есть).
- RED: отправка новому контакту, публикация наружу без согласования.

## Inputs
- manuscript text (или ссылка на документ в системе)
- target journal name
- journal requirements (если нет — создать “requirements request” doc)
- allowed recipients/domains (allowlist)

## Outputs / Required Artifacts (MUST)
- MANUSCRIPT.md (или .docx later)
- ABSTRACT.txt
- KEYWORDS.txt
- COVER_LETTER.txt
- JOURNAL_REQUIREMENTS.md
- SUBMISSION_CHECKLIST.md
- OUTBOX item: “Submission Email” (если нет реальной отправки)
- Pending action: send_submission (если требует approval)

## State Machine
NEW → REQUIREMENTS → FORMATTED → LETTER_READY → CHECKED → PACKAGED → QUEUED_OR_SENT → DONE (or FAILED)

## Steps
1) Requirements: собрать требования (или зафиксировать неизвестность)
2) Format manuscript: привести к структуре
3) Create cover letter (версия 1)
4) Prepare metadata (abstract/keywords)
5) Checklist: валидация на основе requirements
6) Package: собрать единый “send bundle”
7) Queue send: создать outbox message (email payload) + pending action (если нужно)

## Tools Used (ToolRegistry)
- notify_stub (YELLOW)
- (later) email_send (YELLOW/RED)

## Acceptance Criteria
- [ ] Пакет готов полностью (все файлы/доки есть)
- [ ] Есть outbox preview (что будет отправлено)
- [ ] Если отправка требует approval — есть pending action

## Tests / Verification
- Проверить наличие артефактов в documents/object store
- Проверить наличие outbox_messages(QUEUED) + preview_document_id
