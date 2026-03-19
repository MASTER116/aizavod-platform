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

__all__ = [
    "Conductor",
    "get_conductor",
    "AgentInfo",
    "RouteDecision",
    "ConductorResult",
    "AgentMessage",
    "AgentResponse",
    "AccessLevel",
]
