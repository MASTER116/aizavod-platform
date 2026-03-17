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


# ─── API Usage (Anthropic) ────────────────────────────────────────────────


@router.get("/api-usage")
def api_usage_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    """Статистика использования Anthropic API: токены, стоимость, по агентам."""
    from sqlalchemy import func
    from backend.models import ApiUsageLog
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Общая статистика
    totals = (
        db.query(
            func.count(ApiUsageLog.id),
            func.sum(ApiUsageLog.input_tokens),
            func.sum(ApiUsageLog.output_tokens),
            func.sum(ApiUsageLog.cost_usd),
            func.avg(ApiUsageLog.duration_ms),
        )
        .filter(ApiUsageLog.created_at >= cutoff)
        .first()
    )

    # По агентам
    by_agent = (
        db.query(
            ApiUsageLog.agent_name,
            func.count(ApiUsageLog.id),
            func.sum(ApiUsageLog.input_tokens),
            func.sum(ApiUsageLog.output_tokens),
            func.sum(ApiUsageLog.cost_usd),
        )
        .filter(ApiUsageLog.created_at >= cutoff)
        .group_by(ApiUsageLog.agent_name)
        .order_by(func.sum(ApiUsageLog.cost_usd).desc())
        .all()
    )

    # По моделям
    by_model = (
        db.query(
            ApiUsageLog.model,
            func.count(ApiUsageLog.id),
            func.sum(ApiUsageLog.cost_usd),
        )
        .filter(ApiUsageLog.created_at >= cutoff)
        .group_by(ApiUsageLog.model)
        .all()
    )

    # По дням
    by_day = (
        db.query(
            func.date(ApiUsageLog.created_at).label("day"),
            func.count(ApiUsageLog.id),
            func.sum(ApiUsageLog.cost_usd),
        )
        .filter(ApiUsageLog.created_at >= cutoff)
        .group_by(func.date(ApiUsageLog.created_at))
        .order_by(func.date(ApiUsageLog.created_at))
        .all()
    )

    # Ошибки
    errors = (
        db.query(func.count(ApiUsageLog.id))
        .filter(ApiUsageLog.created_at >= cutoff, ApiUsageLog.status == "error")
        .scalar()
    )

    return {
        "period_days": days,
        "total_requests": totals[0] or 0,
        "total_input_tokens": int(totals[1] or 0),
        "total_output_tokens": int(totals[2] or 0),
        "total_cost_usd": round(float(totals[3] or 0), 4),
        "avg_duration_ms": round(float(totals[4] or 0), 1),
        "total_errors": errors or 0,
        "by_agent": {
            name: {
                "requests": cnt,
                "input_tokens": int(inp or 0),
                "output_tokens": int(out or 0),
                "cost_usd": round(float(cost or 0), 4),
            }
            for name, cnt, inp, out, cost in by_agent
        },
        "by_model": {
            model: {"requests": cnt, "cost_usd": round(float(cost or 0), 4)}
            for model, cnt, cost in by_model
        },
        "by_day": [
            {"date": str(day), "requests": cnt, "cost_usd": round(float(cost or 0), 4)}
            for day, cnt, cost in by_day
        ],
    }
