from __future__ import annotations

from datetime import datetime, timedelta, timezone


def mock_grants() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "grant_id": "G-001",
            "title": "AI for Materials Science (Early Career)",
            "amount_usd": 250000,
            "deadline": (now + timedelta(days=21)).isoformat(),
            "keywords": ["AI", "materials", "simulation", "PhD"],
        },
        {
            "grant_id": "G-002",
            "title": "Open Science Reproducibility Microgrants",
            "amount_usd": 15000,
            "deadline": (now + timedelta(days=7)).isoformat(),
            "keywords": ["open science", "reproducibility", "tooling"],
        },
        {
            "grant_id": "G-003",
            "title": "Healthcare AI Pilot Program",
            "amount_usd": 120000,
            "deadline": (now + timedelta(days=45)).isoformat(),
            "keywords": ["health", "AI", "clinical", "pilot"],
        },
    ]
