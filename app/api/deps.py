from __future__ import annotations

from fastapi import Header, HTTPException


def get_ctx(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id")
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id")
    return x_tenant_id, x_user_id
