"""Pydantic-схемы для типизированных межагентных сообщений."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Access Levels (единая платформа) ────────────────────────────────────────

class AccessLevel(str, enum.Enum):
    """Уровни доступа к платформе."""
    SIMPLE = "simple"        # Публичный: 291 отрасль, базовые агенты
    PRO = "pro"              # Основатель: полный CONDUCTOR
    ENTERPRISE = "enterprise"  # Будущее: white-label, кастом-агенты


# ─── Agent Info ──────────────────────────────────────────────────────────────

@dataclass
class AgentInfo:
    """Описание зарегистрированного агента."""
    name: str
    title: str               # русское название для UI
    department: str          # директор/отдел
    description: str         # что умеет
    keywords: list[str]      # ключевые слова для быстрой маршрутизации
    handler: str             # имя async-функции для вызова
    access_level: AccessLevel = AccessLevel.SIMPLE  # минимальный уровень доступа
    tier: str = "free"       # free / starter / pro / enterprise
    credit_cost: int = 3     # стоимость в кредитах (1=простой, 3=средний, 8=тяжёлый)
    criticality: str = "E"   # ГОСТ Р 51904: C=существенный, D=незначительный, E=без последствий


# ─── Route Decision ──────────────────────────────────────────────────────────

@dataclass
class RouteDecision:
    """Результат классификации запроса."""
    agent: str
    confidence: float
    reasoning: str
    reformulated_query: str
    multi_agent: bool = False
    secondary_agents: list[str] = field(default_factory=list)


# ─── Conductor Result ────────────────────────────────────────────────────────

@dataclass
class ConductorResult:
    """Полный результат обработки запроса через CONDUCTOR."""
    query: str
    route: RouteDecision
    response: str
    agent_name: str
    department: str
    duration_ms: float
    secondary_responses: dict[str, str] = field(default_factory=dict)
    qa_score: float | None = None  # Оценка от QA-AGENT


# ─── Pydantic Models для межагентных сообщений ───────────────────────────────

class AgentMessage(BaseModel):
    """Типизированное сообщение между агентами."""
    source_agent: str = Field(..., description="Имя агента-отправителя")
    target_agent: str = Field(..., description="Имя агента-получателя")
    task: str = Field(..., description="Описание задачи")
    context: dict[str, Any] = Field(default_factory=dict, description="Контекст задачи")
    priority: str = Field(default="normal", pattern="^(critical|high|normal|low)$")
    user_id: int | None = Field(default=None, description="ID пользователя Telegram")
    session_id: str | None = Field(default=None, description="ID сессии")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    access_level: AccessLevel = Field(default=AccessLevel.SIMPLE)


class AgentResponse(BaseModel):
    """Типизированный ответ агента."""
    agent_name: str = Field(..., description="Имя агента")
    status: str = Field(default="success", pattern="^(success|error|partial|timeout)$")
    response: str = Field(..., description="Текст ответа")
    metadata: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = Field(default=0.0)
    model_used: str | None = Field(default=None, description="Использованная LLM модель")
    tokens_used: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    qa_verdict: str | None = Field(default=None, pattern="^(APPROVE|IMPROVE|REJECT)$|^None$")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QAVerdict(BaseModel):
    """Результат проверки QA-AGENT."""
    verdict: str = Field(..., pattern="^(APPROVE|IMPROVE|REJECT)$")
    scores: dict[str, float] = Field(default_factory=dict)
    total: float = Field(default=0.0)
    issues: list[str] = Field(default_factory=list)
    improved_response: str | None = None
    reasoning: str = ""


# ─── CEO Decomposition (валидация scope) ─────────────────────────────────────

class DirectorAssignment(BaseModel):
    """Назначение директора в CEO-декомпозиции."""
    role: str = Field(..., description="Код директора (cto, cfo, cmo, ...)")
    justification: str = Field(default="", description="Почему этот директор нужен")
    task: str = Field(..., description="Задача для директора")
    priority: str = Field(default="normal", pattern="^(critical|high|normal|low)$")
    estimated_hours: float = Field(default=2.0, ge=0.5, le=40)
    deliverables: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class CEODecomposition(BaseModel):
    """Результат CEO-декомпозиции задачи."""
    task_type: str = Field(default="technical", pattern="^(technical|product|business|marketing|legal|full)$")
    analysis: str = Field(default="", description="Краткий анализ задачи")
    directors: list[DirectorAssignment] = Field(..., max_length=3)


# ─── Memory Entry ─────────────────────────────────────────────────────────────

class MemoryEntry(BaseModel):
    """Запись в памяти агента."""
    memory_type: str = Field(..., pattern="^(episodic|factual|working)$")
    user_id: int
    agent_id: str
    content: str
    context_embedding: list[float] | None = None
    quality_score: float = Field(default=5.0, ge=0, le=10)
    trust_score: float = Field(default=0.5, ge=0, le=1)
    source: str = "agent_derived"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
