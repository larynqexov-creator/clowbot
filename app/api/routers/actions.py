from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.core.db import SessionLocal
from app.models.tables import PendingAction
from app.util.time import now_utc

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.get("/pending")
def list_pending_actions(ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, _ = ctx

    items = (
        db.query(PendingAction)
        .filter(PendingAction.tenant_id == tenant_id, PendingAction.status == "PENDING")
        .order_by(PendingAction.created_at.asc())
        .all()
    )

    return {
        "items": [
            {
                "id": a.id,
                "risk_level": a.risk_level,
                "action_type": a.action_type,
                "payload": a.payload,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a in items
        ]
    }


@router.post("/{action_id}/approve")
def approve_action(action_id: str, payload: dict, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx
    token = (payload or {}).get("confirmation_token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing confirmation_token")

    a: PendingAction | None = (
        db.query(PendingAction)
        .filter(PendingAction.id == action_id, PendingAction.tenant_id == tenant_id)
        .one_or_none()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Action not found")
    if a.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Action not pending (status={a.status})")

    expected = a.confirmation_token_hash
    if not expected or _hash_token(token) != expected:
        raise HTTPException(status_code=403, detail="Invalid confirmation_token")

    a.status = "APPROVED"
    a.user_id = a.user_id or user_id
    a.decided_at = now_utc()
    db.commit()

    return {"id": a.id, "status": a.status}


@router.post("/{action_id}/reject")
def reject_action(action_id: str, payload: dict, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx

    a: PendingAction | None = (
        db.query(PendingAction)
        .filter(PendingAction.id == action_id, PendingAction.tenant_id == tenant_id)
        .one_or_none()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Action not found")
    if a.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Action not pending (status={a.status})")

    a.status = "REJECTED"
    a.user_id = a.user_id or user_id
    a.decided_at = now_utc()
    db.commit()

    return {"id": a.id, "status": a.status}
