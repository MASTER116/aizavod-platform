"""Celery application configuration with beat schedule."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from backend.config import get_celery_config


def create_celery_app() -> Celery:
    cfg = get_celery_config()

    app = Celery(
        "aizavod",
        broker=cfg.broker_url,
        backend=cfg.result_backend,
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_hijack_root_logger=False,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )

    # Beat schedule — mirrors APScheduler jobs
    app.conf.beat_schedule = {
        "publish-scheduled-posts": {
            "task": "services.tasks.publish_scheduled_posts",
            "schedule": 300.0,  # every 5 minutes
        },
        "daily-content-generation": {
            "task": "services.tasks.daily_content_generation",
            "schedule": crontab(hour=2, minute=0),
        },
        "collect-analytics": {
            "task": "services.tasks.collect_analytics",
            "schedule": 14400.0,  # every 4 hours
        },
        "process-comments": {
            "task": "services.tasks.process_comments",
            "schedule": 1800.0,  # every 30 minutes
        },
        "daily-metrics-snapshot": {
            "task": "services.tasks.daily_metrics_snapshot",
            "schedule": crontab(hour=23, minute=55),
        },
        "weekly-strategy-review": {
            "task": "services.tasks.weekly_strategy_review",
            "schedule": crontab(hour=20, day_of_week="sun"),
        },
    }

    app.autodiscover_tasks(["services"])

    return app


celery_app = create_celery_app()
