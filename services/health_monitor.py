"""Health Monitor + Kill-Switch (DEADMAN) для агентов.

Функции:
- Heartbeat мониторинг каждого агента
- Automatic circuit breaker при деградации
- Manual kill-switch через Telegram
- Purpose binding (агент не может выйти за рамки своих полномочий)
- Аудит всех действий
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("aizavod.health_monitor")


class AgentStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    KILLED = "killed"


@dataclass
class AgentHealth:
    """Состояние здоровья агента."""
    name: str
    status: AgentStatus = AgentStatus.HEALTHY
    last_heartbeat: float = 0.0
    total_calls: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_error: str = ""
    kill_reason: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def error_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_errors / self.total_calls

    @property
    def is_alive(self) -> bool:
        return self.status not in (AgentStatus.KILLED, AgentStatus.UNHEALTHY)


class HealthMonitor:
    """Мониторинг здоровья агентов + DEADMAN kill-switch."""

    def __init__(
        self,
        error_threshold: float = 0.3,
        latency_threshold_ms: float = 30000,
        heartbeat_timeout_s: float = 300,
    ):
        self._agents: dict[str, AgentHealth] = {}
        self._error_threshold = error_threshold
        self._latency_threshold = latency_threshold_ms
        self._heartbeat_timeout = heartbeat_timeout_s
        self._kill_list: set[str] = set()
        self._audit_log: list[dict] = []

    def register(self, agent_name: str) -> None:
        """Зарегистрировать агента для мониторинга."""
        if agent_name not in self._agents:
            self._agents[agent_name] = AgentHealth(name=agent_name, last_heartbeat=time.monotonic())

    def heartbeat(self, agent_name: str) -> None:
        """Записать heartbeat агента."""
        if agent_name in self._agents:
            self._agents[agent_name].last_heartbeat = time.monotonic()

    def record_call(self, agent_name: str, latency_ms: float, success: bool, error: str = "") -> None:
        """Записать результат вызова агента."""
        self.register(agent_name)
        agent = self._agents[agent_name]
        agent.total_calls += 1
        agent.last_heartbeat = time.monotonic()

        # Running average latency
        if agent.avg_latency_ms == 0:
            agent.avg_latency_ms = latency_ms
        else:
            agent.avg_latency_ms = agent.avg_latency_ms * 0.9 + latency_ms * 0.1

        if not success:
            agent.total_errors += 1
            agent.last_error = error

        # Auto-detect degradation
        self._evaluate_health(agent_name)

    def _evaluate_health(self, agent_name: str) -> None:
        """Оценить здоровье агента."""
        agent = self._agents.get(agent_name)
        if not agent or agent.status == AgentStatus.KILLED:
            return

        if agent.error_rate > self._error_threshold:
            agent.status = AgentStatus.UNHEALTHY
            self._audit("auto_unhealthy", agent_name,
                        f"Error rate {agent.error_rate:.1%} > threshold {self._error_threshold:.1%}")
            logger.warning("Agent %s marked UNHEALTHY (error_rate=%.1f%%)", agent_name, agent.error_rate * 100)
        elif agent.avg_latency_ms > self._latency_threshold:
            agent.status = AgentStatus.DEGRADED
            self._audit("auto_degraded", agent_name,
                        f"Avg latency {agent.avg_latency_ms:.0f}ms > threshold {self._latency_threshold:.0f}ms")
        else:
            agent.status = AgentStatus.HEALTHY

    def check_stale(self) -> list[str]:
        """Проверить агентов без heartbeat (stale)."""
        now = time.monotonic()
        stale = []
        for name, agent in self._agents.items():
            if agent.status == AgentStatus.KILLED:
                continue
            if now - agent.last_heartbeat > self._heartbeat_timeout:
                agent.status = AgentStatus.DEGRADED
                stale.append(name)
        return stale

    # === DEADMAN Kill-Switch ===

    def kill(self, agent_name: str, reason: str = "Manual kill-switch") -> bool:
        """DEADMAN: принудительно остановить агента."""
        self.register(agent_name)
        agent = self._agents[agent_name]
        agent.status = AgentStatus.KILLED
        agent.kill_reason = reason
        self._kill_list.add(agent_name)
        self._audit("kill", agent_name, reason)
        logger.critical("DEADMAN: Agent %s KILLED — %s", agent_name, reason)
        return True

    def revive(self, agent_name: str) -> bool:
        """Восстановить убитого агента."""
        if agent_name in self._agents:
            self._agents[agent_name].status = AgentStatus.HEALTHY
            self._agents[agent_name].kill_reason = ""
            self._agents[agent_name].total_errors = 0
            self._kill_list.discard(agent_name)
            self._audit("revive", agent_name, "Agent revived")
            logger.info("Agent %s REVIVED", agent_name)
            return True
        return False

    def is_killed(self, agent_name: str) -> bool:
        """Проверить, убит ли агент."""
        return agent_name in self._kill_list

    def can_execute(self, agent_name: str) -> bool:
        """Может ли агент выполнять запросы."""
        if agent_name in self._kill_list:
            return False
        agent = self._agents.get(agent_name)
        if agent and agent.status == AgentStatus.UNHEALTHY:
            return False
        return True

    # === Reporting ===

    def get_status(self, agent_name: str) -> dict | None:
        """Получить статус агента."""
        agent = self._agents.get(agent_name)
        if not agent:
            return None
        return {
            "name": agent.name,
            "status": agent.status.value,
            "total_calls": agent.total_calls,
            "total_errors": agent.total_errors,
            "error_rate": f"{agent.error_rate:.1%}",
            "avg_latency_ms": f"{agent.avg_latency_ms:.0f}",
            "last_error": agent.last_error,
            "kill_reason": agent.kill_reason,
            "is_alive": agent.is_alive,
        }

    def get_all_status(self) -> list[dict]:
        """Получить статус всех агентов."""
        return [self.get_status(name) for name in self._agents]

    def get_summary(self) -> dict:
        """Общая сводка здоровья системы."""
        agents = list(self._agents.values())
        return {
            "total_agents": len(agents),
            "healthy": sum(1 for a in agents if a.status == AgentStatus.HEALTHY),
            "degraded": sum(1 for a in agents if a.status == AgentStatus.DEGRADED),
            "unhealthy": sum(1 for a in agents if a.status == AgentStatus.UNHEALTHY),
            "killed": sum(1 for a in agents if a.status == AgentStatus.KILLED),
            "total_calls": sum(a.total_calls for a in agents),
            "total_errors": sum(a.total_errors for a in agents),
            "killed_agents": list(self._kill_list),
        }

    def _audit(self, action: str, agent: str, details: str):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "agent": agent,
            "details": details,
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        return self._audit_log[-limit:]


# Singleton
_health_monitor: HealthMonitor | None = None


def get_health_monitor() -> HealthMonitor:
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
