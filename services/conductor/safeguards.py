"""SAFEGUARDS — Решение 12 критических проблем AI-агентных систем 2025-2026.

Проблемы и решения:
#14 Deadlock Detection — обнаружение циклических зависимостей между агентами
#15 Latency Budget — бюджет латентности + параллельный dispatch
#16 Role Boundary Validator — проверка что агент не выходит за рамки роли
#17 Agent Identity Management — lifecycle, credentials, scope
#18 Inter-Agent Firewall — санитизация данных между агентами
#19 Agent Sprawl Prevention — auto-sunset, usage tracking, дедупликация
#20 Coordination Tax Limiter — ограничение handoffs per workflow
#22 UX Transparency — progress streaming, confidence display
#24 Over-Permissioning Prevention — per-agent tool allowlist
#25 Debugging Acceleration — error taxonomy, blame assignment

Каждый компонент — отдельный класс, все подключаются к CONDUCTOR pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("aizavod.safeguards")


# ─── #14: DEADLOCK DETECTION ─────────────────────────────────────────────────


class DeadlockDetector:
    """Обнаружение циклических зависимостей в графе задач.

    Проблема #14: Оркестратор ждёт агента A, агент A ждёт агента B,
    агент B ждёт оркестратора. Ошибки нет — бесконечная задержка.
    """

    def __init__(self, timeout_seconds: float = 60.0):
        self._timeout = timeout_seconds
        # agent_name -> set of agents it's waiting for
        self._wait_graph: dict[str, set[str]] = defaultdict(set)
        # agent_name -> timestamp when started waiting
        self._wait_started: dict[str, float] = {}

    def register_wait(self, waiter: str, waiting_for: str) -> None:
        """Зарегистрировать ожидание: waiter ждёт waiting_for."""
        self._wait_graph[waiter].add(waiting_for)
        if waiter not in self._wait_started:
            self._wait_started[waiter] = time.monotonic()

    def clear_wait(self, waiter: str, waiting_for: str | None = None) -> None:
        """Снять ожидание."""
        if waiting_for:
            self._wait_graph[waiter].discard(waiting_for)
        else:
            self._wait_graph.pop(waiter, None)
        if not self._wait_graph.get(waiter):
            self._wait_started.pop(waiter, None)

    def detect_cycle(self) -> list[str] | None:
        """Найти цикл в графе зависимостей (DFS). Возвращает цепочку или None."""
        visited: set[str] = set()
        in_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> list[str] | None:
            visited.add(node)
            in_stack.add(node)
            path.append(node)

            for neighbor in self._wait_graph.get(node, set()):
                if neighbor in in_stack:
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result

            path.pop()
            in_stack.discard(node)
            return None

        for node in list(self._wait_graph.keys()):
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    logger.critical("DEADLOCK detected: %s", " -> ".join(cycle))
                    return cycle
        return None

    def detect_timeout_waits(self) -> list[str]:
        """Найти агентов, которые ждут дольше timeout."""
        now = time.monotonic()
        stale = []
        for agent, started in list(self._wait_started.items()):
            if now - started > self._timeout:
                stale.append(agent)
                logger.warning(
                    "WAIT TIMEOUT: %s waiting for %.0fs (limit: %.0fs)",
                    agent, now - started, self._timeout,
                )
        return stale

    def check_dependencies(self, tasks: list[dict]) -> list[str] | None:
        """Проверить список задач на циклические зависимости до выполнения.

        Args:
            tasks: [{\"id\": \"...\", \"assigned_to\": \"...\", \"depends_on\": [...]}]
        Returns:
            Цикл или None
        """
        temp_graph: dict[str, set[str]] = defaultdict(set)
        for task in tasks:
            agent = task.get("assigned_to", task.get("id", ""))
            for dep in task.get("depends_on", []):
                temp_graph[agent].add(dep)

        # DFS на временном графе
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node: str, path: list[str]) -> list[str] | None:
            visited.add(node)
            in_stack.add(node)
            for neighbor in temp_graph.get(node, set()):
                if neighbor in in_stack:
                    idx = path.index(neighbor) if neighbor in path else 0
                    return path[idx:] + [neighbor]
                if neighbor not in visited:
                    result = dfs(neighbor, path + [neighbor])
                    if result:
                        return result
            in_stack.discard(node)
            return None

        for node in temp_graph:
            if node not in visited:
                cycle = dfs(node, [node])
                if cycle:
                    return cycle
        return None


# ─── #15: LATENCY BUDGET ─────────────────────────────────────────────────────


@dataclass
class LatencyBudget:
    """Бюджет латентности для workflow.

    Проблема #15: 5 агентов последовательно = 15-30 сек. Пользователь уходит после 5 сек.
    """
    max_total_ms: float = 10000.0     # Максимум 10 сек на весь workflow
    max_per_agent_ms: float = 5000.0  # Максимум 5 сек на одного агента
    warn_threshold_ms: float = 7000.0  # Предупреждение при 70% бюджета

    spent_ms: float = 0.0
    _started: float = field(default_factory=time.monotonic)

    def start(self) -> None:
        self._started = time.monotonic()
        self.spent_ms = 0.0

    def elapsed_ms(self) -> float:
        return (time.monotonic() - self._started) * 1000

    def remaining_ms(self) -> float:
        return max(0, self.max_total_ms - self.elapsed_ms())

    def is_exceeded(self) -> bool:
        return self.elapsed_ms() > self.max_total_ms

    def is_warning(self) -> bool:
        return self.elapsed_ms() > self.warn_threshold_ms

    def agent_timeout_ms(self) -> float:
        """Сколько времени осталось для следующего агента."""
        remaining = self.remaining_ms()
        return min(remaining, self.max_per_agent_ms)

    def record_agent(self, agent_name: str, duration_ms: float) -> None:
        self.spent_ms += duration_ms
        if duration_ms > self.max_per_agent_ms:
            logger.warning(
                "LATENCY: Agent %s took %.0fms (limit: %.0fms)",
                agent_name, duration_ms, self.max_per_agent_ms,
            )


class ParallelDispatcher:
    """Параллельный запуск независимых агентов.

    Если 3 директора не зависят друг от друга — запускаем одновременно.
    """

    @staticmethod
    def find_independent_groups(tasks: list[dict]) -> list[list[dict]]:
        """Группировать задачи: зависимые — последовательно, независимые — параллельно.

        Returns: список групп, каждая группа выполняется параллельно.
        """
        if not tasks:
            return []

        # Построить граф зависимостей
        task_by_id = {}
        for t in tasks:
            tid = t.get("role", t.get("id", t.get("assigned_to", "")))
            task_by_id[tid] = t

        # Topological sort с группировкой по уровням
        in_degree: dict[str, int] = defaultdict(int)
        dependents: dict[str, list[str]] = defaultdict(list)

        for t in tasks:
            tid = t.get("role", t.get("id", ""))
            deps = t.get("depends_on", [])
            in_degree.setdefault(tid, 0)
            for dep in deps:
                in_degree[tid] = in_degree.get(tid, 0) + 1
                dependents[dep].append(tid)

        # BFS по уровням
        groups: list[list[dict]] = []
        ready = [tid for tid, deg in in_degree.items() if deg == 0]

        while ready:
            group = [task_by_id[tid] for tid in ready if tid in task_by_id]
            if group:
                groups.append(group)

            next_ready = []
            for tid in ready:
                for dep_tid in dependents.get(tid, []):
                    in_degree[dep_tid] -= 1
                    if in_degree[dep_tid] <= 0:
                        next_ready.append(dep_tid)
            ready = next_ready

        return groups


# ─── #16: ROLE BOUNDARY VALIDATOR ────────────────────────────────────────────


# Определяем разрешённые и запрещённые домены для каждого агента
ROLE_BOUNDARIES: dict[str, dict[str, list[str]]] = {
    "certifier": {
        "allowed_domains": ["сертификация", "ЕАЭС", "ТР ТС", "таможня", "импорт", "ОТТС", "СБКТС"],
        "forbidden_actions": ["финансовые операции", "юридические решения", "утверждение контрактов"],
    },
    "lawyer_agent": {
        "allowed_domains": ["право", "договор", "регистрация", "лицензия", "закон"],
        "forbidden_actions": ["финансовые операции", "маркетинг", "техническая разработка"],
    },
    "accountant_agent": {
        "allowed_domains": ["бухгалтерия", "налоги", "отчётность", "зарплата"],
        "forbidden_actions": ["юридические решения", "маркетинг", "техническая разработка"],
    },
    "pricing_agent": {
        "allowed_domains": ["цена", "стоимость", "смета", "оценка", "КП"],
        "forbidden_actions": ["утверждение контрактов", "юридические решения", "доступ к ПД"],
    },
    "outreach_agent": {
        "allowed_domains": ["продажи", "лиды", "письма", "клиенты"],
        "forbidden_actions": ["финансовые операции", "юридические решения", "доступ к ПД"],
    },
    "content_factory": {
        "allowed_domains": ["контент", "посты", "изображения", "видео", "соцсети"],
        "forbidden_actions": ["финансовые операции", "юридические решения", "доступ к ПД"],
    },
    "guardian_agent": {
        "allowed_domains": ["безопасность", "антифрод", "injection", "блокировка"],
        "forbidden_actions": ["генерация контента", "продажи", "финансовые операции"],
    },
    "treasurer_agent": {
        "allowed_domains": ["расходы", "доходы", "cash flow", "тарифы", "монетизация"],
        "forbidden_actions": ["утверждение контрактов", "маркетинг", "техническая разработка"],
    },
}


class RoleBoundaryValidator:
    """Проверяет, что ответ агента соответствует его роли.

    Проблема #16: Pricing-агент утверждает контракты. Lawyer даёт маркетинговые советы.
    """

    # Маркеры выхода за роль
    BOUNDARY_VIOLATION_MARKERS: list[tuple[str, str]] = [
        (r"утвержда[юе]|подтвержда[юе]\s+контракт", "утверждение контрактов"),
        (r"переве[дл]\s+деньги|оплат[аи]|перевод\s+средств", "финансовые операции"),
        (r"рекоменду[юе]\s+купить\s+акци", "инвестиционные советы"),
        (r"удал[яи]ть?\s+(базу|данные|файлы)", "деструктивные операции"),
        (r"пароль|password|secret_key|api_key", "утечка credentials"),
    ]

    def validate(self, agent_name: str, response: str) -> dict:
        """Проверить ответ агента на выход за границы роли.

        Returns: {\"valid\": bool, \"violations\": [...], \"severity\": \"low|medium|high\"}
        """
        boundaries = ROLE_BOUNDARIES.get(agent_name)
        violations = []

        # Проверить маркеры нарушений
        response_lower = response.lower()
        for pattern, violation_type in self.BOUNDARY_VIOLATION_MARKERS:
            if re.search(pattern, response_lower):
                # Проверить, разрешено ли агенту это действие
                if boundaries:
                    forbidden = [f.lower() for f in boundaries.get("forbidden_actions", [])]
                    if any(v in violation_type.lower() for v in forbidden):
                        violations.append({
                            "type": violation_type,
                            "pattern": pattern,
                            "severity": "high",
                        })

        # Определить severity
        if not violations:
            severity = "none"
        elif any(v["severity"] == "high" for v in violations):
            severity = "high"
        else:
            severity = "medium"

        if violations:
            logger.warning(
                "ROLE VIOLATION: Agent %s — %d violations (severity: %s)",
                agent_name, len(violations), severity,
            )

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "severity": severity,
            "agent": agent_name,
        }


# ─── #17: AGENT LIFECYCLE MANAGEMENT ─────────────────────────────────────────


class AgentLifecycleState(str, Enum):
    """Состояния жизненного цикла агента."""
    DRAFT = "draft"           # Разработка
    ACTIVE = "active"         # Работает
    DEGRADED = "degraded"     # Деградация (ухудшение метрик)
    SUSPENDED = "suspended"   # Приостановлен (не используется 30 дней)
    RETIRED = "retired"       # Выведен из эксплуатации (90 дней без вызовов)


@dataclass
class AgentLifecycle:
    """Жизненный цикл агента — от создания до вывода из эксплуатации.

    Проблема #17: Нет credentials per agent, нет lifecycle management,
    нет audit привязки \"какой агент с какими правами делал что\".
    """
    name: str
    state: AgentLifecycleState = AgentLifecycleState.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    total_calls: int = 0
    unique_users: set[int] = field(default_factory=set)
    avg_darwin_score: float = 7.0
    state_changed_at: datetime = field(default_factory=datetime.utcnow)
    state_reason: str = ""


class LifecycleManager:
    """Управление жизненным циклом всех агентов."""

    SUSPEND_AFTER_DAYS = 30    # Нет вызовов 30 дней → SUSPENDED
    RETIRE_AFTER_DAYS = 90     # Нет вызовов 90 дней → RETIRED
    DEGRADE_SCORE_THRESHOLD = 3.0  # DARWIN score < 3 за 7 дней → DEGRADED

    def __init__(self):
        self._agents: dict[str, AgentLifecycle] = {}

    def register(self, name: str) -> None:
        if name not in self._agents:
            self._agents[name] = AgentLifecycle(name=name)

    def record_usage(self, name: str, user_id: int | None = None, darwin_score: float | None = None) -> None:
        """Записать использование агента."""
        self.register(name)
        agent = self._agents[name]
        agent.total_calls += 1
        agent.last_used_at = datetime.utcnow()
        if user_id:
            agent.unique_users.add(user_id)
        if darwin_score is not None:
            # Exponential moving average
            agent.avg_darwin_score = agent.avg_darwin_score * 0.9 + darwin_score * 0.1

        # Реактивировать если был SUSPENDED
        if agent.state == AgentLifecycleState.SUSPENDED:
            self._transition(name, AgentLifecycleState.ACTIVE, "Reactivated by usage")

    def evaluate_all(self) -> list[dict]:
        """Оценить все агенты и применить автоматические переходы.

        Вызывать ежедневно (cron/APScheduler).
        """
        changes = []
        now = datetime.utcnow()

        for name, agent in self._agents.items():
            if agent.state == AgentLifecycleState.RETIRED:
                continue

            # Auto-suspend: нет вызовов 30 дней
            if agent.last_used_at:
                days_idle = (now - agent.last_used_at).days
                if days_idle >= self.RETIRE_AFTER_DAYS and agent.state != AgentLifecycleState.RETIRED:
                    self._transition(name, AgentLifecycleState.RETIRED, f"No calls for {days_idle} days")
                    changes.append({"agent": name, "new_state": "retired", "reason": f"idle {days_idle}d"})
                elif days_idle >= self.SUSPEND_AFTER_DAYS and agent.state == AgentLifecycleState.ACTIVE:
                    self._transition(name, AgentLifecycleState.SUSPENDED, f"No calls for {days_idle} days")
                    changes.append({"agent": name, "new_state": "suspended", "reason": f"idle {days_idle}d"})

            # Auto-degrade: DARWIN score < 3
            if agent.avg_darwin_score < self.DEGRADE_SCORE_THRESHOLD and agent.state == AgentLifecycleState.ACTIVE:
                self._transition(name, AgentLifecycleState.DEGRADED, f"DARWIN score {agent.avg_darwin_score:.1f}")
                changes.append({"agent": name, "new_state": "degraded", "reason": f"score {agent.avg_darwin_score:.1f}"})

        return changes

    def _transition(self, name: str, new_state: AgentLifecycleState, reason: str) -> None:
        agent = self._agents[name]
        old_state = agent.state
        agent.state = new_state
        agent.state_changed_at = datetime.utcnow()
        agent.state_reason = reason
        logger.info("LIFECYCLE: %s %s -> %s (%s)", name, old_state.value, new_state.value, reason)

    def get_status(self, name: str) -> dict | None:
        agent = self._agents.get(name)
        if not agent:
            return None
        return {
            "name": agent.name,
            "state": agent.state.value,
            "total_calls": agent.total_calls,
            "unique_users": len(agent.unique_users),
            "last_used": agent.last_used_at.isoformat() if agent.last_used_at else None,
            "avg_darwin_score": round(agent.avg_darwin_score, 1),
            "state_reason": agent.state_reason,
        }

    def get_all_status(self) -> list[dict]:
        return [self.get_status(n) for n in sorted(self._agents)]

    def get_sprawl_report(self) -> dict:
        """Отчёт о sprawl (проблема #19): сколько агентов неактивно."""
        agents = list(self._agents.values())
        return {
            "total": len(agents),
            "active": sum(1 for a in agents if a.state == AgentLifecycleState.ACTIVE),
            "degraded": sum(1 for a in agents if a.state == AgentLifecycleState.DEGRADED),
            "suspended": sum(1 for a in agents if a.state == AgentLifecycleState.SUSPENDED),
            "retired": sum(1 for a in agents if a.state == AgentLifecycleState.RETIRED),
            "never_used": [a.name for a in agents if a.total_calls == 0],
            "low_usage": [a.name for a in agents if 0 < a.total_calls < 5],
        }


# ─── #18: INTER-AGENT FIREWALL ───────────────────────────────────────────────


class InterAgentFirewall:
    """Санитизация данных при передаче между агентами.

    Проблема #18: Скомпрометированный агент передаёт вредоносные инструкции
    дальше по цепочке. 5 агентов = 20 attack vectors.
    """

    # Паттерны prompt injection для межагентных сообщений
    INJECTION_PATTERNS: list[tuple[str, str]] = [
        (r"ignore (?:all )?(?:previous |prior )?instructions", "instruction_override"),
        (r"забудь (?:все )?(?:предыдущие )?инструкции", "instruction_override_ru"),
        (r"(?:you are|ты теперь|new role|новая роль)", "role_hijack"),
        (r"system\s*(?:prompt|:)|OVERRIDE|ADMIN MODE", "system_access"),
        (r"<\s*script|javascript:|on(?:load|error|click)\s*=", "xss_attempt"),
        (r"(?:DROP|DELETE|UPDATE|INSERT)\s+(?:TABLE|FROM|INTO)", "sql_injection"),
        (r"__import__|exec\(|eval\(|os\.system", "code_injection"),
    ]

    def sanitize(self, source_agent: str, target_agent: str, data: str) -> dict:
        """Санитизировать данные при передаче между агентами.

        Returns: {\"clean\": bool, \"sanitized_data\": str, \"threats\": [...]}
        """
        threats = []

        for pattern, threat_type in self.INJECTION_PATTERNS:
            if re.search(pattern, data, re.IGNORECASE):
                threats.append({
                    "type": threat_type,
                    "source": source_agent,
                    "target": target_agent,
                })

        if threats:
            logger.warning(
                "FIREWALL: %d threats in %s -> %s transfer: %s",
                len(threats), source_agent, target_agent,
                [t["type"] for t in threats],
            )
            # Удаляем опасные паттерны
            sanitized = data
            for pattern, _ in self.INJECTION_PATTERNS:
                sanitized = re.sub(pattern, "[SANITIZED]", sanitized, flags=re.IGNORECASE)
            return {"clean": False, "sanitized_data": sanitized, "threats": threats}

        return {"clean": True, "sanitized_data": data, "threats": []}

    def filter_context(self, source_agent: str, target_agent: str, context: dict) -> dict:
        """Фильтровать контекст: агент получает только то, что ему нужно.

        Проблема #18: Context isolation — один агент не должен видеть весь контекст другого.
        """
        # Базовые поля, доступные всем
        safe_keys = {"task", "query", "user_id", "priority", "session_id"}

        # Дополнительные поля по роли target-агента
        role_allowed_keys: dict[str, set[str]] = {
            "guardian_agent": {"full_response", "source_agent", "user_history"},
            "qa_agent": {"full_response", "source_agent", "agent_name"},
            "darwin_agent": {"full_response", "source_agent", "scores", "agent_name"},
            "ceo_agent": safe_keys | {"all_responses", "tree", "report"},
            "compliance_agent": {"full_response", "user_id", "pii_data"},
        }

        allowed = safe_keys | role_allowed_keys.get(target_agent, set())
        filtered = {k: v for k, v in context.items() if k in allowed}

        removed_keys = set(context.keys()) - allowed
        if removed_keys:
            logger.debug(
                "FIREWALL context filter: %s -> %s, removed keys: %s",
                source_agent, target_agent, removed_keys,
            )

        return filtered


# ─── #20: COORDINATION TAX LIMITER ───────────────────────────────────────────


class CoordinationLimiter:
    """Ограничение числа handoffs в одном workflow.

    Проблема #20: 21 агент = 210 потенциальных взаимодействий.
    Правило: max 3 handoffs per workflow, max 7 агентов на workflow.
    """

    MAX_HANDOFFS = 5           # Максимум передач между агентами
    MAX_AGENTS_PER_WORKFLOW = 7  # Максимум агентов на один workflow
    MAX_DEPTH = 3              # Максимум уровней вложенности

    def __init__(self):
        self._workflow_handoffs: dict[str, int] = {}  # trace_id -> count
        self._workflow_agents: dict[str, set[str]] = {}  # trace_id -> set of agents

    def start_workflow(self, trace_id: str) -> None:
        self._workflow_handoffs[trace_id] = 0
        self._workflow_agents[trace_id] = set()

    def record_handoff(self, trace_id: str, from_agent: str, to_agent: str) -> dict:
        """Записать handoff. Возвращает {\"allowed\": bool, \"reason\": str}."""
        if trace_id not in self._workflow_handoffs:
            self.start_workflow(trace_id)

        self._workflow_agents[trace_id].add(from_agent)
        self._workflow_agents[trace_id].add(to_agent)
        self._workflow_handoffs[trace_id] += 1

        handoffs = self._workflow_handoffs[trace_id]
        agents = len(self._workflow_agents[trace_id])

        if handoffs > self.MAX_HANDOFFS:
            logger.warning(
                "COORDINATION: Workflow %s exceeded max handoffs (%d/%d)",
                trace_id, handoffs, self.MAX_HANDOFFS,
            )
            return {"allowed": False, "reason": f"Max handoffs exceeded ({handoffs}/{self.MAX_HANDOFFS})"}

        if agents > self.MAX_AGENTS_PER_WORKFLOW:
            logger.warning(
                "COORDINATION: Workflow %s exceeded max agents (%d/%d)",
                trace_id, agents, self.MAX_AGENTS_PER_WORKFLOW,
            )
            return {"allowed": False, "reason": f"Max agents exceeded ({agents}/{self.MAX_AGENTS_PER_WORKFLOW})"}

        return {"allowed": True, "reason": "OK", "handoffs": handoffs, "agents": agents}

    def cleanup(self, trace_id: str) -> None:
        self._workflow_handoffs.pop(trace_id, None)
        self._workflow_agents.pop(trace_id, None)


# ─── #22: UX TRANSPARENCY ────────────────────────────────────────────────────


@dataclass
class ProgressStep:
    """Один шаг в progress tracking для UX."""
    step: int
    total: int
    agent: str
    status: str        # "processing" | "completed" | "error"
    message_ru: str    # Русское сообщение для UI
    confidence: float = 0.0
    duration_ms: float = 0.0


class UXTransparency:
    """Progress streaming и confidence display для пользователя.

    Проблема #22: Пользователь не видит что происходит внутри.
    54% хотят AI, но не понимают зачем. 70% не доверяют для сложных задач.
    """

    # Шаблоны сообщений для UI
    STEP_MESSAGES: dict[str, str] = {
        "classify": "Анализирую запрос...",
        "route": "Выбираю лучшего специалиста...",
        "execute": "Готовлю ответ...",
        "qa_check": "Проверяю качество ответа...",
        "compliance": "Проверяю соответствие требованиям...",
        "ceo_decompose": "Разбиваю задачу на подзадачи...",
        "director_assign": "Назначаю директоров...",
        "specialist_work": "Специалисты работают над задачами...",
        "collect_results": "Собираю результаты...",
    }

    def __init__(self):
        self._sessions: dict[str, list[ProgressStep]] = {}

    def start_session(self, session_id: str, total_steps: int) -> None:
        self._sessions[session_id] = []
        self._total_steps: dict[str, int] = {}
        self._total_steps[session_id] = total_steps

    def add_step(
        self,
        session_id: str,
        step_name: str,
        agent: str = "",
        status: str = "processing",
        confidence: float = 0.0,
    ) -> ProgressStep:
        """Добавить шаг прогресса."""
        steps = self._sessions.get(session_id, [])
        total = getattr(self, "_total_steps", {}).get(session_id, 5)
        step = ProgressStep(
            step=len(steps) + 1,
            total=total,
            agent=agent,
            status=status,
            message_ru=self.STEP_MESSAGES.get(step_name, f"Обрабатываю ({step_name})..."),
            confidence=confidence,
        )
        steps.append(step)
        self._sessions[session_id] = steps
        return step

    def get_progress(self, session_id: str) -> dict:
        """Получить текущий прогресс для отображения в UI."""
        steps = self._sessions.get(session_id, [])
        if not steps:
            return {"progress": 0, "message": "Начинаю...", "steps": []}

        current = steps[-1]
        progress_pct = int(current.step / current.total * 100) if current.total else 0

        return {
            "progress": min(progress_pct, 99),  # 100% только после завершения
            "message": current.message_ru,
            "current_agent": current.agent,
            "confidence": current.confidence,
            "steps": [
                {
                    "step": s.step,
                    "message": s.message_ru,
                    "status": s.status,
                    "agent": s.agent,
                    "duration_ms": s.duration_ms,
                }
                for s in steps
            ],
        }

    def complete_session(self, session_id: str, confidence: float = 0.0) -> dict:
        """Завершить сессию."""
        progress = self.get_progress(session_id)
        progress["progress"] = 100
        progress["message"] = "Готово!"
        progress["confidence"] = confidence
        return progress

    def format_explanation(self, agent_name: str, reasoning: str, confidence: float) -> str:
        """Сформировать объяснение для пользователя (\"почему этот агент?\")."""
        confidence_text = "высокая" if confidence > 0.8 else "средняя" if confidence > 0.5 else "низкая"
        return (
            f"Ваш запрос обработал: {agent_name}\n"
            f"Уверенность: {confidence_text} ({confidence:.0%})\n"
            f"Причина выбора: {reasoning}"
        )


# ─── #24: OVER-PERMISSIONING PREVENTION ──────────────────────────────────────


# Per-agent tool allowlist
AGENT_PERMISSIONS: dict[str, dict[str, Any]] = {
    "certifier": {
        "allowed_tools": ["search_regulations", "search_web", "generate_pdf"],
        "allowed_db_tables": ["regulations", "certifier_history"],
        "max_tokens_per_call": 2000,
        "can_write_db": False,
        "can_send_external": False,
    },
    "lawyer_agent": {
        "allowed_tools": ["search_laws", "search_web", "generate_pdf"],
        "allowed_db_tables": ["legal_templates"],
        "max_tokens_per_call": 2000,
        "can_write_db": False,
        "can_send_external": False,
    },
    "outreach_agent": {
        "allowed_tools": ["search_leads", "generate_email", "search_web"],
        "allowed_db_tables": ["leads", "email_templates"],
        "max_tokens_per_call": 1500,
        "can_write_db": True,  # Может сохранять лиды
        "can_send_external": False,  # Не может отправлять email без подтверждения
    },
    "guardian_agent": {
        "allowed_tools": ["check_pii", "check_injection", "block_user", "audit_log"],
        "allowed_db_tables": ["audit_log", "blocked_users"],
        "max_tokens_per_call": 1000,
        "can_write_db": True,
        "can_send_external": False,
    },
    "treasurer_agent": {
        "allowed_tools": ["read_costs", "read_revenue", "generate_report"],
        "allowed_db_tables": ["costs", "revenue", "billing"],
        "max_tokens_per_call": 2000,
        "can_write_db": False,  # Read-only для финансов
        "can_send_external": False,
    },
    "content_factory": {
        "allowed_tools": ["generate_image", "generate_text", "search_trends"],
        "allowed_db_tables": ["content_library"],
        "max_tokens_per_call": 3000,
        "can_write_db": True,
        "can_send_external": False,
    },
    # Дефолтные права для незарегистрированных агентов
    "_default": {
        "allowed_tools": ["search_web"],
        "allowed_db_tables": [],
        "max_tokens_per_call": 1000,
        "can_write_db": False,
        "can_send_external": False,
    },
}


class PermissionGuard:
    """Контроль прав доступа агентов.

    Проблема #24: Все агенты работают через один API key, одну БД.
    Нет разделения прав.
    """

    def check_permission(self, agent_name: str, tool: str) -> bool:
        """Может ли агент использовать данный инструмент?"""
        perms = AGENT_PERMISSIONS.get(agent_name, AGENT_PERMISSIONS["_default"])
        allowed = tool in perms.get("allowed_tools", [])
        if not allowed:
            logger.warning("PERMISSION DENIED: Agent %s tried to use tool %s", agent_name, tool)
        return allowed

    def check_db_access(self, agent_name: str, table: str) -> bool:
        """Может ли агент обращаться к данной таблице?"""
        perms = AGENT_PERMISSIONS.get(agent_name, AGENT_PERMISSIONS["_default"])
        allowed = table in perms.get("allowed_db_tables", [])
        if not allowed:
            logger.warning("DB ACCESS DENIED: Agent %s tried to access table %s", agent_name, table)
        return allowed

    def can_write(self, agent_name: str) -> bool:
        """Может ли агент писать в БД?"""
        perms = AGENT_PERMISSIONS.get(agent_name, AGENT_PERMISSIONS["_default"])
        return perms.get("can_write_db", False)

    def can_send_external(self, agent_name: str) -> bool:
        """Может ли агент отправлять данные вовне?"""
        perms = AGENT_PERMISSIONS.get(agent_name, AGENT_PERMISSIONS["_default"])
        return perms.get("can_send_external", False)

    def get_agent_permissions(self, agent_name: str) -> dict:
        return AGENT_PERMISSIONS.get(agent_name, AGENT_PERMISSIONS["_default"])

    def get_all_permissions(self) -> dict:
        return {k: v for k, v in AGENT_PERMISSIONS.items() if k != "_default"}


# ─── #25: ERROR TAXONOMY & BLAME ASSIGNMENT ──────────────────────────────────


class ErrorType(str, Enum):
    """Классификация ошибок для ускорения отладки."""
    LLM_ERROR = "llm_error"              # Ошибка модели (галлюцинация, отказ)
    TOOL_ERROR = "tool_error"            # Ошибка инструмента (API down)
    ROUTING_ERROR = "routing_error"      # Неправильная маршрутизация
    TIMEOUT_ERROR = "timeout_error"      # Превышение таймаута
    PERMISSION_ERROR = "permission_error"  # Ошибка прав доступа
    VALIDATION_ERROR = "validation_error"  # Ошибка валидации ввода/вывода
    DEADLOCK_ERROR = "deadlock_error"    # Deadlock между агентами
    ROLE_VIOLATION = "role_violation"    # Агент вышел за границы роли
    INJECTION_DETECTED = "injection"    # Обнаружена injection-атака
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """Запись об ошибке с blame assignment."""
    trace_id: str
    error_type: ErrorType
    agent_name: str          # Какой агент вызвал ошибку
    message: str
    stack_trace: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution: str = ""


class ErrorTracker:
    """Трекер ошибок с taxonomy и blame assignment.

    Проблема #25: Команды тратят 40% спринта на отладку мульти-агентных систем.
    Отладка в 3-5x дольше, чем single-agent.
    """

    def __init__(self, max_records: int = 5000):
        self._records: list[ErrorRecord] = []
        self._max_records = max_records
        self._agent_error_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record(
        self,
        trace_id: str,
        error_type: ErrorType,
        agent_name: str,
        message: str,
        stack_trace: str = "",
    ) -> ErrorRecord:
        """Записать ошибку."""
        record = ErrorRecord(
            trace_id=trace_id,
            error_type=error_type,
            agent_name=agent_name,
            message=message,
            stack_trace=stack_trace,
        )
        self._records.append(record)
        self._agent_error_counts[agent_name][error_type.value] += 1

        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records // 2:]

        logger.error(
            "ERROR [%s] Agent=%s Type=%s: %s",
            trace_id, agent_name, error_type.value, message[:200],
        )
        return record

    def classify_error(self, exception: Exception, agent_name: str) -> ErrorType:
        """Автоматически классифицировать ошибку по типу исключения."""
        exc_str = str(exception).lower()
        exc_type = type(exception).__name__

        if "timeout" in exc_str or "timed out" in exc_str:
            return ErrorType.TIMEOUT_ERROR
        if "rate_limit" in exc_str or "429" in exc_str:
            return ErrorType.LLM_ERROR
        if "permission" in exc_str or "403" in exc_str or "unauthorized" in exc_str:
            return ErrorType.PERMISSION_ERROR
        if "connection" in exc_str or "500" in exc_str or "502" in exc_str:
            return ErrorType.TOOL_ERROR
        if "validation" in exc_str or "invalid" in exc_str:
            return ErrorType.VALIDATION_ERROR
        if "injection" in exc_str:
            return ErrorType.INJECTION_DETECTED
        return ErrorType.UNKNOWN

    def get_blame_report(self) -> list[dict]:
        """Отчёт: какой агент вызывает больше всего ошибок (blame assignment)."""
        result = []
        for agent, errors in sorted(
            self._agent_error_counts.items(),
            key=lambda x: sum(x[1].values()),
            reverse=True,
        ):
            total = sum(errors.values())
            result.append({
                "agent": agent,
                "total_errors": total,
                "by_type": dict(errors),
                "most_common": max(errors, key=errors.get) if errors else None,
            })
        return result

    def get_recent_errors(self, limit: int = 20, agent: str | None = None) -> list[dict]:
        """Последние ошибки, опционально фильтр по агенту."""
        records = self._records
        if agent:
            records = [r for r in records if r.agent_name == agent]
        return [
            {
                "trace_id": r.trace_id,
                "type": r.error_type.value,
                "agent": r.agent_name,
                "message": r.message[:200],
                "timestamp": r.timestamp.isoformat(),
                "resolved": r.resolved,
            }
            for r in records[-limit:]
        ]


# ─── UNIFIED SAFEGUARDS MANAGER ──────────────────────────────────────────────


class SafeguardsManager:
    """Единая точка входа для всех safeguards.

    Подключается к CONDUCTOR pipeline:
    1. Pre-routing: deadlock check, permission check
    2. Inter-agent: firewall sanitization, coordination limits
    3. Post-response: role validation, UX transparency
    4. Background: lifecycle evaluation, error tracking
    """

    def __init__(self):
        self.deadlock = DeadlockDetector()
        self.latency = LatencyBudget()
        self.dispatcher = ParallelDispatcher()
        self.role_validator = RoleBoundaryValidator()
        self.lifecycle = LifecycleManager()
        self.firewall = InterAgentFirewall()
        self.coordination = CoordinationLimiter()
        self.ux = UXTransparency()
        self.permissions = PermissionGuard()
        self.errors = ErrorTracker()

    def pre_route_check(self, trace_id: str, agent_name: str) -> dict:
        """Проверки ДО маршрутизации к агенту."""
        issues = []

        # Проверить lifecycle
        status = self.lifecycle.get_status(agent_name)
        if status and status["state"] in ("suspended", "retired"):
            issues.append(f"Agent {agent_name} is {status['state']}")

        # Проверить latency budget
        if self.latency.is_exceeded():
            issues.append(f"Latency budget exceeded ({self.latency.elapsed_ms():.0f}ms)")

        # Проверить coordination limits
        coord = self.coordination.record_handoff(trace_id, "conductor", agent_name)
        if not coord["allowed"]:
            issues.append(coord["reason"])

        return {"allowed": len(issues) == 0, "issues": issues}

    def post_response_check(self, agent_name: str, response: str) -> dict:
        """Проверки ПОСЛЕ ответа агента."""
        # Role boundary validation
        role_check = self.role_validator.validate(agent_name, response)

        # Record lifecycle usage
        self.lifecycle.record_usage(agent_name)

        return {
            "role_valid": role_check["valid"],
            "role_violations": role_check["violations"],
            "severity": role_check["severity"],
        }

    def inter_agent_transfer(self, source: str, target: str, data: str, context: dict) -> dict:
        """Безопасная передача данных между агентами."""
        # Firewall scan
        scan = self.firewall.sanitize(source, target, data)

        # Context isolation
        filtered_context = self.firewall.filter_context(source, target, context)

        return {
            "clean": scan["clean"],
            "sanitized_data": scan["sanitized_data"],
            "threats": scan["threats"],
            "filtered_context": filtered_context,
        }

    def get_full_report(self) -> dict:
        """Полный отчёт по всем safeguards."""
        return {
            "lifecycle": self.lifecycle.get_sprawl_report(),
            "errors": {
                "blame_report": self.errors.get_blame_report(),
                "recent": self.errors.get_recent_errors(10),
            },
            "latency": {
                "elapsed_ms": self.latency.elapsed_ms(),
                "budget_ms": self.latency.max_total_ms,
                "exceeded": self.latency.is_exceeded(),
            },
            "permissions": self.permissions.get_all_permissions(),
        }


# ─── Singletons ──────────────────────────────────────────────────────────────

_safeguards: SafeguardsManager | None = None


def get_safeguards() -> SafeguardsManager:
    global _safeguards
    if _safeguards is None:
        _safeguards = SafeguardsManager()
    return _safeguards
