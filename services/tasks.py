"""Celery tasks — wrapping scheduler job logic for distributed execution."""
from __future__ import annotations

import asyncio
import logging

from services.celery_app import celery_app

logger = logging.getLogger("aizavod.tasks")


def _run_async(coro):
    """Run an async coroutine in a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="services.tasks.publish_scheduled_posts")
def publish_scheduled_posts():
    """Celery task: publish scheduled posts."""
    from services.scheduler import _publish_scheduled_posts
    _run_async(_publish_scheduled_posts())
    logger.info("Celery: publish_scheduled_posts completed")


@celery_app.task(name="services.tasks.daily_content_generation")
def daily_content_generation():
    """Celery task: generate daily content."""
    from services.scheduler import _daily_content_generation
    _run_async(_daily_content_generation())
    logger.info("Celery: daily_content_generation completed")


@celery_app.task(name="services.tasks.collect_analytics")
def collect_analytics():
    """Celery task: collect analytics from all platforms."""
    from services.scheduler import _collect_analytics
    _run_async(_collect_analytics())
    logger.info("Celery: collect_analytics completed")


@celery_app.task(name="services.tasks.process_comments")
def process_comments():
    """Celery task: process and reply to comments."""
    from services.scheduler import _process_comments
    _run_async(_process_comments())
    logger.info("Celery: process_comments completed")


@celery_app.task(name="services.tasks.daily_metrics_snapshot")
def daily_metrics_snapshot():
    """Celery task: save daily metrics snapshot."""
    from services.scheduler import _daily_metrics_snapshot
    _run_async(_daily_metrics_snapshot())
    logger.info("Celery: daily_metrics_snapshot completed")


@celery_app.task(name="services.tasks.weekly_strategy_review")
def weekly_strategy_review():
    """Celery task: weekly strategy review."""
    from services.scheduler import _weekly_strategy_review
    _run_async(_weekly_strategy_review())
    logger.info("Celery: weekly_strategy_review completed")
