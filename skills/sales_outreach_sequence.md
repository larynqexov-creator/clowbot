# Skill: sales_outreach_sequence

## Purpose
Быстро запустить Revenue Engine: оффер → лиды → сообщения → outbox → approvals → (later) реальная отправка.

## Trigger
Проект/задача типа SALES: “Нужно заработать / найти клиентов / продать”.

## Default Autonomy Level
A2 (создает всё внутри). A3 для отправки в разрешенные каналы. A4 для широких рассылок через approvals.

## Risk Profile
- GREEN: оффер, ICP, списки, тексты сообщений, план доставки.
- YELLOW: отправка в известные каналы/контакты (если интеграции есть).
- RED: массовая рассылка, новые контакты, любые финансовые действия.

## Inputs
- product/service description
- target audience constraints
- allowed channels/domains (allowlist)

## Outputs / Required Artifacts
- OFFER.md (3 варианта)
- ICP.md
- LEADS.csv (20+)
- OUTREACH_MESSAGES.md (5 шаблонов)
- DELIVERY_PLAN.md
- outbox_messages (QUEUED) для каждого сообщения (или батч)

## State Machine
NEW → OFFER_READY → ICP_READY → LEADS_READY → MESSAGES_READY → QUEUED → DONE (or FAILED)

## Steps
1) Offer: сформировать 3 оффера (простой/средний/премиум)
2) ICP: портрет клиента + pain points
3) Leads: 20 потенциальных контактов/каналов (без токенов — просто список источников)
4) Messages: 5 шаблонов (short/long/follow-up)
5) Queue: создать outbox items (без отправки)
6) Approvals: если нужно — создать pending action на “send batch”

## Tools Used (ToolRegistry)
- notify_stub (YELLOW)
- (later) send_email/send_message adapters

## Acceptance Criteria
- [ ] Все артефакты созданы
- [ ] В outbox есть очередь сообщений с preview
- [ ] Нет “массовой отправки” без approval

## Tests / Verification
- GET /outbox показывает queued items
- dispatcher переводит queued → stub_sent
