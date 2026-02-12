from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.memory.bootstrap import check_bootstrap_fresh


def require_bootstrap(db: Session, *, tenant_id: str) -> str:
    ok, context_version, reason = check_bootstrap_fresh(db, tenant_id=tenant_id)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BOOTSTRAP_REQUIRED",
                "reason": reason,
                "context_version": context_version,
                "hint": "Call POST /memory/bootstrap",
            },
        )
    return context_version or ""
