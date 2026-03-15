"""Analytics and metrics routes."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..schemas import AnalyticsOverview, DailyMetricsRead, GenerationLogRead

router = APIRouter(prefix="/admin/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from services.instagram_analytics import get_analytics_overview

    return get_analytics_overview(db)


@router.get("/daily", response_model=List[DailyMetricsRead])
def daily_metrics(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from services.instagram_analytics import get_growth_data
    from backend.models import DailyMetrics
    from datetime import date, timedelta

    cutoff = date.today() - timedelta(days=days)
    return db.query(DailyMetrics).filter(DailyMetrics.date >= cutoff).order_by(DailyMetrics.date).all()


@router.get("/posts/top")
def top_posts(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from services.instagram_analytics import get_top_posts

    return get_top_posts(db, limit)


@router.get("/growth")
def growth_report(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from services.instagram_analytics import get_growth_data

    return get_growth_data(db, days)


@router.get("/content_performance")
def content_performance(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from services.instagram_analytics import get_content_performance

    return get_content_performance(db)


@router.get("/logs", response_model=List[GenerationLogRead])
def generation_logs(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from backend.models import GenerationLog

    return db.query(GenerationLog).order_by(GenerationLog.created_at.desc()).limit(limit).all()


@router.get("/costs")
def cost_summary(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from sqlalchemy import func
    from backend.models import GenerationLog
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()

    # Today's cost
    today_cost = (
        db.query(func.sum(GenerationLog.cost_usd))
        .filter(GenerationLog.created_at >= datetime.combine(today, datetime.min.time()))
        .scalar() or 0
    )

    # This month
    month_start = today.replace(day=1)
    month_cost = (
        db.query(func.sum(GenerationLog.cost_usd))
        .filter(GenerationLog.created_at >= datetime.combine(month_start, datetime.min.time()))
        .scalar() or 0
    )

    # All time
    total_cost = db.query(func.sum(GenerationLog.cost_usd)).scalar() or 0

    # Count by action
    actions = (
        db.query(GenerationLog.action, func.count(), func.sum(GenerationLog.cost_usd))
        .group_by(GenerationLog.action)
        .all()
    )

    return {
        "today_usd": round(today_cost, 2),
        "month_usd": round(month_cost, 2),
        "total_usd": round(total_cost, 2),
        "by_action": {
            action: {"count": count, "cost_usd": round(cost or 0, 2)}
            for action, count, cost in actions
        },
    }
