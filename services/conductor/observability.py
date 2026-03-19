"""Agent Observability — трейсинг, cost tracking, quality metrics.

89% production agent systems имеют observability (Q1 2026).
Формат совместим с Langfuse/Braintrust для export.

Tracks: traces, cost, latency, quality scores per agent, per user, per session.
Alerts: cost threshold, error rate, latency degradation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any

logger = logging.getLogger("aizavod.observability")

# Cost per 1M tokens (March 2026 prices)
MODEL_COSTS = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    "qwen3:30b-a3b": {"input": 0.0, "output": 0.0},  # Local = free
}


@dataclass
class TraceSpan:
    """Один span в trace (один вызов агента/LLM)."""
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    agent_name: str = ""
    operation: str = ""  # classify, route, orchestrate, qa_check, etc.
    input_text: str = ""
    output_text: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    status: str = "success"  # success, error, timeout
    error: str = ""
    quality_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None


@dataclass
class Trace:
    """Полный trace одного запроса (от input до output)."""
    trace_id: str
    user_id: int | None = None
    session_id: str | None = None
    query: str = ""
    final_response: str = ""
    agent_name: str = ""
    spans: list[TraceSpan] = field(default_factory=list)
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None


class ObservabilityTracker:
    """Центральный трекер для всех agent interactions."""

    def __init__(self, daily_cost_alert_usd: float = 5.0):
        self._traces: list[Trace] = []
        self._daily_costs: dict[str, float] = {}  # date_str → total cost
        self._user_costs: dict[str, dict[str, float]] = {}  # user_id → {date → cost}
        self._agent_stats: dict[str, dict] = {}  # agent_name → stats
        self._daily_cost_alert = daily_cost_alert_usd
        self._span_counter = 0

    def _next_span_id(self) -> str:
        self._span_counter += 1
        return f"span_{self._span_counter}_{int(time.time() * 1000)}"

    def start_trace(self, query: str, user_id: int | None = None, session_id: str | None = None) -> str:
        """Начать trace для нового запроса."""
        trace_id = f"trace_{int(time.time() * 1000)}_{len(self._traces)}"
        trace = Trace(
            trace_id=trace_id,
            user_id=user_id,
            session_id=session_id,
            query=query[:500],
        )
        self._traces.append(trace)
        # Keep max 10000 traces
        if len(self._traces) > 10000:
            self._traces = self._traces[-5000:]
        return trace_id

    def add_span(
        self,
        trace_id: str,
        agent_name: str,
        operation: str,
        input_text: str = "",
        output_text: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        latency_ms: float = 0.0,
        status: str = "success",
        error: str = "",
        quality_score: float | None = None,
        parent_span_id: str | None = None,
    ) -> str:
        """Добавить span в trace."""
        trace = self._find_trace(trace_id)
        if not trace:
            return ""

        # Calculate cost
        cost = self._calculate_cost(model, input_tokens, output_tokens, cache_read_tokens)

        span = TraceSpan(
            span_id=self._next_span_id(),
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            agent_name=agent_name,
            operation=operation,
            input_text=input_text[:500],
            output_text=output_text[:500],
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            status=status,
            error=error,
            quality_score=quality_score,
        )

        trace.spans.append(span)
        trace.total_cost_usd += cost
        trace.total_latency_ms += latency_ms
        trace.total_tokens += input_tokens + output_tokens

        # Update daily costs
        today = date.today().isoformat()
        self._daily_costs[today] = self._daily_costs.get(today, 0) + cost

        # Update user costs
        if trace.user_id:
            uid = str(trace.user_id)
            if uid not in self._user_costs:
                self._user_costs[uid] = {}
            self._user_costs[uid][today] = self._user_costs[uid].get(today, 0) + cost

        # Update agent stats
        self._update_agent_stats(agent_name, latency_ms, cost, status == "success", quality_score)

        # Check cost alert
        if self._daily_costs.get(today, 0) > self._daily_cost_alert:
            logger.warning(
                "COST ALERT: Daily spend $%.2f exceeds threshold $%.2f",
                self._daily_costs[today], self._daily_cost_alert,
            )

        return span.span_id

    def end_trace(self, trace_id: str, final_response: str = "", agent_name: str = "") -> None:
        """Завершить trace."""
        trace = self._find_trace(trace_id)
        if trace:
            trace.ended_at = datetime.utcnow()
            trace.final_response = final_response[:500]
            if agent_name:
                trace.agent_name = agent_name

    def _find_trace(self, trace_id: str) -> Trace | None:
        for t in reversed(self._traces):
            if t.trace_id == trace_id:
                return t
        return None

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int, cache_tokens: int) -> float:
        """Рассчитать стоимость вызова."""
        costs = MODEL_COSTS.get(model, {"input": 1.0, "output": 5.0})
        # Cache tokens cost 90% less
        effective_input = max(0, input_tokens - cache_tokens) + cache_tokens * 0.1
        return (effective_input * costs["input"] + output_tokens * costs["output"]) / 1_000_000

    def _update_agent_stats(self, agent_name: str, latency_ms: float, cost: float, success: bool, quality: float | None):
        if agent_name not in self._agent_stats:
            self._agent_stats[agent_name] = {
                "total_calls": 0, "total_errors": 0, "total_cost": 0.0,
                "total_latency": 0.0, "quality_scores": [],
            }
        stats = self._agent_stats[agent_name]
        stats["total_calls"] += 1
        if not success:
            stats["total_errors"] += 1
        stats["total_cost"] += cost
        stats["total_latency"] += latency_ms
        if quality is not None:
            stats["quality_scores"].append(quality)
            # Keep last 100
            if len(stats["quality_scores"]) > 100:
                stats["quality_scores"] = stats["quality_scores"][-100:]

    # === Reporting ===

    def get_daily_cost(self, date_str: str | None = None) -> float:
        """Стоимость за день."""
        d = date_str or date.today().isoformat()
        return self._daily_costs.get(d, 0.0)

    def get_user_daily_cost(self, user_id: int, date_str: str | None = None) -> float:
        """Стоимость за день для конкретного пользователя."""
        d = date_str or date.today().isoformat()
        return self._user_costs.get(str(user_id), {}).get(d, 0.0)

    def get_agent_stats(self, agent_name: str) -> dict:
        """Статистика агента."""
        stats = self._agent_stats.get(agent_name, {})
        if not stats:
            return {"agent": agent_name, "total_calls": 0}
        total = stats["total_calls"]
        scores = stats["quality_scores"]
        return {
            "agent": agent_name,
            "total_calls": total,
            "error_rate": f"{stats['total_errors'] / max(total, 1) * 100:.1f}%",
            "total_cost_usd": f"${stats['total_cost']:.4f}",
            "avg_latency_ms": f"{stats['total_latency'] / max(total, 1):.0f}",
            "avg_quality": f"{sum(scores) / max(len(scores), 1):.1f}" if scores else "N/A",
        }

    def get_all_agent_stats(self) -> list[dict]:
        """Статистика всех агентов."""
        return [self.get_agent_stats(name) for name in sorted(self._agent_stats.keys())]

    def get_summary(self) -> dict:
        """Общая сводка."""
        today = date.today().isoformat()
        return {
            "total_traces": len(self._traces),
            "today_cost_usd": f"${self._daily_costs.get(today, 0):.4f}",
            "today_alert_threshold": f"${self._daily_cost_alert:.2f}",
            "active_agents": len(self._agent_stats),
            "total_users_today": len([
                uid for uid, dates in self._user_costs.items() if today in dates
            ]),
        }

    def export_langfuse_format(self, trace_id: str) -> dict | None:
        """Export trace в формате совместимом с Langfuse."""
        trace = self._find_trace(trace_id)
        if not trace:
            return None
        return {
            "id": trace.trace_id,
            "name": f"conductor_{trace.agent_name}",
            "userId": str(trace.user_id) if trace.user_id else None,
            "sessionId": trace.session_id,
            "input": trace.query,
            "output": trace.final_response,
            "metadata": {
                "total_cost_usd": trace.total_cost_usd,
                "total_tokens": trace.total_tokens,
                "total_latency_ms": trace.total_latency_ms,
            },
            "observations": [
                {
                    "id": s.span_id,
                    "parentObservationId": s.parent_span_id,
                    "name": f"{s.agent_name}.{s.operation}",
                    "type": "GENERATION",
                    "model": s.model,
                    "input": s.input_text,
                    "output": s.output_text,
                    "usage": {
                        "promptTokens": s.input_tokens,
                        "completionTokens": s.output_tokens,
                        "totalTokens": s.input_tokens + s.output_tokens,
                    },
                    "metadata": {
                        "cost_usd": s.cost_usd,
                        "latency_ms": s.latency_ms,
                        "cache_read_tokens": s.cache_read_tokens,
                        "quality_score": s.quality_score,
                    },
                    "level": "ERROR" if s.status == "error" else "DEFAULT",
                    "statusMessage": s.error if s.error else None,
                    "startTime": s.started_at.isoformat(),
                }
                for s in trace.spans
            ],
        }


# Singleton
_tracker: ObservabilityTracker | None = None


def get_tracker(daily_cost_alert_usd: float = 5.0) -> ObservabilityTracker:
    global _tracker
    if _tracker is None:
        _tracker = ObservabilityTracker(daily_cost_alert_usd)
    return _tracker
