from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.tables import Tenant, User, AuditLog
from app.util.time import now_utc


def new_uuid() -> str:
    return str(uuid.uuid4())


def seed() -> None:
    db: Session = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.name == "seed-tenant").one_or_none()
        if not tenant:
            tenant = Tenant(id=new_uuid(), name="seed-tenant", created_at=now_utc())
            db.add(tenant)
            db.commit()

        user = db.query(User).filter(User.id == "seed-user", User.tenant_id == tenant.id).one_or_none()
        if not user:
            user = User(
                id="seed-user",
                tenant_id=tenant.id,
                email=None,
                display_name="Seed User",
                role="admin",
                api_key_hash=None,
                created_at=now_utc(),
            )
            db.add(user)
            db.commit()

        db.add(
            AuditLog(
                id=new_uuid(),
                tenant_id=tenant.id,
                user_id=user.id,
                event_type="SEED_DONE",
                severity="INFO",
                message="Seed completed",
                context={},
                created_at=now_utc(),
            )
        )
        db.commit()
        print(tenant.id)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
