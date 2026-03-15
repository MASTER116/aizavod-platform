"""CONDUCTOR API — маршрутизация запросов через REST."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter(prefix="/api/conductor", tags=["conductor"])


class ConductorRequest(BaseModel):
    query: str


class ConductorResponse(BaseModel):
    query: str
    agent: str
    department: str
    confidence: float
    reasoning: str
    response: str
    duration_ms: float
    secondary_responses: dict[str, str] = {}


@router.post("/route", response_model=ConductorResponse)
async def route_query(req: ConductorRequest):
    """Принять запрос на естественном языке и маршрутизировать к агенту."""
    from services.conductor import get_conductor

    conductor = get_conductor()
    result = await conductor.process(req.query)

    return ConductorResponse(
        query=result.query,
        agent=result.agent_name,
        department=result.department,
        confidence=result.route.confidence,
        reasoning=result.route.reasoning,
        response=result.response,
        duration_ms=result.duration_ms,
        secondary_responses=result.secondary_responses,
    )


@router.get("/agents")
async def list_agents():
    """Список доступных агентов."""
    from services.conductor import AGENTS

    return [
        {
            "name": a.name,
            "department": a.department,
            "description": a.description,
        }
        for a in AGENTS
    ]
