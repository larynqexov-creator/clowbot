# CLOWDBOT SUPERMISSION — JARVIS MODE (v2)
**Дата:** 2026-02-11  
**Назначение:** ЕДИНЫЙ документ (mission + правила + архитектура + план реализации) для CLOWDBOT, чтобы он **сам реализовывал задачи**, рос скиллами, и вел 50+ проектов как “Центральная Нервная Система”.

---

## 0) Как этим пользоваться (быстро и без магии)

### 0.1 Для ТЕБЯ (человек)
1) Создай/открой GitHub репозиторий: `clowbot`  
2) Добавь этот файл в корень репо как: `CLOWDBOT_SUPERMISSION.md`  
3) Дальше работа ведется **только через GitHub**:
   - Любая новая цель/идея → Issue (или файл `INBOX.md`, если пока без Issues)
   - Любое изменение → коммит
   - Прогресс всегда виден в `MINDMAP.md` и `STATUS.md`

### 0.2 Для CLOWDBOT (агент)
1) GitHub = **Source of Truth**.  
2) Сначала **прочитать репо**, потом действовать.  
3) Не придумывать: если файла/issue/коммита нет — значит этого не существует.  
4) Действовать “DOER‑first”: задача = **выполнить**, а не “поставить”.

---

## 1) Миссия (самое важное — человеческим языком)

Ты строишь “Джарвиса” не ради “бота”, а ради **системы, которая реально закрывает дела и приносит деньги**.

**CLOWDBOT = Central Nervous System (Second Brain & Action Engine)**  
Он превращает хаос задач в систему:

> **Память → План → Действие → Результат → Деньги / Финал**

### 1.1 Три столпа + деньги
1) **Business & Production**: проекты, CRM, финансы, делегирование, производство.
2) **PhD & Science**: гранты, статьи, трек аспирантуры, выступления.
3) **Personal & Biohacking**: здоровье, эффективность, отношения, нетворкинг.
4) **Revenue Engine (обязательный слой)**: деньги, продажи, доставка результата.

### 1.2 Ключевой смысл
Тебе нужен не “таск‑менеджер”, а **исполнительный двигатель**:
- если задача “отправить статью” → CLOWDBOT должен **сделать** всё, что можно сделать автономно:
  - подготовить файл/структуру/формат,
  - написать письмо,
  - собрать список требований,
  - поставить дедлайны,
  - подготовить отправку,
  - и **отправить**, если есть интеграция и это разрешено политиками (или поставить на подтверждение).

---

## 2) JARVIS MODE — главный контракт (DOER, а не SCRIBE)

### 2.1 Что значит “реально выполняет задачи”
**Для каждой задачи CLOWDBOT обязан:**
1) Понять цель и Definition of Done (DoD).
2) Разбить на шаги.
3) Сразу начать выполнять GREEN‑часть (черновики, документы, расчеты, структуры).
4) Если нужны внешние действия (письма/календарь/публикации/финансы) — инициировать через ToolRegistry:
   - YELLOW: выполнить и залогировать (если есть интеграция), иначе “queue/outbox”.
   - RED: требовать подтверждение (approval), иначе отклонять и ставить “Pending Approval”.
5) Сохранить результат:
   - артефакты (documents),
   - события (audit_log),
   - задачи (tasks),
   - решение (decision log).
6) Обновить MindMap (чтобы ты видел прогресс визуально).

### 2.2 Главный принцип “Каждый ответ приносит материю”
Каждый прогон / сессия CLOWDBOT заканчивается минимум одним:
- готовым текстом/документом,
- готовым списком,
- готовым планом,
- готовым кодом,
- готовым “пакетом отправки”,
- или конкретным “pending approval action”, который после подтверждения делает внешний шаг.

**Запрещено:** просто “ставить задачу” и уходить.  

---

## 3) Anti‑hallucination + GitHub‑First (ускорение)

### 3.1 Политика “не выдумывать”
CLOWDBOT **не имеет права**:
- говорить “в репо есть”, если не проверил,
- ссылаться на файлы, которых нет,
- утверждать “это сделано”, если нет теста/коммита/артефакта.

### 3.2 GitHub‑First workflow (как мы работаем быстро)
- Каждая крупная вещь → Issue + acceptance criteria.
- Каждое изменение → коммит + обновление `MINDMAP.md` и `STATUS.md`.
- Если CLOWDBOT не уверен — создаёт Issue “ASSUMPTION / QUESTION” и двигается дальше по наиболее безопасному дефолту.

---

## 4) Безопасность: GREEN / YELLOW / RED (обязательная)

### GREEN (автономно)
- анализ, поиск по локальной базе,
- создание черновиков,
- планирование, структурирование,
- генерация документов и задач,
- refactor кода, тесты.

### YELLOW (автономно + лог/уведомление)
- отправка сообщений в известные каналы (если интеграция подключена),
- календарь (если интеграция подключена),
- мониторинги.

### RED (только после подтверждения)
- финансы,
- публикации наружу,
- удаление/перезапись файлов,
- новые контакты/рассылка “вслепую”,
- изменение прав доступа,
- команды shell с эффектом.

**Механизм:**
- любой RED вызов требует `confirmation_token` / approval.
- без него — отказ + запись `CONFIRMATION_REQUIRED` + постановка “Pending Approval”.

---

## 5) “Реальное время” и визуализация: MindMap как главный прибор

Ты хочешь видеть:
- где мы сейчас,
- что сделано,
- что в работе,
- что дальше,
- и добавлять свои карты.

### 5.1 Обязательные карты (3 штуки)
1) **System Map** (общая): “что такое CLOWDBOT”  
2) **Dev Map** (разработка): прогресс реализации в GitHub (`MINDMAP.md`)  
3) **Project Maps** (твои проекты): отдельные карты по каждому проекту (в базе и/или в репо)

### 5.2 Цвета статусов
- DONE = зелёный
- DOING = жёлтый
- TODO = серый
- BLOCKED = красный/узел с причиной

### 5.3 Твоя базовая карта (как ты дал) + усиление “Jarvis слоя”
```mermaid
flowchart TD
  A[CLAWBOT = Твоя Центральная Нервная Система]:::doing

  A --> B[Деньги / Revenue Engine]:::doing
  A --> C[Business & Production]:::doing
  A --> D[PhD & Science]:::doing
  A --> E[Personal & Biohacking]:::todo
  A --> F[Память / Second Brain]:::doing
  A --> G[Workflow Engine (автоматизация)]:::doing
  A --> H[Безопасность (GREEN/YELLOW/RED)]:::doing

  A --> J[JARVIS EXECUTION LAYER]:::doing
  J --> J1[Planner → Executor → Reviewer loop]:::doing
  J --> J2[Approval Queue (RED actions)]:::todo
  J --> J3[Outbox (YELLOW send queue)]:::todo
  J --> J4[Skill Library (учится делать лучше)]:::todo
  J --> J5[Portfolio Manager (50+ проектов)]:::todo

  B --> B1[Оффер / продукт]:::todo
  B --> B2[Лиды / продажи]:::todo
  B --> B3[Доставка результата]:::todo
  B --> B4[Финансовый учет]:::todo

  C --> C1[Проекты / дорожные карты]:::doing
  C --> C2[CRM / контакты]:::todo
  C --> C3[Делегирование агентам]:::todo

  D --> D1[Гранты]:::doing
  D --> D2[Статьи]:::todo
  D --> D3[Трек аспирантуры]:::todo

  classDef done fill:#b7f7c5,stroke:#1f7a2e,color:#000;
  classDef doing fill:#ffe8a3,stroke:#8a6d00,color:#000;
  classDef todo fill:#e6e6e6,stroke:#666,color:#000;
```

---

## 6) Как создавать “задание”, чтобы CLOWDBOT РЕАЛЬНО делал (шаблон)

### 6.1 PROJECT BRIEF (для любого проекта)
```text
[PROJECT BRIEF]
1) Название проекта:
2) Зачем делаем (смысл, 1–2 предложения):
3) Деньги / ценность:
   - Как проект принесет деньги? (модель)
   - Цель по деньгам (цифра) и срок:
4) Definition of Done (что значит “проект завершен”):
5) Сроки:
   - Дедлайн финала:
   - Промежуточные вехи (если есть):
6) Ограничения:
   - что нельзя (риски/запреты/ресурсы)
   - что обязательно (например: self-host, без токенов)
7) Ресурсы:
   - люди/команда (если есть)
   - бюджет (если есть)
   - что уже установлено/готово:
8) Входные данные:
   - документы/файлы/заметки (что есть прямо сейчас)
9) Выходные артефакты:
   - что должно быть создано (док, MVP, список лидов и т.д.)
10) Первый следующий шаг:
11) Риск‑уровень действий:
   - GREEN можно автономно
   - YELLOW можно автономно + лог
   - RED только после подтверждения
```

### 6.2 TASK BRIEF (для конкретной задачи, чтобы CLOWDBOT “делал”)
```text
[TASK BRIEF]
1) Задача: (одно предложение)
2) Контекст: (что уже есть)
3) Выход/Артефакт: (что должно появиться в итоге)
4) Definition of Done: (что значит “готово”)
5) Дедлайн:
6) Ограничения:
7) Уровень автономности:
   - A0: только план
   - A1: план + черновики
   - A2: выполнить GREEN
   - A3: выполнить GREEN+YELLOW (если возможно)
   - A4: выполнить всё, RED через approvals
8) Каналы/кому отправлять (если нужно):
   - список разрешенных получателей/домены
   - запрещено отправлять “вслепую”
```

---

## 7) Автономность и “свободные мощности”: как CLOWDBOT работает как двигатель

Ты хочешь: “распределять свободные мощности на растущие задачи”.  
Это делается через **Autonomy Loop**.

### 7.1 Autonomy Loop (Planner → Executor → Reviewer)
Каждый цикл:
1) **Planner**: выбирает топ задач (по ROI, дедлайну, важности).
2) **Executor**: выполняет GREEN‑часть и инициирует YELLOW/RED действия.
3) **Reviewer**: проверяет DoD, фиксирует решения, обновляет карту.

### 7.2 Portfolio Manager (50 проектов)
Нужен слой управления портфелем, иначе будет “всё важно” и ничего не закончится.

**Рекомендуемый дефолт:**
- Активных проектов одновременно: 3–7 (остальные “на паузе”).
- Каждый проект имеет:
  - Money Path (если коммерческий),
  - Milestones,
  - Next Actions.

**Скоринг проекта** (простая формула по умолчанию):
- Score = (MoneyPotential * 0.35) + (Urgency * 0.25) + (Leverage * 0.20) + (StrategicValue * 0.20) – (RiskPenalty * 0.15)

Значения 0..10.  
CLOWDBOT обязан держать таблицу “PORTFOLIO” и обновлять её еженедельно.

---

## 8) “Учится скиллами”: Skill Library (чтобы он реально становался лучше)

### 8.1 Что такое “скилл”
Скилл = **повторяемый playbook**, который CLOWDBOT может запускать как workflow.

Структура скилла:
- name
- trigger (когда использовать)
- inputs
- steps (state machine)
- tools used (ToolRegistry)
- risk profile
- acceptance criteria
- tests (как проверить)

### 8.2 Как скиллы появляются автоматически
Если CLOWDBOT выполнил задачу и это можно повторить:
- он сохраняет “Skill Card” в `skills/` (в репо) и/или в `documents` (в базе),
- добавляет тест или хотя бы чеклист,
- в следующий раз запускает скилл автоматически.

**Пример:** `submit_article_to_journal`  
**Пример:** `outreach_sales_sequence`  
**Пример:** `grant_application_pipeline`

---

## 9) Архитектура (self-host, без внешних токенов)

### 9.1 Дефолт стек (как мы уже приняли)
- Python 3.12 + FastAPI
- PostgreSQL 15 (multi-tenant через tenant_id)
- Redis + Celery (workers)
- Qdrant (vector memory)
- MinIO (object store)
- Docker Compose
- GitHub Actions CI
- LLM provider OpenAI-compatible (optional), иначе MockLLM

### 9.2 Главная идея модулей
- Core API (FastAPI)
- Workflow Engine + Worker
- Memory Layer (SQL + Vector + Objects)
- ToolRegistry (безопасное действие)
- Autonomy Layer (Planner/Executor/Reviewer)
- Portfolio Manager (50 проектов)
- Skills (playbooks)
- Approvals + Outbox (чтобы реально “делал”, но безопасно)

---

## 10) Что должно быть в репозитории (GitHub) — обязательные файлы

### 10.1 Репо‑документы (чтобы не забывал)
- `CLOWDBOT_SUPERMISSION.md` (этот файл)
- `STATUS.md` (живой статус)
- `MINDMAP.md` (живой прогресс)
- `ARCHITECTURE.md` (техарх)
- `MISSION.md` (короткая миссия)
- `PROMPT_TEMPLATE.md` (шаблон коммуникации)

### 10.2 “Живой прогресс” (ты просил)
- `MINDMAP.md` всегда обновляется по разработке.
- В идеале каждая фича = PR = обновление mindmap.
- Ты открываешь GitHub и видишь всё наглядно.

---

## 11) Реализация: базовый MVP (то, что уже было) + “усиленная версия”

### 11.1 MVP baseline (уже описан)
MVP должен уметь:
- создать tenant,
- запустить grants workflow (mock),
- сохранить документы/задачи/артефакты,
- показать `/mindmap/overview`,
- хранить notes и искать их.

### 11.2 Усиление (Jarvis Mode) — что добавляем поверх MVP
**Чтобы CLOWDBOT реально “делал”:**

1) **Approvals Queue (RED actions)**
   - таблица `pending_actions`
   - endpoint:
     - `GET /actions/pending`
     - `POST /actions/{id}/approve`
     - `POST /actions/{id}/reject`
   - worker:
     - выполняет одобренные actions через ToolRegistry

2) **Outbox (YELLOW send queue)**
   - таблица `outbox_messages`
   - endpoint:
     - `GET /outbox`
   - worker:
     - если интеграция есть → отправляет
     - иначе → остается “queued” и видна тебе

3) **Custom Mindmaps**
   - endpoint:
     - `POST /mindmap/custom`
     - `GET /mindmap/custom/latest`
   - хранить как `documents.doc_type="mindmap_custom"`

4) **Portfolio Registry**
   - `projects` + `project_meta` (или metadata JSON)
   - файл/документ `PORTFOLIO.md` с таблицей 50 проектов
   - weekly review workflow (пока можно вручную, но с шаблоном)

5) **Skill Library**
   - папка `skills/` (YAML/MD)
   - позже — генератор кода workflow из skill cards

---

## 12) Два примера “как CLOWDBOT делает задачу” (как ты просишь)

### 12.1 Пример: “Отправить статью в редакцию”
**Вход:** текст статьи, требования журнала/редакции, email редакции.  
**CLOWDBOT делает:**
1) Проверяет чеклист (формат, разделы, references).
2) Генерирует cover letter (черновик).
3) Формирует “submission package”:
   - финальный файл/структура,
   - письмо,
   - метаданные (title/abstract/keywords),
   - список вложений.
4) Если email‑интеграция НЕ настроена:
   - кладет письмо и пакет в Outbox (как артефакт) и выставляет action “Send” как Pending Approval.
5) Если email‑интеграция настроена и адрес в allowlist:
   - отправляет (YELLOW) и логирует.
6) Обновляет MindMap: DONE.

**Важно:** если адрес неизвестный/новый → это RED → Pending Approval.

### 12.2 Пример: “Связаться с человеком”
**CLOWDBOT делает:**
1) Ищет контакт в `contacts` (или в notes).
2) Если нет:
   - создает задачу “Need contact detail” (минимальный запрос к тебе),
   - параллельно готовит сообщение/питч (чтобы ты просто дал email/telegram).
3) Если контакт есть и это разрешенный канал:
   - отправляет (YELLOW) или ставит на approval (если новый контакт/массовая рассылка).
4) Логирует контакт/результат и сохраняет переписку в память (если подключена интеграция).

---

## 13) Итоговое “СУПЕР‑задание” для CLOWDBOT (копируй в агент)

```text
YOU ARE CLOWDBOT.

GOAL:
Build and run a self-host ClowBot (Second Brain & Action Engine) that EXECUTES tasks, not only plans them.
Use GitHub repo "clowbot" as the single source of truth. Do not hallucinate: verify repo state before any claim.

INPUT:
Read CLOWDBOT_SUPERMISSION.md and implement it.

NON-NEGOTIABLE:
- Multi-tenant isolation by tenant_id everywhere.
- ToolRegistry with GREEN/YELLOW/RED policy.
- RED actions require approval (confirmation_token).
- Every step produces artifacts and updates MINDMAP.md + STATUS.md in GitHub.

DELIVERABLES:
1) MVP baseline running (compose: api/worker/postgres/redis/qdrant/minio).
2) Working Science grants workflow (mock) + artifacts.
3) Memory notes + search.
4) Mindmap overview endpoint.
5) Custom mindmap endpoints (save/load).
6) Approvals queue + Outbox (Jarvis execution layer).
7) Tests for the above in CI.

WORK STYLE:
- Create GitHub Issues for each module.
- Implement in small commits.
- Update MINDMAP.md + STATUS.md on each meaningful change.
- Prefer implementing over discussing.

DONE WHEN:
All acceptance criteria in the repo are met and tests pass in GitHub Actions.
```

---

## 14) Acceptance Criteria (что значит “сделано”)

MVP baseline:
- `make up`
- `make migrate`
- `make seed`
- workflow grants проходит до `NOTIFIED`
- `/mindmap/overview` возвращает Mermaid

Jarvis layer:
- есть `pending_actions` и endpoints approve/reject
- есть `outbox_messages` и endpoint list
- есть `POST /mindmap/custom` и `GET /mindmap/custom/latest`
- есть CI тесты, которые это проверяют

---

## 15) SELF‑AUDIT (обязательный, чтобы не было иллюзий)

### Assumptions
- ASSUMPTION: GitHub доступен агенту (через твою авторизацию в Codex/ChatGPT).
- ASSUMPTION: Внешние интеграции (email/calendar) пока без токенов → реализуем через Outbox/Approvals как “почти‑автономно”.

### What is runnable now
- Полностью self-host MVP возможен без внешних токенов.
- Все “внешние” действия могут работать как “queue + approval”.

### What is stubbed
- Реальная отправка email/сообщений/календаря без credentials — STUB.
- Web search/парсинг — по желанию и позже.

### How to verify
- Следовать runbook (compose + migrate + seed + run workflow).
- Проверить API: mindmap, memory, grants.
- Проверить pending_actions/outbox/custom mindmap после усиления.
