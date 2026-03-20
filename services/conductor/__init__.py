"""CONDUCTOR — мета-оркестратор Zavod-ii.

Два режима:
  1. Роутер: вопрос → keyword/Claude классификация → один агент → ответ
  2. Оркестратор: задача → CEO-декомпозиция → директора → отделы → специалисты → сборка

Пакетная структура:
  - schemas: Pydantic-модели для типизированных межагентных сообщений
  - registry: реестр агентов (AgentInfo, AGENTS)
  - hierarchy: директора, отделы, специалисты
  - prompts: все промпты CONDUCTOR
  - routes: обработчики маршрутов (_route_* функции)
  - llm_client: Claude API клиент с circuit breaker и fallback
  - core: класс Conductor (основная логика)
  - safeguards: решение 12 критических проблем AI-агентных систем 2025-2026
  - session_trace: session-level observability с correlation_id и replay
"""

from services.conductor.core import Conductor, get_conductor
from services.conductor.schemas import (
    AgentInfo,
    RouteDecision,
    ConductorResult,
    AgentMessage,
    AgentResponse,
    AccessLevel,
)
from services.conductor.registry import AGENTS, get_agent_by_name, get_agents_for_level
from services.conductor.hierarchy import DIRECTORS, DEPARTMENT_SPECIALISTS
from services.conductor.llm_client import LLMClient, CircuitBreaker, get_llm_client
from services.conductor.safeguards import SafeguardsManager, get_safeguards
from services.conductor.session_trace import SessionTracer, get_session_tracer
from services.conductor.scope_classifier import classify_task_scope, classify_task_type, get_allowed_directors, filter_ceo_directors
from services.conductor.project_context import get_project_context_text

__all__ = [
    "Conductor",
    "get_conductor",
    "AgentInfo",
    "RouteDecision",
    "ConductorResult",
    "AgentMessage",
    "AgentResponse",
    "AccessLevel",
    "SafeguardsManager",
    "get_safeguards",
    "SessionTracer",
    "get_session_tracer",
]
