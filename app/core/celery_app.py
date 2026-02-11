from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery = Celery(
    "clowbot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.grant_tasks", "app.tasks.jarvis_tasks"],
)

celery.conf.update(
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    task_default_queue="default",
)
