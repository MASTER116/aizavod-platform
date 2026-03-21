"""Dashboard API — endpoints for React SPA dashboard.

Exposes HealthMonitor, ObservabilityTracker, SessionTracer, AgentRegistry
data for the agent monitoring dashboard. Includes Team Chat with SSE streaming.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
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


# ─── Agent Personas ───────────────────────────────────────────────────────────

AGENT_PERSONAS = {
    "ceo_agent": {"avatar": "\U0001f454", "color": "#d4a017", "style": "Strategic leader", "quick_actions": ["Декомпозиция задачи", "Стратегия развития", "Приоритеты"]},
    "certifier": {"avatar": "\U0001f4cb", "color": "#ca8a04", "style": "Certification expert", "quick_actions": ["Сертификация", "ТР ТС ЕАЭС", "Таможня"]},
    "opportunity_scanner": {"avatar": "\U0001f50d", "color": "#22c55e", "style": "Opportunity hunter", "quick_actions": ["Поиск грантов", "Активные конкурсы", "Глубокий анализ"]},
    "idea_generator": {"avatar": "\U0001f4a1", "color": "#f59e0b", "style": "Creative ideator", "quick_actions": ["Идеи заработка", "Бизнес-модели", "Монетизация"]},
    "market_analyzer": {"avatar": "\U0001f4ca", "color": "#3b82f6", "style": "Market analyst", "quick_actions": ["Анализ рынка", "Конкуренты", "Оценка ниши"]},
    "freelance_agent": {"avatar": "\U0001f4bc", "color": "#8b5cf6", "style": "Freelance pro", "quick_actions": ["Заказы Kwork", "Анализ ТЗ", "Отклик"]},
    "pricing_agent": {"avatar": "\U0001f4b0", "color": "#10b981", "style": "Pricing expert", "quick_actions": ["Оценка проекта", "КП", "Смета Excel"]},
    "outreach_agent": {"avatar": "\U0001f4e7", "color": "#ec4899", "style": "Sales manager", "quick_actions": ["Холодные письма", "Поиск лидов", "Сегменты"]},
    "content_factory": {"avatar": "\U0001f3a8", "color": "#f97316", "style": "Content creator", "quick_actions": ["Пост Instagram", "Reels сценарий", "Контент-план"]},
    "lawyer_agent": {"avatar": "\u2696\ufe0f", "color": "#6366f1", "style": "Legal advisor", "quick_actions": ["Договор", "Регистрация ИП", "Юр. консультация"]},
    "accountant_agent": {"avatar": "\U0001f9ee", "color": "#14b8a6", "style": "Accountant", "quick_actions": ["Налоги", "Отчётность", "УСН или ОСН?"]},
    "darwin_agent": {"avatar": "\U0001f9ec", "color": "#a855f7", "style": "Quality optimizer", "quick_actions": ["Оптимизация агентов", "Отчёт качества", "Паттерны ошибок"]},
    "guardian_agent": {"avatar": "\U0001f6e1\ufe0f", "color": "#ef4444", "style": "Security guard", "quick_actions": ["Проверка безопасности", "Антифрод", "Анализ угроз"]},
    "scholar_agent": {"avatar": "\U0001f393", "color": "#0ea5e9", "style": "Academic scholar", "quick_actions": ["Грантовая заявка", "Литобзор", "Статья по ГОСТ"]},
    "herald_agent": {"avatar": "\U0001f4e2", "color": "#f43f5e", "style": "PR manager", "quick_actions": ["README", "Статья Хабр", "Product Hunt"]},
    "namer_agent": {"avatar": "\u270f\ufe0f", "color": "#84cc16", "style": "Naming specialist", "quick_actions": ["Нейминг", "Проверка домена", "Товарный знак"]},
    "guardian_ip_agent": {"avatar": "\U0001f510", "color": "#e11d48", "style": "IP protector", "quick_actions": ["Товарный знак", "Патент", "IP-аудит"]},
    "voice_agent": {"avatar": "\U0001f399\ufe0f", "color": "#7c3aed", "style": "Voice specialist", "quick_actions": ["Скрипт звонка", "TTS оптимизация", "Переговоры"]},
    "treasurer_agent": {"avatar": "\U0001f3e6", "color": "#059669", "style": "Treasurer", "quick_actions": ["Cash flow", "Анализ расходов", "Монетизация"]},
    "oracle_agent": {"avatar": "\U0001f52e", "color": "#2563eb", "style": "Predictive analyst", "quick_actions": ["Прогноз", "ML-модель", "Скоринг"]},
}


# ─── Chat ─────────────────────────────────────────────────────────────────────

# In-memory chat history
_chat_history: list[dict] = []
_MAX_HISTORY = 200


class ChatRequest(BaseModel):
    message: str
    agent: str | None = None


@router.get("/chat/agents")
def chat_agents():
    """Agent list with personas for chat UI."""
    from services.conductor.registry import AGENTS
    result = []
    for a in AGENTS:
        persona = AGENT_PERSONAS.get(a.name, {})
        result.append({
            "name": a.name,
            "title": a.title,
            "department": a.department,
            "description": a.description,
            "avatar": persona.get("avatar", "\U0001f916"),
            "color": persona.get("color", "#71717a"),
            "style": persona.get("style", ""),
            "quick_actions": persona.get("quick_actions", []),
            "access_level": a.access_level.value if hasattr(a.access_level, "value") else a.access_level,
        })
    return result


@router.get("/chat/history")
def chat_history(limit: int = Query(50, ge=1, le=200)):
    """Get recent chat messages."""
    return _chat_history[-limit:]


@router.post("/chat/send")
async def chat_send(body: ChatRequest):
    """Send message to CONDUCTOR and stream response via SSE."""

    user_msg = {
        "id": f"msg_{int(time.time() * 1000)}",
        "role": "user",
        "text": body.message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    _chat_history.append(user_msg)

    async def event_stream():
        from services.conductor.core import get_conductor

        # Send thinking event
        yield _sse("thinking", {"status": "classifying"})

        conductor = get_conductor()
        start = time.time()

        try:
            result = await conductor.process(body.message)

            # Send routed event
            yield _sse("routed", {
                "agent": result.agent_name,
                "department": result.department,
                "confidence": result.route.confidence,
                "reasoning": result.route.reasoning,
            })

            # Small delay for UI feel
            await asyncio.sleep(0.1)

            # Send the full response as chunk
            persona = AGENT_PERSONAS.get(result.agent_name, {})
            yield _sse("chunk", {
                "agent": result.agent_name,
                "title": persona.get("avatar", "\U0001f916") + " " + result.agent_name,
                "text": result.response,
            })

            # Send secondary responses if any
            for sec_agent, sec_text in result.secondary_responses.items():
                sec_persona = AGENT_PERSONAS.get(sec_agent, {})
                yield _sse("secondary", {
                    "agent": sec_agent,
                    "title": sec_persona.get("avatar", "\U0001f916") + " " + sec_agent,
                    "text": sec_text,
                })

            duration = (time.time() - start) * 1000

            # Done event with metrics
            yield _sse("done", {
                "agent": result.agent_name,
                "duration_ms": round(duration, 1),
                "qa_score": result.qa_score,
            })

            # Save agent message to history
            agent_msg = {
                "id": f"msg_{int(time.time() * 1000)}_agent",
                "role": "agent",
                "agent": result.agent_name,
                "avatar": persona.get("avatar", "\U0001f916"),
                "color": persona.get("color", "#71717a"),
                "title": next(
                    (a.title for a in __import__("services.conductor.registry", fromlist=["AGENTS"]).AGENTS if a.name == result.agent_name),
                    result.agent_name,
                ),
                "text": result.response,
                "duration_ms": round(duration, 1),
                "qa_score": result.qa_score,
                "department": result.department,
                "timestamp": datetime.utcnow().isoformat(),
            }
            _chat_history.append(agent_msg)
            if len(_chat_history) > _MAX_HISTORY:
                _chat_history[:] = _chat_history[-_MAX_HISTORY:]

        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
