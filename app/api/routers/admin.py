from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import require_admin_token
from app.models.tables import Tenant
from app.util.ids import new_uuid
from app.util.time import now_utc

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/tenants", dependencies=[Depends(require_admin_token)])
def create_tenant(payload: dict, db: Session = Depends(get_db)):
    # create-or-get by unique name (idempotent)
    name = (payload or {}).get("name")
    if not name:
        return {"detail": "Missing name"}

    existing: Tenant | None = db.query(Tenant).filter(Tenant.name == name).one_or_none()
    if existing:
        return {"id": existing.id, "name": existing.name}

    tenant = Tenant(id=new_uuid(), name=name, created_at=now_utc())
    db.add(tenant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Another request likely created it concurrently
        existing = db.query(Tenant).filter(Tenant.name == name).one_or_none()
        if existing:
            return {"id": existing.id, "name": existing.name}
        raise

    return {"id": tenant.id, "name": tenant.name}
