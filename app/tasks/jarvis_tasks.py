from __future__ import annotations

import logging

from app.core.celery_app import celery
from app.core.db import SessionLocal
from app.core.tool_registry import ConfirmationRequired, execute_pending_action
from app.models.tables import PendingAction
from app.util.time import now_utc

log = logging.getLogger("jarvis_tasks")


@celery.task(name="app.tasks.jarvis_tasks.process_pending_actions")
def process_pending_actions(*, limit: int = 25) -> dict:
    """Process APPROVED pending actions.

    STUB executor:
    - Executes via ToolRegistry
    - Updates action status: DONE / FAILED
    - External sends are not performed; routed to Outbox.
    """

    db = SessionLocal()
    try:
        actions = (
            db.query(PendingAction)
            .filter(PendingAction.status == "APPROVED")
            .order_by(PendingAction.created_at.asc())
            .limit(limit)
            .all()
        )

        done = 0
        failed = 0
        queued = 0

        for a in actions:
            try:
                res = execute_pending_action(db, action=a)
                if res.status == "QUEUED":
                    a.status = "DONE"  # action completed by producing an outbox item
                    queued += 1
                else:
                    a.status = "DONE"
                a.decided_at = a.decided_at or now_utc()
                db.commit()
                done += 1
            except ConfirmationRequired:
                # Should not happen for APPROVED; keep as APPROVED for visibility
                db.rollback()
                log.warning("Action %s blocked: confirmation required", a.id)
                failed += 1
            except Exception as e:
                db.rollback()
                log.exception("Action %s failed: %s", a.id, str(e))
                # Mark failed
                try:
                    a2 = db.query(PendingAction).filter(PendingAction.id == a.id).one_or_none()
                    if a2:
                        a2.status = "FAILED"
                        a2.decided_at = now_utc()
                        db.commit()
                except Exception:
                    db.rollback()
                failed += 1

        return {"ok": True, "done": done, "queued": queued, "failed": failed}
    finally:
        db.close()
