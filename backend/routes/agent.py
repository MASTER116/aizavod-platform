"""Agent orchestrator routes — status, decisions log, manual trigger."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import AgentDecision
from ..schemas import AgentDecisionRead, AgentStatusResponse, AgentTriggerRequest

router = APIRouter(prefix="/admin/api/agent", tags=["agent"])


@router.get("/status", response_model=AgentStatusResponse)
async def agent_status(_admin: str = Depends(verify_admin_token)):
    from services.agent_orchestrator import get_agent_status

    return await get_agent_status()


@router.get("/decisions", response_model=List[AgentDecisionRead])
def agent_decisions(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    return (
        db.query(AgentDecision)
        .order_by(AgentDecision.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/trigger")
async def agent_trigger(
    req: AgentTriggerRequest,
    _admin: str = Depends(verify_admin_token),
):
    """Manually trigger the agent orchestrator cycle."""
    from services.agent_orchestrator import run_cycle

    results = await run_cycle()
    return {"triggered": True, "actions": len(results), "results": results}


@router.get("/insights/audience")
def audience_insights(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from ..models import AudienceInsight

    return (
        db.query(AudienceInsight)
        .order_by(AudienceInsight.snapshot_date.desc())
        .limit(limit)
        .all()
    )


@router.get("/insights/competitors")
def competitor_insights(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from ..models import CompetitorProfile

    return (
        db.query(CompetitorProfile)
        .order_by(CompetitorProfile.last_analyzed_at.desc())
        .all()
    )


@router.get("/insights/viral")
def viral_insights(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from ..models import ViralContentAnalysis

    return (
        db.query(ViralContentAnalysis)
        .order_by(ViralContentAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )
