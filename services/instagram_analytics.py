"""Instagram analytics collection service."""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models import Post, PostStatus, PostAnalytics, DailyMetrics

logger = logging.getLogger("aizavod.instagram_analytics")


def get_analytics_overview(db: Session) -> dict:
    """Get a summary of current analytics."""
    # Total published posts
    total_posts = db.query(Post).filter(Post.status == PostStatus.PUBLISHED).count()

    # Posts pending review
    pending = db.query(Post).filter(
        Post.status.in_([PostStatus.GENERATED, PostStatus.REVIEW])
    ).count()

    # Scheduled
    scheduled = db.query(Post).filter(Post.status == PostStatus.SCHEDULED).count()

    # Average engagement rate
    avg_er = db.query(func.avg(PostAnalytics.engagement_rate)).scalar() or 0.0

    # Total cost
    total_cost = db.query(func.sum(Post.generation_cost_usd)).scalar() or 0.0

    # Latest daily metrics
    latest_metrics = db.query(DailyMetrics).order_by(DailyMetrics.date.desc()).first()

    return {
        "total_followers": latest_metrics.followers_count if latest_metrics else 0,
        "followers_today": latest_metrics.followers_gained if latest_metrics else 0,
        "total_posts": total_posts,
        "avg_engagement_rate": round(avg_er, 2),
        "total_reach_today": latest_metrics.total_reach if latest_metrics else 0,
        "pending_posts": pending,
        "scheduled_posts": scheduled,
        "total_cost_usd": round(total_cost, 2),
    }


def get_top_posts(db: Session, limit: int = 10) -> list[dict]:
    """Get top performing posts by engagement rate."""
    results = (
        db.query(Post, PostAnalytics)
        .join(PostAnalytics, PostAnalytics.post_id == Post.id)
        .filter(Post.status == PostStatus.PUBLISHED)
        .order_by(PostAnalytics.engagement_rate.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "post_id": post.id,
            "category": post.category.value,
            "content_type": post.content_type.value,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "likes": analytics.likes,
            "comments": analytics.comments_count,
            "saves": analytics.saves,
            "shares": analytics.shares,
            "reach": analytics.reach,
            "engagement_rate": round(analytics.engagement_rate, 2),
            "image_path": post.image_path,
        }
        for post, analytics in results
    ]


def get_content_performance(db: Session) -> dict:
    """Get performance breakdown by content category."""
    results = (
        db.query(
            Post.category,
            func.count(Post.id).label("count"),
            func.avg(PostAnalytics.engagement_rate).label("avg_er"),
            func.sum(PostAnalytics.likes).label("total_likes"),
            func.sum(PostAnalytics.reach).label("total_reach"),
        )
        .join(PostAnalytics, PostAnalytics.post_id == Post.id)
        .filter(Post.status == PostStatus.PUBLISHED)
        .group_by(Post.category)
        .all()
    )

    return {
        row.category.value: {
            "count": row.count,
            "avg_engagement_rate": round(row.avg_er or 0, 2),
            "total_likes": row.total_likes or 0,
            "total_reach": row.total_reach or 0,
        }
        for row in results
    }


def get_growth_data(db: Session, days: int = 30) -> list[dict]:
    """Get daily follower growth data."""
    cutoff = date.today() - timedelta(days=days)
    metrics = (
        db.query(DailyMetrics)
        .filter(DailyMetrics.date >= cutoff)
        .order_by(DailyMetrics.date)
        .all()
    )

    return [
        {
            "date": m.date.isoformat(),
            "followers": m.followers_count,
            "gained": m.followers_gained,
            "lost": m.followers_lost,
            "posts": m.posts_count,
            "avg_er": round(m.avg_engagement_rate, 2),
        }
        for m in metrics
    ]
