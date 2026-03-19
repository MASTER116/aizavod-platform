"""SESSION-LEVEL OBSERVABILITY — End-to-end session tracing.

Проблема #21: Видим отдельные вызовы, но не полную картину сессии пользователя
от запроса до результата через 5 агентов.

Решение:
- Global correlation_id прокидывается через ВСЕ агенты
- Session replay: timeline с каждым шагом, решением, задержкой
- OpenTelemetry-like span model: каждый агент = span, весь workflow = trace
- Визуализация дерева исполнения
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("aizavod.session_trace")


@dataclass
class SessionSpan:
    """Один span в сессии (один шаг работы агента)."""
    span_id: str
    parent_span_id: str | None = None
    agent_name: str = ""
    operation: str = ""         # classify, route, execute, qa_check, etc.
    input_summary: str = ""     # Краткий ввод (до 200 символов)
    output_summary: str = ""    # Краткий вывод (до 200 символов)
    status: str = "running"     # running, success, error, timeout, skipped
    error_message: str = ""
    started_at: float = 0.0     # monotonic
    ended_at: float = 0.0
    duration_ms: float = 0.0
    model_used: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str = "success", output: str = "", error: str = "") -> None:
        self.ended_at = time.monotonic()
        self.duration_ms = (self.ended_at - self.started_at) * 1000
        self.status = status
        if output:
            self.output_summary = output[:200]
        if error:
            self.error_message = error


@dataclass
class SessionTrace:
    """Полная трассировка сессии от входа до выхода."""
    correlation_id: str                  # Global ID, прокидывается через все агенты
    user_id: int | None = None
    channel: str = "telegram"            # telegram, web, api
    query: str = ""
    final_response: str = ""
    mode: str = "router"                 # router | orchestrator
    spans: list[SessionSpan] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    total_duration_ms: float = 0.0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    agent_chain: list[str] = field(default_factory=list)  # Порядок вызовов агентов
    error_count: int = 0
    final_status: str = "pending"        # pending, success, partial, error


class SessionTracer:
    """Менеджер session-level traces.

    Обеспечивает:
    1. Генерация correlation_id в точке входа (Telegram/API/Web)
    2. Прокидывание через каждый agent call
    3. Session replay: полная timeline
    4. Blame assignment: какой агент где сломался
    """

    def __init__(self, max_sessions: int = 5000):
        self._sessions: dict[str, SessionTrace] = {}
        self._max_sessions = max_sessions
        self._start_times: dict[str, float] = {}  # correlation_id -> monotonic start

    @staticmethod
    def generate_correlation_id() -> str:
        """Генерация уникального correlation_id."""
        return f"ses_{uuid.uuid4().hex[:12]}_{int(time.time())}"

    def start_session(
        self,
        correlation_id: str | None = None,
        user_id: int | None = None,
        channel: str = "telegram",
        query: str = "",
        mode: str = "router",
    ) -> str:
        """Начать новую сессию. Возвращает correlation_id."""
        if not correlation_id:
            correlation_id = self.generate_correlation_id()

        session = SessionTrace(
            correlation_id=correlation_id,
            user_id=user_id,
            channel=channel,
            query=query[:500],
            mode=mode,
        )
        self._sessions[correlation_id] = session
        self._start_times[correlation_id] = time.monotonic()

        # Cleanup old sessions
        if len(self._sessions) > self._max_sessions:
            oldest_keys = sorted(self._sessions.keys())[:self._max_sessions // 2]
            for k in oldest_keys:
                self._sessions.pop(k, None)
                self._start_times.pop(k, None)

        logger.info("SESSION START: %s user=%s channel=%s mode=%s", correlation_id, user_id, channel, mode)
        return correlation_id

    def start_span(
        self,
        correlation_id: str,
        agent_name: str,
        operation: str,
        input_summary: str = "",
        parent_span_id: str | None = None,
    ) -> str:
        """Начать новый span в сессии. Возвращает span_id."""
        session = self._sessions.get(correlation_id)
        if not session:
            return ""

        span_id = f"sp_{uuid.uuid4().hex[:8]}"
        span = SessionSpan(
            span_id=span_id,
            parent_span_id=parent_span_id,
            agent_name=agent_name,
            operation=operation,
            input_summary=input_summary[:200],
            started_at=time.monotonic(),
        )
        session.spans.append(span)

        if agent_name and agent_name not in session.agent_chain:
            session.agent_chain.append(agent_name)

        return span_id

    def end_span(
        self,
        correlation_id: str,
        span_id: str,
        status: str = "success",
        output: str = "",
        error: str = "",
        model: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Завершить span."""
        session = self._sessions.get(correlation_id)
        if not session:
            return

        for span in session.spans:
            if span.span_id == span_id:
                span.finish(status=status, output=output, error=error)
                span.model_used = model
                span.tokens_in = tokens_in
                span.tokens_out = tokens_out
                span.cost_usd = cost_usd
                session.total_cost_usd += cost_usd
                session.total_tokens += tokens_in + tokens_out
                if status == "error":
                    session.error_count += 1
                break

    def end_session(
        self,
        correlation_id: str,
        final_response: str = "",
        status: str = "success",
    ) -> SessionTrace | None:
        """Завершить сессию."""
        session = self._sessions.get(correlation_id)
        if not session:
            return None

        session.ended_at = datetime.utcnow()
        session.final_response = final_response[:500]
        session.final_status = status

        start = self._start_times.get(correlation_id, 0)
        session.total_duration_ms = (time.monotonic() - start) * 1000 if start else 0

        logger.info(
            "SESSION END: %s status=%s duration=%.0fms agents=%s errors=%d cost=$%.4f",
            correlation_id, status, session.total_duration_ms,
            "->".join(session.agent_chain), session.error_count, session.total_cost_usd,
        )
        return session

    # === Session Replay ===

    def get_replay(self, correlation_id: str) -> dict | None:
        """Полный replay сессии — timeline с каждым шагом.

        Формат для UI: массив шагов с временными метками, агентами, статусами.
        """
        session = self._sessions.get(correlation_id)
        if not session:
            return None

        session_start = self._start_times.get(correlation_id, 0)

        timeline = []
        for span in session.spans:
            offset_ms = (span.started_at - session_start) * 1000 if session_start else 0
            timeline.append({
                "span_id": span.span_id,
                "parent_span_id": span.parent_span_id,
                "agent": span.agent_name,
                "operation": span.operation,
                "input": span.input_summary,
                "output": span.output_summary,
                "status": span.status,
                "error": span.error_message,
                "offset_ms": round(offset_ms, 1),
                "duration_ms": round(span.duration_ms, 1),
                "model": span.model_used,
                "tokens": span.tokens_in + span.tokens_out,
                "cost_usd": round(span.cost_usd, 6),
            })

        return {
            "correlation_id": session.correlation_id,
            "user_id": session.user_id,
            "channel": session.channel,
            "query": session.query,
            "final_response": session.final_response,
            "mode": session.mode,
            "status": session.final_status,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "total_duration_ms": round(session.total_duration_ms, 1),
            "total_cost_usd": round(session.total_cost_usd, 6),
            "total_tokens": session.total_tokens,
            "agent_chain": session.agent_chain,
            "error_count": session.error_count,
            "timeline": timeline,
        }

    def get_blame(self, correlation_id: str) -> dict | None:
        """Blame assignment: какой агент вызвал ошибку в сессии."""
        session = self._sessions.get(correlation_id)
        if not session:
            return None

        error_spans = [s for s in session.spans if s.status == "error"]
        slowest_span = max(session.spans, key=lambda s: s.duration_ms) if session.spans else None

        return {
            "correlation_id": correlation_id,
            "total_errors": len(error_spans),
            "error_agents": [
                {"agent": s.agent_name, "operation": s.operation, "error": s.error_message}
                for s in error_spans
            ],
            "slowest_agent": {
                "agent": slowest_span.agent_name,
                "operation": slowest_span.operation,
                "duration_ms": round(slowest_span.duration_ms, 1),
            } if slowest_span else None,
            "agent_chain": session.agent_chain,
        }

    # === Reporting ===

    def get_recent_sessions(self, limit: int = 20, user_id: int | None = None) -> list[dict]:
        """Последние сессии."""
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        sessions.sort(key=lambda s: s.started_at, reverse=True)

        return [
            {
                "correlation_id": s.correlation_id,
                "user_id": s.user_id,
                "query": s.query[:100],
                "status": s.final_status,
                "mode": s.mode,
                "agents": len(s.agent_chain),
                "duration_ms": round(s.total_duration_ms, 1),
                "cost_usd": round(s.total_cost_usd, 6),
                "errors": s.error_count,
                "started_at": s.started_at.isoformat(),
            }
            for s in sessions[:limit]
        ]

    def get_summary(self) -> dict:
        """Общая сводка по сессиям."""
        sessions = list(self._sessions.values())
        completed = [s for s in sessions if s.final_status != "pending"]
        errors = [s for s in completed if s.final_status == "error"]

        avg_duration = (
            sum(s.total_duration_ms for s in completed) / len(completed)
            if completed else 0
        )
        avg_cost = (
            sum(s.total_cost_usd for s in completed) / len(completed)
            if completed else 0
        )

        return {
            "total_sessions": len(sessions),
            "completed": len(completed),
            "errors": len(errors),
            "error_rate": f"{len(errors) / max(len(completed), 1) * 100:.1f}%",
            "avg_duration_ms": round(avg_duration, 1),
            "avg_cost_usd": round(avg_cost, 6),
            "avg_agents_per_session": round(
                sum(len(s.agent_chain) for s in completed) / max(len(completed), 1), 1
            ),
        }


# ─── Singleton ────────────────────────────────────────────────────────────────

_session_tracer: SessionTracer | None = None


def get_session_tracer() -> SessionTracer:
    global _session_tracer
    if _session_tracer is None:
        _session_tracer = SessionTracer()
    return _session_tracer
