"""Content scheduler — orchestrates the autonomous content pipeline.

Anti-ban strategy:
- Warm-up phase (first 14 days): reduced posting, no engagement automation
- Posting times optimized for RU (MSK) + EU (CET) audiences
- Random jitter ±15 min on all jobs to avoid detection patterns
- Rest period 01:00-07:00 MSK (22:00-04:00 UTC) — no actions
- IG: max 1 Reel/day (2 parts = 1 master split), 3 Stories/day
- TikTok: 1 video/day (lenient, no strict limits)
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("aizavod.scheduler")


def _get_account_age_days() -> int:
    """Return how many days since the first post was published.

    Used for warm-up logic — new accounts get reduced automation.
    """
    try:
        from backend.database import SessionLocal
        from backend.models import Post, PostStatus
        db = SessionLocal()
        try:
            first_post = (
                db.query(Post)
                .filter(Post.status == PostStatus.PUBLISHED)
                .filter(Post.published_at.isnot(None))
                .order_by(Post.published_at.asc())
                .first()
            )
            if first_post and first_post.published_at:
                return (datetime.utcnow() - first_post.published_at).days
            return 0
        finally:
            db.close()
    except Exception:
        return 0


def _is_rest_period() -> bool:
    """Check if we're in the rest period (22:00-04:00 UTC = 01:00-07:00 MSK).

    No automated actions during this window to appear human.
    """
    hour = datetime.utcnow().hour
    return hour >= 22 or hour < 4

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler() -> None:
    """Configure and start all scheduled jobs."""
    scheduler = get_scheduler()

    # Publish scheduled posts (every 5 minutes)
    scheduler.add_job(
        _publish_scheduled_posts,
        "interval",
        minutes=5,
        id="publish_scheduled",
        replace_existing=True,
    )

    # Generate content batch (daily at 2:00 AM)
    scheduler.add_job(
        _daily_content_generation,
        "cron",
        hour=2,
        minute=0,
        id="daily_generation",
        replace_existing=True,
    )

    # Collect analytics (every 4 hours)
    scheduler.add_job(
        _collect_analytics,
        "interval",
        hours=4,
        id="collect_analytics",
        replace_existing=True,
    )

    # Process comments (every 30 minutes)
    scheduler.add_job(
        _process_comments,
        "interval",
        minutes=30,
        id="process_comments",
        replace_existing=True,
    )

    # Daily metrics snapshot (23:55)
    scheduler.add_job(
        _daily_metrics_snapshot,
        "cron",
        hour=23,
        minute=55,
        id="daily_metrics",
        replace_existing=True,
    )

    # Weekly strategy review (Sunday 20:00)
    scheduler.add_job(
        _weekly_strategy_review,
        "cron",
        day_of_week="sun",
        hour=20,
        id="weekly_review",
        replace_existing=True,
    )

    # ─── Agent v2 Jobs ────────────────────────────────────────────────────

    # Agent orchestrator cycle (every 30 min — enough for decision-making)
    scheduler.add_job(
        _agent_cycle,
        "interval",
        minutes=30,
        id="agent_cycle",
        replace_existing=True,
    )

    # Process DMs — read + categorize + notify (every 45 min — safe API rate)
    scheduler.add_job(
        _process_dms,
        "interval",
        minutes=45,
        id="process_dms",
        replace_existing=True,
    )

    # Post-publish engagement: reply to comments (every 90 min — safe for IG)
    scheduler.add_job(
        _post_engagement,
        "interval",
        minutes=90,
        id="post_engagement",
        replace_existing=True,
    )

    # Niche engagement: like/comment in hashtags (3 times/day — safe spread)
    for hour in [10, 15, 19]:
        scheduler.add_job(
            _niche_engagement,
            "cron",
            hour=hour,
            minute=random.randint(0, 30),  # random offset to avoid patterns
            id=f"niche_engagement_{hour}",
            replace_existing=True,
        )

    # Analyze competitors (daily 4:00)
    scheduler.add_job(
        _analyze_competitors,
        "cron",
        hour=4,
        minute=0,
        id="analyze_competitors",
        replace_existing=True,
    )

    # Analyze audience (daily 3:00)
    scheduler.add_job(
        _analyze_audience,
        "cron",
        hour=3,
        minute=0,
        id="analyze_audience",
        replace_existing=True,
    )

    # Viral pattern analysis (Mon + Thu 5:00)
    scheduler.add_job(
        _viral_analysis,
        "cron",
        day_of_week="mon,thu",
        hour=5,
        minute=0,
        id="viral_analysis",
        replace_existing=True,
    )

    # Story generation (3 times per day — RU+EU timezone coverage)
    # 08:00 UTC = 11:00 MSK / 09:00 CET (morning engagement)
    # 13:00 UTC = 16:00 MSK / 14:00 CET (afternoon)
    # 17:00 UTC = 20:00 MSK / 18:00 CET (evening prime time)
    for hour in [8, 13, 17]:
        scheduler.add_job(
            _story_generation,
            "cron",
            hour=hour,
            minute=random.randint(0, 20),  # random offset to avoid patterns
            id=f"story_generation_{hour}",
            replace_existing=True,
        )

    # Hashtag performance tracking (daily 22:00)
    scheduler.add_job(
        _hashtag_tracking,
        "cron",
        hour=22,
        minute=0,
        id="hashtag_tracking",
        replace_existing=True,
    )

    # ─── v3 Jobs ───────────────────────────────────────────────────────────

    # Trend analysis — TikTok + IG (every 4 hours)
    scheduler.add_job(
        _trend_analysis,
        "interval",
        hours=4,
        id="trend_analysis",
        replace_existing=True,
    )

    # Generate media for DRAFT posts → SCHEDULED (every 3 hours)
    scheduler.add_job(
        _generate_media_for_drafts,
        "interval",
        hours=3,
        id="generate_media_drafts",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# ─── Job implementations ───────────────────────────────────────────────────


async def _publish_scheduled_posts() -> None:
    """Check for posts scheduled for now and publish them.

    Respects rest period (22:00-04:00 UTC) — defers publication until morning.
    """
    if _is_rest_period():
        return

    from backend.database import SessionLocal
    from backend.models import Post, PostStatus, SystemSettings, GenerationLog, Platform
    from services.publisher import get_publisher_registry

    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings or not settings.auto_publish:
            return

        now = datetime.utcnow()
        posts = (
            db.query(Post)
            .filter(Post.status == PostStatus.SCHEDULED)
            .filter(Post.scheduled_at <= now)
            .all()
        )

        if not posts:
            return

        registry = get_publisher_registry()
        _ensure_publishers_registered(registry, settings)

        for post in posts:
            try:
                post.status = PostStatus.PUBLISHING
                db.commit()

                if not registry.has(post.platform):
                    logger.warning("No publisher for platform %s, skipping post %d", post.platform.value, post.id)
                    post.status = PostStatus.FAILED
                    db.commit()
                    continue

                publisher = registry.get(post.platform)

                # Build caption
                caption_parts = []
                if post.caption_ru:
                    caption_parts.append(post.caption_ru)
                if post.caption_en:
                    caption_parts.append("")
                    caption_parts.append(post.caption_en)
                if post.hashtags:
                    caption_parts.append("")
                    caption_parts.append(post.hashtags)
                caption = "\n".join(caption_parts)

                if post.video_path and post.content_type.value == "reel":
                    # Build audio kwargs for platform-specific sound
                    audio_kwargs = {}
                    if post.platform == Platform.INSTAGRAM and getattr(post, "ig_sound_id", None):
                        audio_kwargs["audio_id"] = post.ig_sound_id
                    elif post.platform == Platform.TIKTOK and getattr(post, "tiktok_sound_id", None):
                        audio_kwargs["sound_id"] = post.tiktok_sound_id

                    media_id = await publisher.publish_video(
                        post.video_path, caption, post.thumbnail_path, **audio_kwargs
                    )
                elif post.image_path:
                    media_id = await publisher.publish_photo(post.image_path, caption)
                else:
                    logger.warning("Post %d has no media to publish", post.id)
                    post.status = PostStatus.FAILED
                    db.commit()
                    continue

                # Store platform-specific ID
                if post.platform == Platform.INSTAGRAM:
                    post.instagram_media_id = media_id
                elif post.platform == Platform.TELEGRAM:
                    post.telegram_message_id = media_id
                elif post.platform == Platform.VK:
                    post.vk_post_id = media_id
                elif post.platform == Platform.TIKTOK:
                    post.tiktok_video_id = media_id

                post.published_at = datetime.utcnow()
                post.status = PostStatus.PUBLISHED

                db.add(GenerationLog(
                    action="publish",
                    entity_type="post",
                    entity_id=post.id,
                    status="success",
                    details=f"platform={post.platform.value}",
                ))

                logger.info("Published post %d to %s: id=%s", post.id, post.platform.value, media_id)

            except Exception as e:
                logger.error("Failed to publish post %d: %s", post.id, e)
                post.status = PostStatus.FAILED
                db.add(GenerationLog(
                    action="publish",
                    entity_type="post",
                    entity_id=post.id,
                    status="failure",
                    details=str(e),
                ))

            db.commit()

    finally:
        db.close()


def _ensure_publishers_registered(registry, settings) -> None:
    """Lazily register publishers on first use."""
    from backend.models import Platform

    if not registry.has(Platform.INSTAGRAM):
        try:
            from services.instagram_publisher import InstagramPublisher
            from services.instagram_client import get_instagram_client

            client = get_instagram_client()
            if settings.instagram_session_data:
                client.login(session_data=settings.instagram_session_data)
            else:
                client.login()
                settings.instagram_session_data = client.get_session_data()

            registry.register(InstagramPublisher())
        except Exception as e:
            logger.warning("Failed to register Instagram publisher: %s", e)

    if not registry.has(Platform.TELEGRAM):
        try:
            from backend.config import get_telegram_channel_config
            cfg = get_telegram_channel_config()
            if cfg.channel_id or cfg.channel_username:
                from services.telegram_publisher import TelegramPublisher
                registry.register(TelegramPublisher())
        except Exception as e:
            logger.warning("Failed to register Telegram publisher: %s", e)

    if not registry.has(Platform.TIKTOK):
        try:
            import os
            if os.getenv("TIKTOK_ACCESS_TOKEN"):
                from services.tiktok_publisher import TikTokPublisher
                registry.register(TikTokPublisher())
        except Exception as e:
            logger.warning("Failed to register TikTok publisher: %s", e)


async def _daily_content_generation() -> None:
    """Generate content for the upcoming day.

    Warm-up schedule (anti-ban):
    - Days 0-3:   1 photo/day only (no reels) — establish account
    - Days 4-7:   1 reel/day + 1 story — gentle start
    - Days 8-14:  1 reel/day + 2 stories — building trust
    - Days 15+:   full schedule (1 reel/day + 3 stories)
    """
    from backend.database import SessionLocal
    from backend.models import Post, PostStatus, SystemSettings
    from services.character_manager import get_active_character

    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings or not settings.auto_generate:
            return

        character = get_active_character(db)
        if not character:
            logger.warning("No active character for auto-generation")
            return

        # Warm-up: adjust posts_per_day based on account age
        age = _get_account_age_days()
        effective_posts = settings.posts_per_day
        if age < 4:
            effective_posts = 1  # photos only, no reels
            logger.info("Warm-up phase (day %d): 1 photo only", age)
        elif age < 8:
            effective_posts = 1
            logger.info("Warm-up phase (day %d): 1 reel + 1 story", age)
        elif age < 15:
            effective_posts = 1
            logger.info("Warm-up phase (day %d): 1 reel + 2 stories", age)
        else:
            logger.info("Full schedule (day %d): %d posts/day", age, effective_posts)

        # Check if content for tomorrow already exists
        tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
        existing = (
            db.query(Post)
            .filter(Post.scheduled_at >= datetime.combine(tomorrow, datetime.min.time()))
            .filter(Post.scheduled_at < datetime.combine(tomorrow + timedelta(days=1), datetime.min.time()))
            .count()
        )

        if existing >= effective_posts:
            logger.info("Content for %s already generated (%d posts)", tomorrow, existing)
            return

        # Adjust stories for warm-up phase
        effective_stories = settings.stories_per_day
        effective_reels = settings.reels_per_week
        if age < 4:
            effective_stories = 0
            effective_reels = 0  # photos only during first 3 days
        elif age < 8:
            effective_stories = 1
            effective_reels = 7
        elif age < 15:
            effective_stories = 2
            effective_reels = 7

        from services.content_strategy import generate_weekly_calendar

        calendar = await generate_weekly_calendar(
            character=character,
            days=1,
            posts_per_day=effective_posts,
            stories_per_day=effective_stories,
            reels_per_week=effective_reels,
        )

        if not calendar:
            return

        from backend.models import ContentCategory, ContentType

        for day in calendar:
            for i, post_data in enumerate(day.get("posts", [])):
                cat = post_data.get("category", "workout")
                try:
                    category = ContentCategory(cat)
                except ValueError:
                    category = ContentCategory.WORKOUT

                ctype = post_data.get("content_type", "photo")
                try:
                    content_type = ContentType(ctype)
                except ValueError:
                    content_type = ContentType.PHOTO

                # Schedule at specified time
                time_str = post_data.get("time", f"{9 + i * 4}:00")
                hour, minute = map(int, time_str.split(":"))
                scheduled = datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute))

                post = Post(
                    character_id=character.id,
                    content_type=content_type,
                    category=category,
                    status=PostStatus.DRAFT,
                    image_prompt_used=post_data.get("scene", ""),
                    caption_ru=post_data.get("description_ru", ""),
                    caption_en=post_data.get("description_en", ""),
                    scheduled_at=scheduled,
                )
                db.add(post)

        db.commit()
        logger.info("Generated daily content plan for %s", tomorrow)

    finally:
        db.close()


async def _collect_analytics() -> None:
    """Fetch metrics for recently published posts from all platforms."""
    from backend.database import SessionLocal
    from backend.models import Post, PostStatus, PostAnalytics, Platform
    from services.publisher import get_publisher_registry

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        posts = (
            db.query(Post)
            .filter(Post.status == PostStatus.PUBLISHED)
            .filter(Post.published_at >= cutoff)
            .all()
        )

        if not posts:
            return

        registry = get_publisher_registry()

        for post in posts:
            # Determine the platform-specific post ID
            platform_post_id = None
            if post.platform == Platform.INSTAGRAM:
                platform_post_id = post.instagram_media_id
            elif post.platform == Platform.TELEGRAM:
                platform_post_id = post.telegram_message_id
            elif post.platform == Platform.VK:
                platform_post_id = post.vk_post_id
            elif post.platform == Platform.TIKTOK:
                platform_post_id = getattr(post, "tiktok_video_id", None)

            if not platform_post_id:
                continue

            if not registry.has(post.platform):
                continue

            try:
                publisher = registry.get(post.platform)
                insights = await publisher.get_post_analytics(platform_post_id)
                if not insights:
                    continue

                analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post.id).first()
                if not analytics:
                    analytics = PostAnalytics(post_id=post.id)
                    db.add(analytics)

                analytics.likes = insights.get("likes", 0)
                analytics.comments_count = insights.get("comments", 0)
                analytics.shares = insights.get("shares", 0)
                analytics.saves = insights.get("saves", 0)
                analytics.reach = insights.get("reach", 0)
                analytics.impressions = insights.get("impressions", 0)
                analytics.video_views = insights.get("video_views", 0)

                total_engagement = analytics.likes + analytics.comments_count + analytics.saves + analytics.shares
                if analytics.reach > 0:
                    analytics.engagement_rate = (total_engagement / analytics.reach) * 100

                analytics.last_fetched_at = datetime.utcnow()

            except Exception as e:
                logger.warning("Failed to fetch analytics for post %d (%s): %s", post.id, post.platform.value, e)

        db.commit()
        logger.info("Updated analytics for %d posts", len(posts))

    finally:
        db.close()


async def _process_comments() -> None:
    """Fetch and auto-reply to new comments from all platforms."""
    from backend.database import SessionLocal
    from backend.models import Post, PostStatus, Comment, SystemSettings, Platform
    from services.character_manager import get_active_character
    from services.publisher import get_publisher_registry

    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings or not settings.auto_reply_comments:
            return

        character = get_active_character(db)
        if not character:
            return

        registry = get_publisher_registry()
        cutoff = datetime.utcnow() - timedelta(days=3)
        posts = (
            db.query(Post)
            .filter(Post.status == PostStatus.PUBLISHED)
            .filter(Post.published_at >= cutoff)
            .all()
        )

        from services.caption_generator import generate_comment_reply

        for post in posts:
            # Get the platform-specific post ID
            platform_post_id = None
            if post.platform == Platform.INSTAGRAM:
                platform_post_id = post.instagram_media_id
            elif post.platform == Platform.VK:
                platform_post_id = post.vk_post_id

            if not platform_post_id or not registry.has(post.platform):
                continue

            publisher = registry.get(post.platform)

            try:
                raw_comments = await publisher.get_comments(platform_post_id, limit=20)

                for raw in raw_comments:
                    existing = db.query(Comment).filter(
                        Comment.platform_comment_id == raw["id"]
                    ).first()
                    if existing:
                        continue

                    comment = Comment(
                        post_id=post.id,
                        platform=post.platform,
                        platform_comment_id=raw["id"],
                        username=raw["username"],
                        text=raw["text"],
                    )
                    db.add(comment)
                    db.flush()

                    reply = await generate_comment_reply(
                        character=character,
                        username=raw["username"],
                        comment_text=raw["text"],
                        post_description=post.caption_ru or post.caption_en or "",
                    )
                    comment.reply_text = reply

                    await publisher.reply_to_comment(
                        platform_post_id, raw["id"], reply
                    )
                    comment.reply_sent = True
                    comment.reply_sent_at = datetime.utcnow()

            except Exception as e:
                logger.warning("Error processing comments for post %d (%s): %s", post.id, post.platform.value, e)

        db.commit()

    finally:
        db.close()


async def _daily_metrics_snapshot() -> None:
    """Save daily follower/engagement snapshot for all active platforms."""
    from backend.database import SessionLocal
    from backend.models import DailyMetrics, Post, PostStatus, Platform
    from services.publisher import get_publisher_registry
    from services.character_manager import get_active_character

    db = SessionLocal()
    try:
        today = date.today()
        registry = get_publisher_registry()
        character = get_active_character(db)

        for platform in registry.platforms():
            existing = (
                db.query(DailyMetrics)
                .filter(DailyMetrics.date == today)
                .filter(DailyMetrics.platform == platform)
                .first()
            )
            if existing:
                continue

            followers = 0
            following = 0
            try:
                publisher = registry.get(platform)
                info = await publisher.get_account_info()
                followers = info.get("followers", 0)
                following = info.get("following", 0)
            except Exception as e:
                logger.warning("Failed to get account info for %s: %s", platform.value, e)

            today_start = datetime.combine(today, datetime.min.time())
            today_posts = (
                db.query(Post)
                .filter(Post.status == PostStatus.PUBLISHED)
                .filter(Post.platform == platform)
                .filter(Post.published_at >= today_start)
                .count()
            )

            metrics = DailyMetrics(
                date=today,
                platform=platform,
                character_id=character.id if character else None,
                followers_count=followers,
                following_count=following,
                posts_count=today_posts,
            )
            db.add(metrics)

        db.commit()
        logger.info("Daily metrics snapshot saved for %d platforms", len(registry.platforms()))

    finally:
        db.close()


async def _weekly_strategy_review() -> None:
    """Analyze weekly performance and adjust content mix."""
    from backend.database import SessionLocal
    from backend.models import SystemSettings
    from services.character_manager import get_active_character
    from services.content_strategy import analyze_weekly_performance

    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings or not settings.auto_generate:
            return

        character = get_active_character(db)
        if not character:
            return

        result = await analyze_weekly_performance()

        if result.get("content_mix"):
            import json
            settings.content_mix = json.dumps(result["content_mix"])
            db.commit()
            logger.info("Updated content mix: %s", result["content_mix"])

    finally:
        db.close()


# ─── Agent v2 Job Implementations ─────────────────────────────────────────


async def _agent_cycle() -> None:
    """Run agent orchestrator cycle every 15 minutes."""
    from services.agent_orchestrator import run_cycle

    try:
        results = await run_cycle()
        if results:
            logger.info("Agent cycle completed: %d actions", len(results))
    except Exception as e:
        logger.error("Agent cycle failed: %s", e)


async def _process_dms() -> None:
    """Read, categorize, and notify about new DMs."""
    from backend.database import SessionLocal
    from services.character_manager import get_active_character
    from services.dm_manager import process_dm_inbox

    db = SessionLocal()
    try:
        character = get_active_character(db)
        if not character:
            return

        result = await process_dm_inbox(character)
        if result.get("processed", 0) > 0:
            logger.info("DM processing: %s", result)
    except Exception as e:
        logger.error("DM processing failed: %s", e)
    finally:
        db.close()


async def _post_engagement() -> None:
    """Reply to comments on recent posts (safe intervals).

    Skipped during rest period and first 7 days (warm-up).
    """
    if _is_rest_period():
        return
    if _get_account_age_days() < 7:
        logger.info("Warm-up: skipping post engagement (account < 7 days)")
        return

    from backend.database import SessionLocal
    from services.character_manager import get_active_character
    from services.ig_algorithm import execute_post_engagement_loop

    db = SessionLocal()
    try:
        character = get_active_character(db)
        if not character:
            return

        await execute_post_engagement_loop(character)
    except Exception as e:
        logger.error("Post engagement failed: %s", e)
    finally:
        db.close()


async def _niche_engagement() -> None:
    """Like/comment on niche hashtag posts (3x/day, safe limits).

    Skipped during rest period and first 14 days (warm-up).
    Niche engagement is the riskiest action for new accounts.
    """
    if _is_rest_period():
        return
    if _get_account_age_days() < 14:
        logger.info("Warm-up: skipping niche engagement (account < 14 days)")
        return

    from backend.database import SessionLocal
    from services.character_manager import get_active_character
    from services.ig_algorithm import execute_engagement_loop

    db = SessionLocal()
    try:
        character = get_active_character(db)
        if not character:
            return

        await execute_engagement_loop(character)
    except Exception as e:
        logger.error("Niche engagement failed: %s", e)
    finally:
        db.close()


async def _analyze_competitors() -> None:
    """Daily competitor analysis."""
    from backend.database import SessionLocal
    from backend.models import SystemSettings
    from services.character_manager import get_active_character
    from services.audience_analyzer import analyze_competitors

    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings or not settings.auto_analyze_competitors:
            return

        character = get_active_character(db)
        if not character:
            return

        result = await analyze_competitors(character)
        logger.info("Competitor analysis done: %s", result)
    except Exception as e:
        logger.error("Competitor analysis failed: %s", e)
    finally:
        db.close()


async def _analyze_audience() -> None:
    """Daily audience analysis."""
    from backend.database import SessionLocal
    from services.character_manager import get_active_character
    from services.audience_analyzer import analyze_audience

    db = SessionLocal()
    try:
        character = get_active_character(db)
        if not character:
            return

        result = await analyze_audience(character)
        logger.info("Audience analysis done: insight_id=%s", result.get("id"))
    except Exception as e:
        logger.error("Audience analysis failed: %s", e)
    finally:
        db.close()


async def _viral_analysis() -> None:
    """Viral pattern analysis (Mon + Thu)."""
    from backend.database import SessionLocal
    from services.character_manager import get_active_character
    from services.viral_engine import analyze_viral_patterns

    db = SessionLocal()
    try:
        character = get_active_character(db)
        if not character:
            return

        result = await analyze_viral_patterns(character)
        logger.info("Viral analysis done: %d patterns", result.get("count", 0))
    except Exception as e:
        logger.error("Viral analysis failed: %s", e)
    finally:
        db.close()


async def _story_generation() -> None:
    """Generate and publish a Story.

    Respects warm-up: no stories first 3 days, 1/day days 4-7, 2/day days 8-14.
    """
    if _is_rest_period():
        return

    age = _get_account_age_days()
    if age < 4:
        return  # no stories during first 3 days

    from backend.database import SessionLocal
    from backend.models import Post, PostStatus, ContentType, ContentCategory, SystemSettings
    from services.character_manager import get_active_character

    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings or not settings.auto_generate:
            return

        # Check daily story limit for warm-up phase
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stories_today = (
            db.query(Post)
            .filter(Post.content_type == ContentType.STORY)
            .filter(Post.created_at >= today_start)
            .count()
        )
        max_stories = settings.stories_per_day
        if age < 8:
            max_stories = 1
        elif age < 15:
            max_stories = 2

        if stories_today >= max_stories:
            return

        character = get_active_character(db)
        if not character:
            return

        # Create a story draft
        post = Post(
            character_id=character.id,
            content_type=ContentType.STORY,
            category=ContentCategory.LIFESTYLE,
            status=PostStatus.DRAFT,
            image_prompt_used="Daily story — behind the scenes / lifestyle moment",
        )
        db.add(post)
        db.commit()

        logger.info("Story draft created: post_id=%d", post.id)
    except Exception as e:
        logger.error("Story generation failed: %s", e)
    finally:
        db.close()


async def _hashtag_tracking() -> None:
    """Track hashtag performance nightly."""
    from services.hashtag_optimizer import track_hashtag_performance

    try:
        result = await track_hashtag_performance()
        logger.info(
            "Hashtag tracking: %d tags tracked, top=%s",
            result.get("total_tracked", 0),
            list(result.get("top_performers", {}).keys())[:3],
        )
    except Exception as e:
        logger.error("Hashtag tracking failed: %s", e)


# ─── v3 Job Implementations ─────────────────────────────────────────────


async def _trend_analysis() -> None:
    """Fetch and analyze TikTok + IG trends every 4 hours."""
    import os
    if not os.getenv("TREND_ANALYSIS_ENABLED", "").lower() in ("true", "1", "yes"):
        return

    try:
        from services.trend_analyzer import fetch_and_analyze_trends
        snapshot = await fetch_and_analyze_trends(niche="fitness")
        logger.info("Trend analysis completed: snapshot_id=%s", snapshot.id)
    except Exception as e:
        logger.error("Trend analysis failed: %s", e)


async def _generate_media_for_drafts() -> None:
    """Generate media (65s video) for DRAFT reel posts, then set SCHEDULED.

    This is the critical link: DRAFT → generate media → SCHEDULED.
    Budget gate: checks daily_post_budget_usd vs spent today.
    Creates companion IG posts (split from TikTok master).
    """
    import os
    if not os.getenv("LONG_VIDEO_ENABLED", "").lower() in ("true", "1", "yes"):
        return

    from backend.database import SessionLocal
    from backend.models import (
        Post, PostStatus, ContentType, Platform, SystemSettings, GenerationLog,
    )
    from services.character_manager import get_active_character

    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings or not settings.auto_generate:
            return

        character = get_active_character(db)
        if not character:
            return

        # Budget gate
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_logs = (
            db.query(GenerationLog)
            .filter(GenerationLog.created_at >= today_start)
            .filter(GenerationLog.action == "generate")
            .all()
        )
        spent_today = 0.0
        for log in today_logs:
            try:
                import json as _json
                details = _json.loads(log.details or "{}")
                spent_today += details.get("cost_usd", 0.0)
            except Exception:
                pass

        budget_remaining = settings.daily_post_budget_usd - spent_today
        if budget_remaining < 5.0:
            logger.info("Budget exhausted ($%.2f remaining), skipping media generation", budget_remaining)
            return

        # Find DRAFT reel posts
        drafts = (
            db.query(Post)
            .filter(Post.character_id == character.id)
            .filter(Post.status == PostStatus.DRAFT)
            .filter(Post.content_type == ContentType.REEL)
            .order_by(Post.scheduled_at.asc())
            .limit(2)
            .all()
        )

        if not drafts:
            return

        from services.viral_engine import generate_viral_reel_concept
        from services.long_video_pipeline import generate_long_video
        from services.trend_analyzer import get_latest_trend_summary, get_trending_camera_angles
        from services.caption_generator import generate_caption
        from services.hashtag_optimizer import get_optimized_hashtags

        trend_summary = await get_latest_trend_summary()
        camera_angles = await get_trending_camera_angles()
        trend_context = {
            "trend_summary": trend_summary,
            "trending_formats": [{"camera_angle": a.get("camera_angle", "medium shot"), "format": a.get("format", "")} for a in camera_angles],
        }

        for draft in drafts:
            if budget_remaining < 5.0:
                break

            try:
                draft.status = PostStatus.GENERATING
                db.commit()

                # Generate concept
                concept = await generate_viral_reel_concept(
                    character=character,
                    category=draft.category.value if draft.category else "workout",
                    trends=trend_summary,
                )

                # Generate 65s video
                result = await generate_long_video(
                    character=character,
                    concept=concept,
                    trend_context=trend_context,
                )

                # Generate caption + hashtags
                caption = await generate_caption(
                    character=character,
                    scene_description=concept.get("scene_description", ""),
                    hook_text=concept.get("hook_text", ""),
                )
                hashtags = await get_optimized_hashtags(
                    category=draft.category.value if draft.category else "workout",
                    content_type="reel",
                )

                # Update TikTok draft post
                draft.video_path = result.tiktok_video_path
                draft.thumbnail_path = result.thumbnail_path
                draft.caption_ru = caption.get("caption_ru", "")
                draft.caption_en = caption.get("caption_en", "")
                draft.hashtags = hashtags
                draft.hook_text = concept.get("hook_text", "")
                draft.platform = Platform.TIKTOK
                draft.tiktok_sound_id = result.tiktok_sound_id
                draft.status = PostStatus.SCHEDULED
                if not draft.scheduled_at:
                    draft.scheduled_at = datetime.utcnow() + timedelta(hours=1)

                # Create 2 companion IG posts (split from TikTok master)
                ig_part1 = Post(
                    character_id=character.id,
                    content_type=ContentType.REEL,
                    category=draft.category,
                    platform=Platform.INSTAGRAM,
                    status=PostStatus.SCHEDULED,
                    video_path=result.ig_part1_path,
                    thumbnail_path=result.thumbnail_path,
                    caption_ru=draft.caption_ru,
                    caption_en=draft.caption_en,
                    hashtags=draft.hashtags,
                    hook_text=draft.hook_text,
                    ig_sound_id=result.ig_sound_id,
                    scheduled_at=draft.scheduled_at + timedelta(hours=1),
                )
                ig_part2 = Post(
                    character_id=character.id,
                    content_type=ContentType.REEL,
                    category=draft.category,
                    platform=Platform.INSTAGRAM,
                    status=PostStatus.SCHEDULED,
                    video_path=result.ig_part2_path,
                    thumbnail_path=result.thumbnail_path,
                    caption_ru=f"{draft.caption_ru}\n\nЧасть 2 ➡️",
                    caption_en=f"{draft.caption_en}\n\nPart 2 ➡️" if draft.caption_en else "",
                    hashtags=draft.hashtags,
                    hook_text="",
                    ig_sound_id=result.ig_sound_id,
                    scheduled_at=draft.scheduled_at + timedelta(hours=2),
                )
                db.add(ig_part1)
                db.add(ig_part2)

                # Log generation cost
                db.add(GenerationLog(
                    action="generate",
                    entity_type="long_video",
                    entity_id=draft.id,
                    status="success",
                    details=f'{{"cost_usd": {result.total_cost_usd:.2f}, "clips": {len(result.clip_paths)}}}',
                ))

                budget_remaining -= result.total_cost_usd

                logger.info(
                    "Media generated for draft %d: TT=%s, IG1=%s, IG2=%s, cost=$%.2f",
                    draft.id, result.tiktok_video_path, result.ig_part1_path,
                    result.ig_part2_path, result.total_cost_usd,
                )

            except Exception as e:
                logger.error("Failed to generate media for draft %d: %s", draft.id, e)
                draft.status = PostStatus.FAILED
                db.add(GenerationLog(
                    action="generate",
                    entity_type="long_video",
                    entity_id=draft.id,
                    status="failure",
                    details=str(e)[:500],
                ))

            db.commit()

    finally:
        db.close()
