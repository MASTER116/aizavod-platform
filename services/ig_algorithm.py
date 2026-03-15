"""IG Algorithm optimization — safe engagement within Instagram's limits.

SAFETY FIRST: All limits are set conservatively to avoid action blocks.
Instagram's limits (approximate, stricter for new/small accounts):
- Likes: 60-100/day, max 20/hour, 3-8 sec between actions
- Comments: 20-30/day, max 10/hour, 30-60 sec between actions
- DM reads: no hard limit but don't spam API
- Follows: 20-30/day, max 10/hour
- Total actions: ~200/day combined
- Story views: 100-200/day

Key anti-ban rules:
- Random delays between EVERY action (human-like)
- Never repeat the same comment text
- Warm up gradually (start with fewer actions, increase weekly)
- Rest periods: no actions between 01:00-06:00
- If action block detected → stop ALL actions for 12-24 hours
"""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta

from backend.database import SessionLocal
from backend.models import (
    Character,
    Comment,
    Post,
    PostAnalytics,
    PostStatus,
    Platform,
)

logger = logging.getLogger("aizavod.ig_algorithm")


# ─── Optimization Constants ──────────────────────────────────────────────

REEL_OPTIMIZATION = {
    "hook_window_sec": 3,
    "sweet_spot_min_sec": 15,
    "sweet_spot_max_sec": 30,
    "trending_audio": True,
    "text_overlay": True,
    "loop_ending": True,
    "cta_type": "save",
}

CAROUSEL_OPTIMIZATION = {
    "max_slides": 10,
    "optimal_slides": 7,
    "bold_first_slide": True,
    "save_worthy_content": True,
    "swipe_cta": True,
    "last_slide_cta": True,
}

# ─── Safe Engagement Limits (anti-ban) ────────────────────────────────────
# These are CONSERVATIVE. Instagram blocks at higher numbers,
# but we stay well below to avoid any risk.

ENGAGEMENT_LIMITS = {
    # Per session (one scheduler run)
    "likes_per_session": 5,         # max 5 likes per session
    "comments_per_session": 2,      # max 2 comments per session
    "comment_replies_per_session": 3,  # max 3 replies to own post comments

    # Daily caps (tracked in-memory, resets at midnight)
    "max_likes_per_day": 40,        # IG limit ~100, we stay at 40
    "max_comments_per_day": 15,     # IG limit ~30, we stay at 15
    "max_follows_per_day": 10,      # IG limit ~30, we stay at 10
    "max_total_actions_per_day": 80,  # all actions combined

    # Delays between actions (seconds) — randomized in this range
    "delay_between_likes": (8, 25),     # 8-25 sec between likes
    "delay_between_comments": (45, 120),  # 45-120 sec between comments
    "delay_between_replies": (30, 90),  # 30-90 sec between comment replies
    "delay_after_session": (300, 600),  # 5-10 min rest after session

    # Rest period — NO actions during night
    "rest_hour_start": 1,   # no actions from 01:00
    "rest_hour_end": 7,     # ...until 07:00
}

# Daily action counters (reset at midnight)
_daily_actions = {"likes": 0, "comments": 0, "follows": 0, "total": 0, "date": ""}

# Niche hashtags for engagement (rotate through these)
NICHE_HASHTAGS = [
    "fitnessgirl", "workoutmotivation", "gymgirl", "fitlife",
    "healthylifestyle", "fitnessmotivation", "gymmotivation",
    "fitfam", "girlswholift", "strongnotskinny",
]


def _reset_daily_if_needed() -> None:
    """Reset daily counters at midnight."""
    global _daily_actions
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if _daily_actions["date"] != today:
        _daily_actions = {"likes": 0, "comments": 0, "follows": 0, "total": 0, "date": today}


def _is_rest_period() -> bool:
    """Check if we're in the rest period (no actions)."""
    hour = datetime.utcnow().hour
    return ENGAGEMENT_LIMITS["rest_hour_start"] <= hour < ENGAGEMENT_LIMITS["rest_hour_end"]


def _can_like() -> bool:
    _reset_daily_if_needed()
    return (
        _daily_actions["likes"] < ENGAGEMENT_LIMITS["max_likes_per_day"]
        and _daily_actions["total"] < ENGAGEMENT_LIMITS["max_total_actions_per_day"]
        and not _is_rest_period()
    )


def _can_comment() -> bool:
    _reset_daily_if_needed()
    return (
        _daily_actions["comments"] < ENGAGEMENT_LIMITS["max_comments_per_day"]
        and _daily_actions["total"] < ENGAGEMENT_LIMITS["max_total_actions_per_day"]
        and not _is_rest_period()
    )


async def _safe_delay(delay_range: tuple[int, int]) -> None:
    """Human-like random delay with +-20% jitter."""
    base = random.uniform(delay_range[0], delay_range[1])
    jitter = base * random.uniform(-0.2, 0.2)
    await asyncio.sleep(base + jitter)


def get_optimal_posting_times(character: Character) -> list[str]:
    """Get optimal posting times based on real PostAnalytics data."""
    db = SessionLocal()
    try:
        month_ago = datetime.utcnow() - timedelta(days=30)
        posts = (
            db.query(Post)
            .filter(Post.character_id == character.id)
            .filter(Post.status == PostStatus.PUBLISHED)
            .filter(Post.published_at >= month_ago)
            .all()
        )

        hour_ers: dict[int, list[float]] = {}
        for p in posts:
            if not p.published_at:
                continue
            analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == p.id).first()
            if not analytics or not analytics.engagement_rate:
                continue
            hour = p.published_at.hour
            hour_ers.setdefault(hour, []).append(analytics.engagement_rate)

        if not hour_ers:
            return ["09:00", "12:00", "18:00", "21:00"]

        sorted_hours = sorted(
            hour_ers.items(),
            key=lambda x: sum(x[1]) / len(x[1]),
            reverse=True,
        )

        return [f"{h:02d}:00" for h, _ in sorted_hours[:4]]

    finally:
        db.close()


async def execute_post_engagement_loop(character: Character) -> dict:
    """Post-publish engagement loop for recent posts (SAFE mode).

    Replies to a LIMITED number of comments per session to stay within IG limits.
    Only processes posts published in the last 6 hours (wider window, fewer runs).
    """
    if _is_rest_period():
        return {"posts_engaged": 0, "reason": "rest_period"}

    _reset_daily_if_needed()

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=6)
        recent_posts = (
            db.query(Post)
            .filter(Post.character_id == character.id)
            .filter(Post.status == PostStatus.PUBLISHED)
            .filter(Post.platform == Platform.INSTAGRAM)
            .filter(Post.published_at >= cutoff)
            .filter(Post.instagram_media_id.isnot(None))
            .all()
        )

        if not recent_posts:
            return {"posts_engaged": 0}

        from services.instagram_client import get_instagram_client
        from services.caption_generator import generate_comment_reply

        ig = get_instagram_client()
        engaged = 0
        session_replies = 0
        max_replies = ENGAGEMENT_LIMITS["comment_replies_per_session"]

        for post in recent_posts:
            if session_replies >= max_replies:
                break

            try:
                # 1. Fetch comments (read-only, doesn't count as action)
                comments = await ig.get_comments(post.instagram_media_id, amount=10)

                for raw_comment in comments:
                    if session_replies >= max_replies or not _can_comment():
                        break

                    existing = (
                        db.query(Comment)
                        .filter(Comment.platform_comment_id == raw_comment["id"])
                        .first()
                    )
                    if existing and existing.reply_sent:
                        continue

                    if not existing:
                        existing = Comment(
                            post_id=post.id,
                            platform=Platform.INSTAGRAM,
                            platform_comment_id=raw_comment["id"],
                            username=raw_comment["username"],
                            text=raw_comment["text"],
                        )
                        db.add(existing)
                        db.flush()

                    # Generate and send reply with safe delay
                    reply = await generate_comment_reply(
                        character=character,
                        username=raw_comment["username"],
                        comment_text=raw_comment["text"],
                        post_description=post.caption_ru or post.caption_en or "",
                    )

                    await _safe_delay(ENGAGEMENT_LIMITS["delay_between_replies"])

                    await ig.reply_to_comment(
                        post.instagram_media_id, raw_comment["id"], reply
                    )
                    existing.reply_text = reply
                    existing.reply_sent = True
                    existing.reply_sent_at = datetime.utcnow()
                    session_replies += 1
                    _daily_actions["comments"] += 1
                    _daily_actions["total"] += 1

                engaged += 1
                db.commit()

            except Exception as e:
                if "action_block" in str(e).lower() or "challenge" in str(e).lower():
                    logger.error("ACTION BLOCK detected! Stopping all engagement for safety.")
                    break
                logger.warning("Engagement loop failed for post %d: %s", post.id, e)

        logger.info(
            "Engagement loop: engaged %d posts, %d replies (daily: %d/%d comments)",
            engaged, session_replies,
            _daily_actions["comments"], ENGAGEMENT_LIMITS["max_comments_per_day"],
        )
        return {"posts_engaged": engaged, "replies": session_replies}

    finally:
        db.close()


async def execute_engagement_loop(character: Character) -> dict:
    """Niche engagement: like and comment on posts in relevant hashtags.

    SAFE MODE:
    - Max 5 likes, 2 comments per session
    - 8-25 sec delay between likes
    - 45-120 sec delay between comments
    - Checks daily caps before each action
    - Stops immediately on action block
    - Skips during rest period (01:00-07:00)
    """
    if _is_rest_period():
        return {"liked": 0, "commented": 0, "reason": "rest_period"}

    _reset_daily_if_needed()

    if not _can_like():
        logger.info("Daily like limit reached (%d), skipping engagement", _daily_actions["likes"])
        return {"liked": 0, "commented": 0, "reason": "daily_limit"}

    from services.instagram_client import get_instagram_client

    ig = get_instagram_client()

    hashtag = random.choice(NICHE_HASHTAGS)
    liked = 0
    commented = 0

    try:
        medias = await ig.get_hashtag_medias(hashtag, amount=20)

        # Filter: target mid-range posts (not too big, not too small)
        targets = [
            m for m in medias
            if 100 < m.get("like_count", 0) < 5000
        ]

        random.shuffle(targets)

        for media in targets:
            if liked >= ENGAGEMENT_LIMITS["likes_per_session"] or not _can_like():
                break

            try:
                # Like with human-like delay
                await _safe_delay(ENGAGEMENT_LIMITS["delay_between_likes"])
                await ig.like_post(media["media_id"])
                liked += 1
                _daily_actions["likes"] += 1
                _daily_actions["total"] += 1

                # Comment rarely (20% chance, max 2 per session)
                if (
                    commented < ENGAGEMENT_LIMITS["comments_per_session"]
                    and _can_comment()
                    and random.random() < 0.2
                ):
                    await _safe_delay(ENGAGEMENT_LIMITS["delay_between_comments"])
                    comment_text = _generate_niche_comment(media.get("caption", ""))
                    await ig.comment_on_post(media["media_id"], comment_text)
                    commented += 1
                    _daily_actions["comments"] += 1
                    _daily_actions["total"] += 1

            except Exception as e:
                err_str = str(e).lower()
                if "action_block" in err_str or "challenge" in err_str or "spam" in err_str:
                    logger.error("ACTION BLOCK detected on #%s! Stopping immediately.", hashtag)
                    break
                logger.warning("Engagement action failed: %s", e)
                # Back off on any error
                await asyncio.sleep(random.uniform(60, 180))
                break

    except Exception as e:
        logger.warning("Engagement loop failed for #%s: %s", hashtag, e)

    logger.info(
        "Engagement: #%s — liked %d, commented %d (daily: L=%d/%d, C=%d/%d, total=%d/%d)",
        hashtag, liked, commented,
        _daily_actions["likes"], ENGAGEMENT_LIMITS["max_likes_per_day"],
        _daily_actions["comments"], ENGAGEMENT_LIMITS["max_comments_per_day"],
        _daily_actions["total"], ENGAGEMENT_LIMITS["max_total_actions_per_day"],
    )

    return {
        "hashtag": hashtag,
        "liked": liked,
        "commented": commented,
        "daily_total": _daily_actions["total"],
    }


def _generate_pin_comment(post: Post) -> str | None:
    """Generate a question to pin as top comment for engagement."""
    questions_by_category = {
        "workout": [
            "What's your favorite exercise? Tell me below! 👇",
            "How many times a week do you train? 💪",
            "Tag someone who needs this motivation! 🏋️‍♀️",
        ],
        "lifestyle": [
            "What does your ideal day look like? 🌟",
            "Drop a 💛 if you relate!",
            "Save this for later! 🔖",
        ],
        "motivation": [
            "What's keeping you going today? 💪",
            "Tag someone who needs to hear this! ❤️",
            "Save this and come back when you need motivation 🔖",
        ],
        "nutrition": [
            "What's your go-to healthy meal? 🥗",
            "Save this recipe! 🔖",
        ],
        "outfit": [
            "Rate this outfit 1-10! 👇",
            "Which color would you pick? Comment below! 🎨",
        ],
    }

    cat = post.category.value if post.category else "lifestyle"
    options = questions_by_category.get(cat, questions_by_category["lifestyle"])
    return random.choice(options)


def _generate_niche_comment(caption: str) -> str:
    """Generate a genuine-sounding niche comment."""
    comments = [
        "Love this energy! 🔥💪",
        "So inspiring! Keep going! 💪✨",
        "Goals!! 🙌",
        "This is amazing! 🔥",
        "You're killing it! 💪🔥",
        "Love the dedication! 🙌",
        "This is so motivating! 💛",
        "Wow, incredible! 🔥",
    ]
    return random.choice(comments)
