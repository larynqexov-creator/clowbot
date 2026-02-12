from __future__ import annotations

from collections.abc import Callable

SkillFn = Callable[..., dict]

SKILLS: dict[str, SkillFn] = {}

# Minimal binding (can be expanded)
TASKTYPE_TO_SKILL: dict[str, str] = {
    "ARTICLE": "submit_article_package",
    "SALES_OUTREACH": "sales_outreach_sequence",
}


def register(name: str):
    def _wrap(fn: SkillFn) -> SkillFn:
        SKILLS[name] = fn
        return fn

    return _wrap
