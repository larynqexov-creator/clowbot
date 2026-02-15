# NEXT

## CAPTURE & PROJECT LIBRARY v1
- [x] feat/project-library-v1 ready: pytest x3 green + alembic migration included
- [ ] Add Telegram Capture Bridge module (optional; feature-flag by TELEGRAM_BOT_TOKEN)
- [ ] After merge: run `POST /memory/bootstrap` (SoT→DB)

**Single next step** (this file must never be empty).

## Next step
Implement **Real Outbox Send v1 — SMTP Email Adapter**:
- Email sender adapter (SMTP/provider) behind approvals + allowlist
- Keep GitHub Issue adapter DONE

## Definition of Done
- Outbox dispatcher can deliver at least one real channel (email or github_issue)
- Approval + allowlist rules remain enforced
- Preview artifacts still stored
- Tests pass

Owner: Clowbot
