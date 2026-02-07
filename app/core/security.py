from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import settings


def require_admin_token(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    if settings.AUTH_DISABLED:
        return
    if not x_admin_token or x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
