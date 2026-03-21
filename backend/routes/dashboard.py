"""Dashboard API — endpoints for React SPA dashboard.

Exposes HealthMonitor, ObservabilityTracker, SessionTracer, AgentRegistry
data for the agent monitoring dashboard.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..admin_auth import verify_admin_token

router = APIRouter(
    prefix="/admin/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(verify_admin_token)],
)


# ─── Request / Response Models ────────────────────────────────────────────────

class AgentActionRequest(BaseModel):
    reason: str = ""


# ─── Agent Health ─────────────────────────────────────────────────────────────

@router.get("/agents/health")
def agents_health():
    from services.health_monitor import get_health_monitor
    return get_health_monitor().get_all_status()


@router.get("/agents/summary")
def agents_summary():
    from services.health_monitor import get_health_monitor
    return get_health_monitor().get_summary()


@router.get("/agents/audit")
def agents_audit(limit: int = Query(50, ge=1, le=500)):
    from services.health_monitor import get_health_monitor
    return get_health_monitor().get_audit_log(limit)


@router.post("/agents/{name}/kill")
def agent_kill(name: str, body: AgentActionRequest):
    from services.health_monitor import get_health_monitor
    ok = get_health_monitor().kill(name, body.reason or "Dashboard kill-switch")
    return {"ok": ok, "agent": name, "action": "kill"}


@router.post("/agents/{name}/revive")
def agent_revive(name: str):
    from services.health_monitor import get_health_monitor
    ok = get_health_monitor().revive(name)
    return {"ok": ok, "agent": name, "action": "revive"}


@router.post("/agents/{name}/suspend")
def agent_suspend(name: str, body: AgentActionRequest):
    from services.health_monitor import get_health_monitor
    ok = get_health_monitor().suspend(name, body.reason or "Dashboard suspend")
    return {"ok": ok, "agent": name, "action": "suspend"}


# ─── Agent Registry ───────────────────────────────────────────────────────────

@router.get("/agents/registry")
def agents_registry():
    from services.conductor.registry import AGENTS
    return [
        {
            "name": a.name,
            "title": a.title,
            "department": a.department,
            "description": a.description,
            "access_level": a.access_level.value if hasattr(a.access_level, "value") else a.access_level,
            "tier": a.tier,
            "credit_cost": a.credit_cost,
            "criticality": a.criticality,
        }
        for a in AGENTS
    ]


# ─── Hierarchy ────────────────────────────────────────────────────────────────

@router.get("/hierarchy")
def hierarchy():
    from services.conductor.hierarchy import DIRECTORS, DEPARTMENT_SPECIALISTS
    return {
        "directors": DIRECTORS,
        "specialists": DEPARTMENT_SPECIALISTS,
    }


# ─── Observability ────────────────────────────────────────────────────────────

@router.get("/observability/summary")
def observability_summary():
    from services.conductor.observability import get_tracker
    return get_tracker().get_summary()


@router.get("/observability/agents")
def observability_agents():
    from services.conductor.observability import get_tracker
    return get_tracker().get_all_agent_stats()


@router.get("/observability/daily-costs")
def observability_daily_costs(
    date_from: str = Query(
        default=None,
        alias="from",
        description="Start date YYYY-MM-DD",
    ),
    date_to: str = Query(
        default=None,
        alias="to",
        description="End date YYYY-MM-DD",
    ),
):
    from services.conductor.observability import get_tracker
    tracker = get_tracker()

    today = date.today()
    if not date_from:
        start = today - timedelta(days=30)
    else:
        start = date.fromisoformat(date_from)
    if not date_to:
        end = today
    else:
        end = date.fromisoformat(date_to)

    result = []
    current = start
    while current <= end:
        d = current.isoformat()
        result.append({"date": d, "cost_usd": tracker.get_daily_cost(d)})
        current += timedelta(days=1)
    return result


# ─── Sessions ─────────────────────────────────────────────────────────────────

@router.get("/sessions/recent")
def sessions_recent(limit: int = Query(20, ge=1, le=100)):
    from services.conductor.session_trace import get_session_tracer
    return get_session_tracer().get_recent_sessions(limit)


@router.get("/sessions/summary")
def sessions_summary():
    from services.conductor.session_trace import get_session_tracer
    return get_session_tracer().get_summary()


@router.get("/sessions/{correlation_id}/replay")
def session_replay(correlation_id: str):
    from services.conductor.session_trace import get_session_tracer
    data = get_session_tracer().get_replay(correlation_id)
    if not data:
        return {"error": "Session not found"}
    return data


@router.get("/sessions/{correlation_id}/blame")
def session_blame(correlation_id: str):
    from services.conductor.session_trace import get_session_tracer
    data = get_session_tracer().get_blame(correlation_id)
    if not data:
        return {"error": "Session not found"}
    return data
