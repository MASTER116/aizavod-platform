"""Monetization service — media kit generation, rate card calculation."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models import DailyMetrics, Post, PostStatus, PostAnalytics

logger = logging.getLogger("aizavod.monetization")


def calculate_rate_card(db: Session) -> dict:
    """Calculate recommended pricing for sponsored content based on followers and engagement."""
    latest = db.query(DailyMetrics).order_by(DailyMetrics.date.desc()).first()
    followers = latest.followers_count if latest else 0

    avg_er = db.query(func.avg(PostAnalytics.engagement_rate)).scalar() or 0.0
    avg_reach = db.query(func.avg(PostAnalytics.reach)).scalar() or 0

    # Pricing formulas (industry standard approximations)
    # Base rate: $10 per 1K followers, adjusted by engagement
    er_multiplier = max(0.5, min(2.0, avg_er / 3.0))  # 3% ER = 1x, 6% = 2x

    base_cpm = 10  # $10 per 1K followers
    base_rate = (followers / 1000) * base_cpm * er_multiplier

    return {
        "followers": followers,
        "avg_engagement_rate": round(avg_er, 2),
        "avg_reach": int(avg_reach),
        "rates": {
            "feed_post": {
                "usd": round(base_rate, 2),
                "description": "Single feed post with brand mention",
            },
            "carousel": {
                "usd": round(base_rate * 1.5, 2),
                "description": "Carousel post (3-5 slides) with product showcase",
            },
            "reel": {
                "usd": round(base_rate * 2.0, 2),
                "description": "Short-form video reel with brand integration",
            },
            "story_set": {
                "usd": round(base_rate * 0.5, 2),
                "description": "3-5 story frames with swipe-up link",
            },
            "full_package": {
                "usd": round(base_rate * 3.5, 2),
                "description": "Feed post + Reel + Story set + 1 month brand ambassador",
            },
        },
        "currency": "USD",
    }


def generate_media_kit_data(db: Session, character=None) -> dict:
    """Generate data for a media kit.

    Args:
        db: SQLAlchemy session
        character: Character model instance (optional, for niche/name data)
    """
    latest = db.query(DailyMetrics).order_by(DailyMetrics.date.desc()).first()

    # Growth stats (last 30 days)
    from datetime import timedelta
    import json

    cutoff = date.today() - timedelta(days=30)
    month_start = db.query(DailyMetrics).filter(DailyMetrics.date >= cutoff).order_by(DailyMetrics.date).first()

    growth_30d = 0
    if latest and month_start:
        growth_30d = latest.followers_count - month_start.followers_count

    avg_er = db.query(func.avg(PostAnalytics.engagement_rate)).scalar() or 0
    avg_likes = db.query(func.avg(PostAnalytics.likes)).scalar() or 0
    avg_comments = db.query(func.avg(PostAnalytics.comments_count)).scalar() or 0
    avg_reach = db.query(func.avg(PostAnalytics.reach)).scalar() or 0

    total_posts = db.query(Post).filter(Post.status == PostStatus.PUBLISHED).count()

    rate_card = calculate_rate_card(db)

    # Extract character-specific data
    char_name = character.name if character else ""
    niche = character.niche_description if character else ""

    try:
        content_cats = json.loads(character.content_categories) if character else []
    except (json.JSONDecodeError, TypeError):
        content_cats = []
    content_types = [c.replace("_", " ").title() for c in content_cats[:6]]

    return {
        "profile": {
            "name": char_name,
            "niche": niche,
            "content_types": content_types or ["Content"],
            "languages": ["Russian", "English"],
        },
        "stats": {
            "followers": latest.followers_count if latest else 0,
            "following": latest.following_count if latest else 0,
            "total_posts": total_posts,
            "growth_30d": growth_30d,
            "avg_engagement_rate": round(avg_er, 2),
            "avg_likes_per_post": int(avg_likes),
            "avg_comments_per_post": int(avg_comments),
            "avg_reach_per_post": int(avg_reach),
        },
        "audience": {
            "primary_age": "18-34",
            "top_locations": ["Russia", "CIS", "USA", "Europe"],
        },
        "rates": rate_card["rates"],
        "collaboration_types": [
            "Product placement in posts",
            "Brand ambassador partnerships",
            "Content collaborations",
            "Sponsored posts and reels",
        ],
    }
