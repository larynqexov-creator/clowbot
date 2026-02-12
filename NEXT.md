# NEXT

**Single next step** (this file must never be empty).

## Next step
Implement **Real Outbox Send v1**:
- Email sender adapter (SMTP or provider) behind approvals + allowlist
- GitHub Issue sender adapter behind approvals + allowlist

## Definition of Done
- Outbox dispatcher can deliver at least one real channel (email or github_issue)
- Approval + allowlist rules remain enforced
- Preview artifacts still stored
- Tests pass

Owner: Clowbot
