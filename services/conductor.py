"""CONDUCTOR — мета-оркестратор AI Zavod.

DEPRECATED: Этот файл оставлен для обратной совместимости.
Вся логика перенесена в пакет services/conductor/.

Структура пакета:
  - conductor/__init__.py   — экспорты
  - conductor/schemas.py    — Pydantic-схемы
  - conductor/registry.py   — реестр агентов
  - conductor/hierarchy.py  — директора, отделы, специалисты
  - conductor/prompts.py    — все промпты
  - conductor/routes.py     — обработчики маршрутов
  - conductor/llm_client.py — LLM-клиент с circuit breaker
  - conductor/core.py       — класс Conductor
"""

# Re-export всего для обратной совместимости
from services.conductor.schemas import (
    AgentInfo,
    RouteDecision,
    ConductorResult,
    AgentMessage,
    AgentResponse,
    AccessLevel,
)
from services.conductor.registry import AGENTS
from services.conductor.hierarchy import DIRECTORS, DEPARTMENT_SPECIALISTS
from services.conductor.prompts import (
    CLASSIFIER_PROMPT,
    CEO_DECOMPOSE_PROMPT,
    DIRECTOR_DECOMPOSE_PROMPT,
    DEPARTMENT_DECOMPOSE_PROMPT,
    COLLECT_RESULTS_PROMPT,
    TASK_KEYWORDS,
    QUESTION_KEYWORDS,
)
from services.conductor.routes import *  # noqa: F401, F403
from services.conductor.core import Conductor, get_conductor

__all__ = [
    "AgentInfo",
    "RouteDecision",
    "ConductorResult",
    "AgentMessage",
    "AgentResponse",
    "AccessLevel",
    "AGENTS",
    "DIRECTORS",
    "DEPARTMENT_SPECIALISTS",
    "CLASSIFIER_PROMPT",
    "CEO_DECOMPOSE_PROMPT",
    "DIRECTOR_DECOMPOSE_PROMPT",
    "DEPARTMENT_DECOMPOSE_PROMPT",
    "COLLECT_RESULTS_PROMPT",
    "TASK_KEYWORDS",
    "QUESTION_KEYWORDS",
    "Conductor",
    "get_conductor",
]
