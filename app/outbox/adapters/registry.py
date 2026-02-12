from __future__ import annotations

from app.outbox.adapters.base import SenderAdapter
from app.outbox.adapters.github_issue import GitHubIssueAdapter


def get_adapter(kind: str) -> SenderAdapter:
    if kind == "github_issue":
        return GitHubIssueAdapter()
    raise ValueError(f"No adapter for kind={kind}")
