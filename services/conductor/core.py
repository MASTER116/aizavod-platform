"""CONDUCTOR core — основная логика оркестрации."""

from __future__ import annotations

import logging
import time

from services.conductor.schemas import (
    AgentInfo,
    RouteDecision,
    ConductorResult,
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
from services.conductor.routes import ROUTE_HANDLERS
from services.conductor.llm_client import get_llm_client

logger = logging.getLogger("aizavod.conductor")


class Conductor:
    """Главный маршрутизатор запросов AI Zavod."""

    def __init__(self) -> None:
        self._llm = get_llm_client()

    def _agents_list_text(self) -> str:
        lines = []
        for a in AGENTS:
            lines.append(f"- {a.name} [{a.department}]: {a.description}")
        return "\n".join(lines)

    async def _classify(self, query: str) -> RouteDecision:
        """Классифицировать запрос — сначала по ключевым словам, потом через LLM."""
        query_lower = query.lower()
        scores: dict[str, int] = {}
        for agent in AGENTS:
            score = sum(1 for kw in agent.keywords if kw in query_lower)
            if score > 0:
                scores[agent.name] = score

        if scores:
            best = max(scores, key=scores.get)
            best_score = scores[best]
            if best_score >= 1:
                return RouteDecision(
                    agent=best,
                    confidence=min(0.85 + best_score * 0.05, 0.95),
                    reasoning=f"Ключевые слова совпали ({best_score} совпадений)",
                    reformulated_query=query,
                )

        # LLM-классификация
        prompt = CLASSIFIER_PROMPT.format(
            agents_list=self._agents_list_text(),
            query=query,
        )

        text = await self._llm.call(prompt, max_tokens=500, temperature=0.1, caller="conductor_classify")
        data = self._llm.parse_json(text)

        if data and isinstance(data, dict):
            return RouteDecision(
                agent=data.get("agent", "ceo_agent"),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                reformulated_query=data.get("reformulated_query", query),
                multi_agent=data.get("multi_agent", False),
                secondary_agents=data.get("secondary_agents", []),
            )

        logger.warning("Не удалось распарсить ответ классификатора: %s", text[:200])
        text_lower = text.lower()
        for agent in AGENTS:
            if agent.name in text_lower:
                return RouteDecision(
                    agent=agent.name,
                    confidence=0.5,
                    reasoning="Извлечено из текста ответа",
                    reformulated_query=query,
                )
        return RouteDecision(
            agent="ceo_agent",
            confidence=0.3,
            reasoning="Не удалось классифицировать, фоллбэк в CEO",
            reformulated_query=query,
        )

    def _detect_mode(self, query: str) -> str:
        """Определить режим: 'router' (вопрос) или 'orchestrator' (задача)."""
        q = query.lower().strip()
        for kw in TASK_KEYWORDS:
            if q.startswith(kw) or f" {kw} " in f" {q} ":
                return "orchestrator"
        for kw in QUESTION_KEYWORDS:
            if q.startswith(kw):
                return "router"
        return "router"

    async def _department_decompose(
        self, task: str, director_code: str, department_code: str
    ) -> list[dict]:
        """Отдел разбивает задачу на задачи для специалистов (3-й уровень)."""
        full_dept_code = f"{director_code}.{department_code}"
        specialists = DEPARTMENT_SPECIALISTS.get(full_dept_code, [])
        if not specialists:
            logger.warning("Нет специалистов для %s", full_dept_code)
            return []

        director = DIRECTORS.get(director_code, {})
        specialists_text = "\n".join(
            f"- {s['code']}: {s['title']}" for s in specialists
        )

        prompt = DEPARTMENT_DECOMPOSE_PROMPT.format(
            department_title=full_dept_code,
            director_title=director.get("title", director_code),
            specialists_list=specialists_text,
            task=task,
        )

        response = await self._llm.call(prompt, max_tokens=1500, caller="conductor_dept")
        data = self._llm.parse_json(response)
        if data and "tasks" in data:
            return data["tasks"]
        return []

    async def _collect_results(self, original_task: str, tree: dict) -> dict:
        """Собрать результаты со всех уровней."""
        results_lines = []
        total = 0
        completed = 0

        for d in tree.get("directors", []):
            results_lines.append(f"\n## {d.get('title', d.get('role', '?'))}")
            results_lines.append(f"Задача: {d.get('task', '?')}")
            for dept in d.get("departments", []):
                dept_name = dept.get("department", "?")
                results_lines.append(f"  ### Отдел: {dept_name}")
                results_lines.append(f"  Задача: {dept.get('task', '?')}")
                for spec in dept.get("specialists", []):
                    total += 1
                    status = spec.get("status", "pending")
                    if status == "completed":
                        completed += 1
                    results_lines.append(
                        f"    - [{status}] {spec.get('specialist', '?')}: "
                        f"{spec.get('task', '?')}"
                    )

        results_text = "\n".join(results_lines)
        prompt = COLLECT_RESULTS_PROMPT.format(
            original_task=original_task,
            results_tree=results_text,
        )
        response = await self._llm.call(prompt, max_tokens=1000, caller="conductor_collect")
        data = self._llm.parse_json(response)

        if data:
            data["completed_count"] = completed
            data["total_count"] = total
            return data

        return {
            "summary": f"Декомпозиция завершена: {completed}/{total} задач",
            "status": "completed" if completed == total else "partial",
            "completed_count": completed,
            "total_count": total,
            "highlights": [],
            "issues": [],
            "next_steps": [],
        }

    async def orchestrate(self, task: str, depth: int = 3) -> dict:
        """Полная оркестрация: CEO -> директора -> отделы -> специалисты."""
        start = time.monotonic()
        logger.info("ORCHESTRATOR: начинаю декомпозицию (depth=%d): '%s'", depth, task[:100])

        # Шаг 1: CEO-декомпозиция
        directors_text = "\n".join(
            f"- {code}: {d['title']} — {d['scope']}"
            for code, d in DIRECTORS.items()
        )
        ceo_prompt = CEO_DECOMPOSE_PROMPT.format(
            directors_list=directors_text,
            task=task,
        )
        ceo_response = await self._llm.call(ceo_prompt, caller="conductor_ceo")
        ceo_data = self._llm.parse_json(ceo_response)

        if not ceo_data or "directors" not in ceo_data:
            return {
                "status": "error",
                "message": "CEO не смог декомпозировать задачу",
                "raw": ceo_response[:500],
            }

        analysis = ceo_data.get("analysis", "")
        director_tasks = ceo_data["directors"]
        logger.info("CEO: %d директоров задействовано", len(director_tasks))

        # Шаг 2: Директорская декомпозиция
        full_tree = {
            "task": task,
            "analysis": analysis,
            "directors": [],
            "duration_ms": 0,
            "depth": depth,
        }

        for dt in director_tasks:
            role = dt.get("role", "cto")
            director = DIRECTORS.get(role)
            if not director:
                continue

            dept_list = "\n".join(f"- {d}" for d in director["departments"])
            dir_prompt = DIRECTOR_DECOMPOSE_PROMPT.format(
                director_title=director["title"],
                departments_list=dept_list,
                task=dt["task"],
            )
            dir_response = await self._llm.call(dir_prompt, max_tokens=1500, caller="conductor_dir")
            dir_data = self._llm.parse_json(dir_response)

            dept_tasks = []
            if dir_data and "tasks" in dir_data:
                dept_tasks = dir_data["tasks"]

            # Шаг 3: Отдельская декомпозиция
            if depth >= 3:
                for dept in dept_tasks:
                    dept_code = dept.get("department", "")
                    specialist_tasks = await self._department_decompose(
                        dept.get("task", ""), role, dept_code,
                    )
                    dept["specialists"] = specialist_tasks

            director_node = {
                "role": role,
                "title": director["title"],
                "task": dt["task"],
                "priority": dt.get("priority", "normal"),
                "estimated_hours": dt.get("estimated_hours", 0),
                "deliverables": dt.get("deliverables", []),
                "depends_on": dt.get("depends_on", []),
                "departments": dept_tasks,
            }
            full_tree["directors"].append(director_node)

        # Шаг 4: Сборка отчёта
        report = await self._collect_results(task, full_tree)
        full_tree["report"] = report
        full_tree["duration_ms"] = (time.monotonic() - start) * 1000
        return full_tree

    async def process(self, query: str) -> ConductorResult:
        """Главный метод: классифицировать -> маршрутизировать -> вернуть результат."""
        start = time.monotonic()

        # 1. Классификация
        route = await self._classify(query)
        logger.info(
            "CONDUCTOR: '%s' -> %s (confidence=%.2f)",
            query[:80], route.agent, route.confidence,
        )

        # 2. Маршрутизация
        agent_info = next((a for a in AGENTS if a.name == route.agent), None)
        if not agent_info:
            agent_info = AGENTS[0]
            route.agent = agent_info.name

        handler_fn = ROUTE_HANDLERS.get(agent_info.handler)
        if handler_fn is None:
            response = f"Агент {route.agent} не реализован"
        else:
            try:
                response = await handler_fn(route.reformulated_query)
            except Exception as e:
                logger.error("Ошибка агента %s: %s", route.agent, e)
                response = f"Ошибка при обработке: {e}"

        # 3. Вторичные агенты
        secondary_responses: dict[str, str] = {}
        if route.multi_agent and route.secondary_agents:
            for sec_name in route.secondary_agents[:2]:
                sec_info = next((a for a in AGENTS if a.name == sec_name), None)
                if sec_info:
                    sec_handler = ROUTE_HANDLERS.get(sec_info.handler)
                    if sec_handler:
                        try:
                            sec_resp = await sec_handler(route.reformulated_query)
                            secondary_responses[sec_name] = sec_resp
                        except Exception as e:
                            secondary_responses[sec_name] = f"Ошибка: {e}"

        duration = (time.monotonic() - start) * 1000

        # 4. DARWIN: фоновая оценка
        try:
            import asyncio
            asyncio.create_task(
                self._darwin_background_eval(query, agent_info.name, response)
            )
        except Exception:
            pass

        return ConductorResult(
            query=query,
            route=route,
            response=response,
            agent_name=agent_info.name,
            department=agent_info.department,
            duration_ms=duration,
            secondary_responses=secondary_responses,
        )

    async def _darwin_background_eval(self, query: str, agent_name: str, response: str):
        """Фоновая оценка качества через DARWIN."""
        try:
            from services.darwin_agent import get_darwin_agent
            from services.conductor_autonomy import _extract_score
            darwin = get_darwin_agent()
            evaluation = await darwin.analyze_response(agent_name, query, response[:2000])
            score = _extract_score(evaluation)
            logger.info(
                "DARWIN: %s ответил на '%s' — оценка %.1f/10",
                agent_name, query[:40], score,
            )
        except Exception as e:
            logger.debug("DARWIN eval skip: %s", e)


# ─── Singleton ───────────────────────────────────────────────────────────────

_conductor: Conductor | None = None


def get_conductor() -> Conductor:
    global _conductor
    if _conductor is None:
        _conductor = Conductor()
    return _conductor
