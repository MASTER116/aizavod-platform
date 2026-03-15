"""CONDUCTOR — главный маршрутизатор запросов AI Zavod.

Принимает произвольный запрос на естественном языке,
классифицирует намерение через Claude, маршрутизирует
к нужному агенту/сервису и возвращает результат.

Архитектура:
  Пользователь → CONDUCTOR → Классификация → Агент → Ответ
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("aizavod.conductor")


# ─── Реестр агентов ──────────────────────────────────────────────────────────

@dataclass
class AgentInfo:
    """Описание зарегистрированного агента."""
    name: str
    department: str          # директор/отдел
    description: str         # что умеет
    keywords: list[str]      # ключевые слова для быстрой маршрутизации
    handler: str             # имя async-функции для вызова


AGENTS: list[AgentInfo] = [
    AgentInfo(
        name="ceo_agent",
        department="CEO",
        description="Стратегические вопросы, планирование, декомпозиция задач, распределение по директорам",
        keywords=["стратег", "план", "приоритет", "направлен", "задач", "цел", "развит"],
        handler="_route_ceo",
    ),
    AgentInfo(
        name="certifier",
        department="Продукт",
        description="Консультации по сертификации товаров, ТР ТС ЕАЭС, таможня, импорт",
        keywords=["сертифик", "тр тс", "еаэс", "декларац", "таможн", "импорт", "ввоз", "растамож", "гост", "соответств"],
        handler="_route_certifier",
    ),
    AgentInfo(
        name="opportunity_scanner",
        department="Финансы",
        description="Поиск грантов, хакатонов, конкурсов, источники финансирования",
        keywords=["грант", "хакатон", "конкурс", "субсид", "фонд", "инвестиц", "финансир", "рнф", "фаси", "сколков"],
        handler="_route_opportunities",
    ),
    AgentInfo(
        name="idea_generator",
        department="Финансы",
        description="Генерация идей заработка, монетизация, бизнес-модели",
        keywords=["идея", "заработ", "монетиз", "доход", "бизнес-модел", "как заработ"],
        handler="_route_ideas",
    ),
    AgentInfo(
        name="market_analyzer",
        department="Финансы",
        description="Анализ рынка, конкурентов, оценка ниши, подготовка заявок",
        keywords=["рынок", "конкурент", "ниша", "анализ рынк", "заявк", "предложен"],
        handler="_route_market",
    ),
    AgentInfo(
        name="freelance_agent",
        department="Продажи",
        description="Поиск заказов на фрилансе, Kwork, Upwork, генерация откликов",
        keywords=["фриланс", "заказ", "kwork", "upwork", "отклик", "услуг", "портфолио"],
        handler="_route_freelance",
    ),
    AgentInfo(
        name="pricing_agent",
        department="Продажи",
        description="Оценка стоимости проектов, генерация коммерческих предложений",
        keywords=["цен", "стоимост", "оценк", "кп ", "коммерческ", "бюджет проект", "смет"],
        handler="_route_pricing",
    ),
    AgentInfo(
        name="outreach_agent",
        department="Продажи",
        description="Холодные продажи, генерация писем, поиск лидов, сегменты",
        keywords=["продаж", "лид", "клиент", "холодн", "письм", "email", "сегмент", "привлеч"],
        handler="_route_outreach",
    ),
    AgentInfo(
        name="content_factory",
        department="Контент",
        description="Генерация контента для Instagram, TikTok, VK — изображения, видео, тексты",
        keywords=["контент", "инстаграм", "instagram", "tiktok", "пост", "рилс", "reels", "сторис", "публикац"],
        handler="_route_content",
    ),
]


# ─── Классификация намерения ─────────────────────────────────────────────────

CLASSIFIER_PROMPT = """Ты — CONDUCTOR, маршрутизатор запросов платформы AI Zavod.

Проанализируй запрос пользователя и определи, какому агенту его направить.

ДОСТУПНЫЕ АГЕНТЫ:
{agents_list}

ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

Ответь ТОЛЬКО в формате JSON (без markdown):
{{
  "agent": "имя_агента",
  "confidence": 0.0-1.0,
  "reasoning": "почему этот агент",
  "reformulated_query": "уточнённый запрос для агента",
  "multi_agent": false,
  "secondary_agents": []
}}

Если запрос затрагивает несколько агентов, установи multi_agent=true и перечисли secondary_agents.
Если запрос слишком общий или стратегический — направь в ceo_agent.
"""


@dataclass
class RouteDecision:
    """Результат классификации запроса."""
    agent: str
    confidence: float
    reasoning: str
    reformulated_query: str
    multi_agent: bool = False
    secondary_agents: list[str] = field(default_factory=list)


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


class Conductor:
    """Главный маршрутизатор запросов AI Zavod."""

    def __init__(self) -> None:
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("CONDUCTOR_MODEL", "claude-haiku-4-5-20251001")

    def _agents_list_text(self) -> str:
        lines = []
        for a in AGENTS:
            lines.append(f"- {a.name} [{a.department}]: {a.description}")
        return "\n".join(lines)

    async def _classify(self, query: str) -> RouteDecision:
        """Классифицировать запрос — сначала по ключевым словам, потом через Claude."""
        # Быстрая маршрутизация по ключевым словам
        query_lower = query.lower()
        scores: dict[str, int] = {}
        for agent in AGENTS:
            score = sum(1 for kw in agent.keywords if kw in query_lower)
            if score > 0:
                scores[agent.name] = score

        if scores:
            best = max(scores, key=scores.get)
            best_score = scores[best]
            if best_score >= 2:
                return RouteDecision(
                    agent=best,
                    confidence=min(0.6 + best_score * 0.1, 0.95),
                    reasoning=f"Ключевые слова совпали ({best_score} совпадений)",
                    reformulated_query=query,
                )

        # Claude-классификация для сложных случаев
        if not self._api_key:
            # Фоллбэк — CEO-агент
            return RouteDecision(
                agent="ceo_agent",
                confidence=0.5,
                reasoning="API ключ недоступен, направляю в CEO",
                reformulated_query=query,
            )

        import anthropic

        prompt = CLASSIFIER_PROMPT.format(
            agents_list=self._agents_list_text(),
            query=query,
        )

        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        resp = await client.messages.create(
            model=self._model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        text = resp.content[0].text.strip()

        try:
            data = json.loads(text)
            return RouteDecision(
                agent=data.get("agent", "ceo_agent"),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                reformulated_query=data.get("reformulated_query", query),
                multi_agent=data.get("multi_agent", False),
                secondary_agents=data.get("secondary_agents", []),
            )
        except json.JSONDecodeError:
            logger.warning("Не удалось распарсить ответ классификатора: %s", text[:200])
            return RouteDecision(
                agent="ceo_agent",
                confidence=0.4,
                reasoning="Ошибка парсинга, фоллбэк в CEO",
                reformulated_query=query,
            )

    async def process(self, query: str) -> ConductorResult:
        """Главный метод: классифицировать → маршрутизировать → вернуть результат."""
        start = time.monotonic()

        # 1. Классификация
        route = await self._classify(query)
        logger.info(
            "CONDUCTOR: '%s' → %s (confidence=%.2f)",
            query[:80], route.agent, route.confidence,
        )

        # 2. Маршрутизация к основному агенту
        agent_info = next((a for a in AGENTS if a.name == route.agent), None)
        if not agent_info:
            agent_info = AGENTS[0]  # CEO fallback
            route.agent = agent_info.name

        handler_fn = globals().get(agent_info.handler)
        if handler_fn is None:
            response = f"Агент {route.agent} не реализован"
        else:
            try:
                response = await handler_fn(route.reformulated_query)
            except Exception as e:
                logger.error("Ошибка агента %s: %s", route.agent, e)
                response = f"Ошибка при обработке: {e}"

        # 3. Вторичные агенты (если multi_agent)
        secondary_responses: dict[str, str] = {}
        if route.multi_agent and route.secondary_agents:
            for sec_name in route.secondary_agents[:2]:  # макс 2 доп. агента
                sec_info = next((a for a in AGENTS if a.name == sec_name), None)
                if sec_info:
                    sec_handler = globals().get(sec_info.handler)
                    if sec_handler:
                        try:
                            sec_resp = await sec_handler(route.reformulated_query)
                            secondary_responses[sec_name] = sec_resp
                        except Exception as e:
                            secondary_responses[sec_name] = f"Ошибка: {e}"

        duration = (time.monotonic() - start) * 1000

        return ConductorResult(
            query=query,
            route=route,
            response=response,
            agent_name=agent_info.name,
            department=agent_info.department,
            duration_ms=duration,
            secondary_responses=secondary_responses,
        )


# ─── Обработчики маршрутов (route handlers) ─────────────────────────────────


async def _route_ceo(query: str) -> str:
    from services.ceo_agent import get_ceo_agent
    ceo = get_ceo_agent()
    return await ceo.process_question(query)


async def _route_certifier(query: str) -> str:
    from services.certifier_service import get_certifier
    certifier = get_certifier()
    result = await certifier.ask(query)
    return result.get("answer", str(result))


async def _route_opportunities(query: str) -> str:
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()

    # Если явно просят сканировать — сканируем
    if any(kw in query.lower() for kw in ["найди", "поиск", "сканир", "покажи"]):
        results = await scanner.scan_web()
        if not results:
            return "Ничего не найдено по текущим запросам."
        lines = [f"Найдено: {len(results)} возможностей\n"]
        for i, r in enumerate(results[:10], 1):
            lines.append(f"{i}. {r.title}")
            if r.description:
                lines.append(f"   {r.description[:120]}")
            lines.append(f"   {r.url} | {r.type}\n")
        return "\n".join(lines)

    # Иначе — генерируем идеи
    return await scanner.generate_ideas()


async def _route_ideas(query: str) -> str:
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    return await scanner.generate_ideas()


async def _route_market(query: str) -> str:
    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()

    if any(kw in query.lower() for kw in ["конкурент", "competitor"]):
        return await analyzer.analyze_competitors(query)
    elif any(kw in query.lower() for kw in ["заявк", "предложен", "proposal"]):
        return await analyzer.generate_proposal(query, "")
    else:
        return await analyzer.quick_market_scan(query)


async def _route_freelance(query: str) -> str:
    from services.freelance_agent import get_freelance_agent
    agent = get_freelance_agent()

    if any(kw in query.lower() for kw in ["найди", "поиск", "заказ"]):
        orders = await agent.search_orders()
        if not orders:
            return "Заказы не найдены."
        lines = [f"Найдено: {len(orders)} заказов\n"]
        for i, o in enumerate(orders[:10], 1):
            lines.append(f"{i}. {o.title[:80]}")
            if o.budget:
                lines.append(f"   Бюджет: {o.budget}")
            lines.append(f"   {o.url} | {o.platform}\n")
        return "\n".join(lines)

    if any(kw in query.lower() for kw in ["kwork", "услуг"]):
        return await agent.create_kwork_services()

    return await agent.list_services()


async def _route_pricing(query: str) -> str:
    from services.pricing_agent import get_pricing_agent
    agent = get_pricing_agent()
    return await agent.estimate_project(query)


async def _route_outreach(query: str) -> str:
    from services.outreach_agent import get_outreach_agent
    agent = get_outreach_agent()

    if any(kw in query.lower() for kw in ["лид", "канал", "где найти"]):
        return await agent.find_leads(query)
    elif any(kw in query.lower() for kw in ["письм", "сообщен", "email", "холодн"]):
        return await agent.generate_cold_message(query, "email")
    else:
        return await agent.list_segments()


async def _route_content(query: str) -> str:
    """Контент-фабрика — пока возвращает статус."""
    return (
        "Фабрика контента (Instagram Factory):\n\n"
        "Доступные действия:\n"
        "- Генерация изображений (fal.ai Flux Pro)\n"
        "- Генерация подписей (Claude API)\n"
        "- Публикация в Instagram/TikTok\n"
        "- Расписание постов\n\n"
        "Статус: Instagram логин заблокирован (ChallengeRequired).\n"
        "Генерация контента работает, публикация приостановлена."
    )


# ─── Singleton ───────────────────────────────────────────────────────────────

_conductor: Conductor | None = None


def get_conductor() -> Conductor:
    global _conductor
    if _conductor is None:
        _conductor = Conductor()
    return _conductor
