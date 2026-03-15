"""CONDUCTOR — мета-оркестратор AI Zavod.

Два режима:
  1. Роутер: вопрос → keyword/Claude классификация → один агент → ответ
  2. Оркестратор: задача → CEO-декомпозиция → директора → отделы → специалисты → сборка

Иерархия:
  Основатель → CONDUCTOR → Директора → Начальники отделов → Специалисты
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
        description="Консультации по сертификации товаров, ТР ТС ЕАЭС, таможня, импорт, стоимость сертификации",
        keywords=[
            "сертифик", "тр тс", "еаэс", "декларац", "таможн", "импорт", "ввоз",
            "растамож", "гост", "соответств", "оттс", "сбктс", "эра-глонасс",
            "глонасс", "гбо", "лаборатор", "аккредит", "омологац",
            # Марки авто — основной кейс CERTIFIER
            "jac", "haval", "chery", "geely", "changan", "faw", "byd", "exeed",
            "москвич", "лада", "камаз", "газ ", "уаз", "маз ",
            # Контекст сертификации
            "локализац", "ввоз авто", "параллельн", "спецтехник",
        ],
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
    AgentInfo(
        name="lawyer_agent",
        department="Юридический",
        description="Юридические консультации: договоры, регистрация ИП/ООО, трудовое право, налоговые споры",
        keywords=[
            "юрист", "юридическ", "договор", "контракт", "регистрац ип", "регистрац ооо",
            "трудов", "увольнен", "закон", "право", "суд", "иск", "штраф",
            "лицензи", "оквэд", "устав", "налогов спор", "открыть ип", "открыть ооо",
        ],
        handler="_route_lawyer",
    ),
    AgentInfo(
        name="accountant_agent",
        department="Бухгалтерия",
        description="Бухгалтерия, налоги, отчетность, зарплата, выбор системы налогообложения для ИП/ООО",
        keywords=[
            "бухгалтер", "налог", "усн", "осн", "патент", "отчетност", "декларац налог",
            "взнос", "ндфл", "зарплат", "страхов", "пфр", "фсс", "ндс",
            "касс", "бухучет", "баланс", "календарь отчет",
        ],
        handler="_route_accountant",
    ),
    AgentInfo(
        name="darwin_agent",
        department="Самообучение",
        description="Анализ качества агентов, оптимизация промптов, еженедельные отчёты, поиск паттернов ошибок",
        keywords=[
            "качество агент", "оптимиз промпт", "самообуч", "darwin",
            "улучш агент", "отчёт качеств", "анализ ответ",
        ],
        handler="_route_darwin",
    ),
    AgentInfo(
        name="guardian_agent",
        department="Безопасность",
        description="Антифрод, антиабьюз, проверка безопасности ввода/вывода, анализ поведения пользователей",
        keywords=[
            "безопасност", "фрод", "абьюз", "injection", "спам",
            "guardian", "блокировк", "угроз", "атак", "защит",
        ],
        handler="_route_guardian",
    ),
    AgentInfo(
        name="scholar_agent",
        department="Наука",
        description="Грантовые заявки, научные статьи, литобзоры, оформление по ГОСТ/ВАК",
        keywords=[
            "наук", "стать", "публикац", "гост", "вак", "ринц",
            "литобзор", "диссертац", "исследован", "scholar",
            "грантов заявк", "научн",
        ],
        handler="_route_scholar",
    ),
    AgentInfo(
        name="herald_agent",
        department="DevRel",
        description="Open-source продвижение, README, статьи Habr, Telegram-канал, Product Hunt",
        keywords=[
            "open-source", "readme", "habr", "хабр", "devrel",
            "product hunt", "github", "телеграм канал", "herald",
            "продвижен", "контент маркет",
        ],
        handler="_route_herald",
    ),
    AgentInfo(
        name="namer_agent",
        department="Нейминг",
        description="Генерация названий, проверка доменов, товарных знаков, ЕГРЮЛ, соцсетей",
        keywords=[
            "названи", "нейминг", "имя компан", "имя продукт", "домен",
            "бренд", "нейм", "как назвать",
        ],
        handler="_route_namer",
    ),
    AgentInfo(
        name="guardian_ip_agent",
        department="IP/Патенты",
        description="Товарные знаки, патенты, IP-аудит, анализ доменов, защита интеллектуальной собственности",
        keywords=[
            "патент", "товарн знак", "фипс", "роспатент", "интеллектуальн",
            "ip аудит", "мкту", "авторск прав", "реестр по",
        ],
        handler="_route_guardian_ip",
    ),
    AgentInfo(
        name="voice_agent",
        department="Голос",
        description="Скрипты звонков, оптимизация для TTS, деловые и продающие звонки",
        keywords=[
            "звонок", "звонк", "скрипт", "tts", "голос", "voice",
            "позвонить", "переговор", "телефон",
        ],
        handler="_route_voice",
    ),
    AgentInfo(
        name="treasurer_agent",
        department="Финансы/Казначей",
        description="Монетизация инфраструктуры, анализ расходов, поиск доходов, ценообразование, cash flow",
        keywords=[
            "расход", "оптимиз затрат", "cash flow", "денежн поток",
            "окупаемост", "burn rate", "тариф", "ценообразован",
            "treasurer", "монетизац инфра",
        ],
        handler="_route_treasurer",
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


# ─── Иерархия директоров ─────────────────────────────────────────────────

DIRECTORS = {
    "cto": {
        "title": "Технический директор (CTO)",
        "departments": ["backend", "frontend", "devops", "ai_ml", "security", "qa"],
        "scope": "Архитектура, код, инфраструктура, DevOps, AI/ML, безопасность, тестирование",
    },
    "cfo": {
        "title": "Финансовый директор (CFO)",
        "departments": ["accounting", "grants", "freelance", "analytics"],
        "scope": "Финансы, бюджет, гранты, фриланс, unit-экономика, налоги",
    },
    "cmo": {
        "title": "Маркетинговый директор (CMO)",
        "departments": ["content", "seo", "devrel", "outreach"],
        "scope": "Маркетинг, контент, соцсети, PR, DevRel, продвижение",
    },
    "coo": {
        "title": "Операционный директор (COO)",
        "departments": ["processes", "partners", "support"],
        "scope": "Операции, процессы, автоматизация, партнёры, поддержка",
    },
    "cpo": {
        "title": "Продуктовый директор (CPO)",
        "departments": ["certifier", "saas", "research"],
        "scope": "Продукт, roadmap, фичи, UX, приоритизация бэклога",
    },
    "cdo": {
        "title": "Дизайн-директор (CDO)",
        "departments": ["uiux", "brand", "motion"],
        "scope": "Дизайн, UI/UX, брендинг, промдизайн, анимации",
    },
    "chro": {
        "title": "HR-директор (CHRO)",
        "departments": ["hiring", "culture"],
        "scope": "Кадры, найм, обучение, культура, аутсорс",
    },
    "clo": {
        "title": "Юридический директор (CLO)",
        "departments": ["ip", "contracts", "registration"],
        "scope": "Юридическое, договоры, IP, патенты, регистрация, compliance",
    },
}

# ─── Промпт CEO-декомпозиции ─────────────────────────────────────────────

CEO_DECOMPOSE_PROMPT = """Ты — CEO компании AI Zavod. Основатель дал тебе задачу.
Разбей её на подзадачи для директоров.

ДИРЕКТОРА:
{directors_list}

ЗАДАЧА ОТ ОСНОВАТЕЛЯ:
{task}

Ответь ТОЛЬКО JSON (без markdown):
{{
  "analysis": "краткий анализ задачи (1-2 предложения)",
  "directors": [
    {{
      "role": "cto",
      "task": "конкретная задача для этого директора",
      "priority": "critical|high|normal|low",
      "estimated_hours": 2.0,
      "deliverables": ["что должен сделать"],
      "depends_on": []
    }}
  ]
}}

Правила:
- Привлекай ТОЛЬКО нужных директоров (не всех)
- Задачи должны быть конкретными, не абстрактными
- Укажи зависимости: если CDO должен сделать дизайн до CTO — depends_on: ["cdo"]
- estimated_hours — реалистичная оценка
- deliverables — конкретные результаты
"""

DIRECTOR_DECOMPOSE_PROMPT = """Ты — {director_title} компании AI Zavod.
CEO поставил тебе задачу. Разбей её на подзадачи для своих отделов.

ТВОИ ОТДЕЛЫ:
{departments_list}

ЗАДАЧА ОТ CEO:
{task}

Ответь ТОЛЬКО JSON (без markdown):
{{
  "tasks": [
    {{
      "department": "название_отдела",
      "task": "конкретная задача",
      "estimated_hours": 1.0,
      "deliverables": ["что должен сделать"],
      "depends_on": []
    }}
  ]
}}

Правила:
- Привлекай только нужные отделы
- Задачи конкретные, выполнимые за 1-4 часа
- Если задача простая — один отдел, одна задача
"""

# ─── Определение режима ──────────────────────────────────────────────────

TASK_KEYWORDS = [
    "сделай", "создай", "разработай", "построй", "реализуй", "запусти",
    "настрой", "подготовь", "напиши", "спроектируй", "деплой", "мигрируй",
    "автоматизируй", "интегрируй", "оптимизируй", "рефактор",
    "добавь", "обнови", "исправь", "почини", "переделай",
]

QUESTION_KEYWORDS = [
    "сколько", "что такое", "как работает", "почему", "зачем",
    "можно ли", "есть ли", "какой", "какая", "какие",
    "расскажи", "объясни", "покажи",
]


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
            if best_score >= 1:
                return RouteDecision(
                    agent=best,
                    confidence=min(0.85 + best_score * 0.05, 0.95),
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
            # Попытка парсить напрямую
            data = json.loads(text)
        except json.JSONDecodeError:
            # Извлечь JSON из markdown (```json ... ```) или найти {} в тексте
            import re
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if not json_match:
                json_match = re.search(r"(\{[^{}]*\"agent\"[^{}]*\})", text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    data = None
            else:
                data = None

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
        # Последний шанс: поискать имя агента в тексте
        text_lower = text.lower()
        for agent in AGENTS:
            if agent.name in text_lower:
                return RouteDecision(
                    agent=agent.name,
                    confidence=0.5,
                    reasoning=f"Извлечено из текста ответа (имя агента найдено)",
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
        # Явные маркеры задачи
        for kw in TASK_KEYWORDS:
            if q.startswith(kw) or f" {kw} " in f" {q} ":
                return "orchestrator"
        # Явные маркеры вопроса
        for kw in QUESTION_KEYWORDS:
            if q.startswith(kw):
                return "router"
        # По умолчанию — роутер (безопаснее)
        return "router"

    async def _call_claude(self, prompt: str, max_tokens: int = 2000) -> str:
        """Вызвать Claude API."""
        if not self._api_key:
            return "{}"
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        resp = await client.messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.content[0].text.strip()

    async def _parse_json(self, text: str) -> dict | None:
        """Извлечь JSON из ответа Claude."""
        import re
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if not m:
                m = re.search(r"(\{.*\})", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
        return None

    async def orchestrate(self, task: str) -> dict:
        """Полная оркестрация: CEO → директора → отделы → результат."""
        start = time.monotonic()
        logger.info("ORCHESTRATOR: начинаю декомпозицию: '%s'", task[:100])

        # ── Шаг 1: CEO-декомпозиция ──
        directors_text = "\n".join(
            f"- {code}: {d['title']} — {d['scope']}"
            for code, d in DIRECTORS.items()
        )
        ceo_prompt = CEO_DECOMPOSE_PROMPT.format(
            directors_list=directors_text,
            task=task,
        )
        ceo_response = await self._call_claude(ceo_prompt)
        ceo_data = await self._parse_json(ceo_response)

        if not ceo_data or "directors" not in ceo_data:
            return {
                "status": "error",
                "message": "CEO не смог декомпозировать задачу",
                "raw": ceo_response[:500],
            }

        analysis = ceo_data.get("analysis", "")
        director_tasks = ceo_data["directors"]
        logger.info("CEO: %d директоров задействовано", len(director_tasks))

        # ── Шаг 2: Директорская декомпозиция ──
        full_tree = {
            "task": task,
            "analysis": analysis,
            "directors": [],
            "duration_ms": 0,
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
            dir_response = await self._call_claude(dir_prompt, max_tokens=1500)
            dir_data = await self._parse_json(dir_response)

            dept_tasks = []
            if dir_data and "tasks" in dir_data:
                dept_tasks = dir_data["tasks"]

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
            logger.info(
                "  %s: %d отделов", role.upper(), len(dept_tasks)
            )

        full_tree["duration_ms"] = (time.monotonic() - start) * 1000
        return full_tree

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


async def _route_lawyer(query: str) -> str:
    from services.lawyer_agent import get_lawyer_agent
    agent = get_lawyer_agent()
    q = query.lower()
    if any(kw in q for kw in ["договор", "контракт"]):
        return await agent.check_contract(query)
    elif any(kw in q for kw in ["регистрац", "открыть ип", "зарегистр"]):
        return await agent.ip_registration(query)
    elif any(kw in q for kw in ["трудов", "увольнен", "сотрудник", "работник"]):
        return await agent.labor_law(query)
    return await agent.consult(query)


async def _route_accountant(query: str) -> str:
    from services.accountant_agent import get_accountant_agent
    agent = get_accountant_agent()
    q = query.lower()
    if any(kw in q for kw in ["усн", "осн", "патент", "систем налог", "какой налог"]):
        return await agent.compare_tax_systems(query, "", "")
    elif any(kw in q for kw in ["календар", "отчетност", "когда сдавать", "срок"]):
        return await agent.reporting_calendar()
    elif any(kw in q for kw in ["зарплат", "ндфл", "оклад", "выплат"]):
        return await agent.payroll_calc(query)
    return await agent.consult(query)


async def _route_darwin(query: str) -> str:
    from services.darwin_agent import get_darwin_agent
    agent = get_darwin_agent()
    q = query.lower()
    if any(kw in q for kw in ["оптимиз", "промпт", "улучш"]):
        return await agent.optimize_prompt("unknown", query, "")
    elif any(kw in q for kw in ["отчёт", "отчет", "неделя", "итог"]):
        return await agent.weekly_report(query)
    elif any(kw in q for kw in ["паттерн", "лог", "маршрут"]):
        return await agent.detect_patterns(query)
    return await agent.analyze_response("unknown", query, "")


async def _route_guardian(query: str) -> str:
    from services.guardian_agent import get_guardian_agent
    agent = get_guardian_agent()
    q = query.lower()
    if any(kw in q for kw in ["проверь ввод", "input", "injection"]):
        return await agent.check_input(query)
    elif any(kw in q for kw in ["поведен", "активност", "мультиаккаунт"]):
        return await agent.analyze_user_behavior(query)
    elif any(kw in q for kw in ["отчёт", "отчет", "угроз"]):
        return await agent.threat_report()
    return await agent.check_input(query)


async def _route_scholar(query: str) -> str:
    from services.scholar_agent import get_scholar_agent
    agent = get_scholar_agent()
    q = query.lower()
    if any(kw in q for kw in ["грант", "заявк", "рнф", "фси"]):
        fund = "РНФ" if "рнф" in q else "ФСИ" if "фси" in q else ""
        return await agent.write_grant(query, fund)
    elif any(kw in q for kw in ["литобзор", "обзор литератур", "что написано"]):
        return await agent.literature_review(query)
    elif any(kw in q for kw in ["оформ", "гост", "вак", "стать"]):
        return await agent.format_article(query)
    return await agent.research_question(query)


async def _route_herald(query: str) -> str:
    from services.herald_agent import get_herald_agent
    agent = get_herald_agent()
    q = query.lower()
    if any(kw in q for kw in ["readme"]):
        return await agent.write_readme(query, "")
    elif any(kw in q for kw in ["habr", "хабр", "стать"]):
        return await agent.write_habr_article(query)
    elif any(kw in q for kw in ["телеграм", "telegram", "пост"]):
        return await agent.telegram_post(query)
    elif any(kw in q for kw in ["product hunt", "запуск"]):
        return await agent.product_hunt_launch(query, "")
    return await agent.oss_strategy(query)


async def _route_namer(query: str) -> str:
    from services.namer_agent import get_namer_agent
    agent = get_namer_agent()
    q = query.lower()
    if any(kw in q for kw in ["проверь", "доступн", "занят"]):
        return await agent.check_availability(query)
    elif any(kw in q for kw in ["полн", "цикл", "от и до"]):
        return await agent.full_naming(query)
    return await agent.generate_names(query)


async def _route_guardian_ip(query: str) -> str:
    from services.guardian_ip_agent import get_guardian_ip_agent
    agent = get_guardian_ip_agent()
    q = query.lower()
    if any(kw in q for kw in ["товарн знак", "фипс", "мкту"]):
        return await agent.check_trademark(query)
    elif any(kw in q for kw in ["патент", "изобретен"]):
        return await agent.check_patent(query)
    elif any(kw in q for kw in ["домен", "whois"]):
        return await agent.domain_analysis(query)
    return await agent.ip_audit(query)


async def _route_voice(query: str) -> str:
    from services.voice_agent import get_voice_agent
    agent = get_voice_agent()
    q = query.lower()
    if any(kw in q for kw in ["делов", "переговор", "партнёр"]):
        return await agent.business_call_script(query, "")
    elif any(kw in q for kw in ["продаж", "продающ", "холодн"]):
        return await agent.sales_script(query, "")
    elif any(kw in q for kw in ["tts", "озвуч", "оптимиз"]):
        return await agent.tts_optimize(query)
    return await agent.routine_call_script(query)


async def _route_treasurer(query: str) -> str:
    from services.treasurer_agent import get_treasurer_agent
    agent = get_treasurer_agent()
    q = query.lower()
    if any(kw in q for kw in ["расход", "затрат", "оптимиз"]):
        return await agent.analyze_expenses(query)
    elif any(kw in q for kw in ["доход", "заработ", "источник"]):
        return await agent.find_income_sources(query, "")
    elif any(kw in q for kw in ["cash flow", "денежн", "поток", "прогноз"]):
        return await agent.cash_flow_plan(query, "")
    elif any(kw in q for kw in ["цен", "тариф", "ценообразован"]):
        return await agent.pricing_strategy(query)
    return await agent.find_income_sources(query, "")


# ─── Singleton ───────────────────────────────────────────────────────────────

_conductor: Conductor | None = None


def get_conductor() -> Conductor:
    global _conductor
    if _conductor is None:
        _conductor = Conductor()
    return _conductor
