from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.tables import Document
from app.schemas.outbox_v1 import Allowlist


@dataclass(frozen=True)
class AllowlistDoc:
    allowlist: Allowlist
    document_id: str | None


def load_policy_allowlist(db: Session, *, tenant_id: str) -> AllowlistDoc:
    """Load tenant-wide allowlist from documents.

    Stored as Document(domain='policy', doc_type='policy_allowlist').
    We store the allowlist structure under Document.meta['allowlist'].

    If missing, returns empty Allowlist.
    """

    doc: Document | None = (
        db.query(Document)
        .filter(Document.tenant_id == tenant_id, Document.domain == "policy", Document.doc_type == "policy_allowlist")
        .order_by(Document.created_at.desc())
        .first()
    )

    if not doc:
        return AllowlistDoc(allowlist=Allowlist(), document_id=None)

    meta = dict(doc.meta or {})
    raw = meta.get("allowlist") or {}
    try:
        allow = Allowlist.model_validate(raw)
    except Exception:
        # Fail closed: if malformed, treat as empty allowlist.
        allow = Allowlist()

    return AllowlistDoc(allowlist=allow, document_id=doc.id)


def merge_allowlists(*, base: Allowlist, extra: Allowlist) -> Allowlist:
    """Union allowlists (dedup, stable-ish ordering)."""

    def uniq(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return Allowlist(
        email_domains=uniq((base.email_domains or []) + (extra.email_domains or [])),
        emails=uniq((base.emails or []) + (extra.emails or [])),
        telegram_chats=uniq((base.telegram_chats or []) + (extra.telegram_chats or [])),
        github_repos=uniq((base.github_repos or []) + (extra.github_repos or [])),
    )
