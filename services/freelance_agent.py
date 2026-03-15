"""FreelanceAgent — поиск заказов на фрилансе и генерация откликов.

Сканирует Kwork, FL.ru, Habr Freelance, Upwork.
Генерирует персонализированные отклики через Claude API.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger("aizavod.freelance_agent")


FREELANCE_PLATFORMS = [
    {
        "name": "Kwork",
        "search_url": "https://kwork.ru/projects",
        "categories": [
            "разработка ботов", "telegram боты", "автоматизация",
            "парсинг", "AI", "нейросети", "python разработка",
            "FastAPI", "базы данных", "интеграция API",
        ],
    },
    {
        "name": "FL.ru",
        "search_url": "https://www.fl.ru/projects/",
        "categories": [
            "python", "telegram бот", "автоматизация бизнеса",
            "искусственный интеллект", "парсинг данных",
            "backend разработка", "API интеграция",
        ],
    },
    {
        "name": "Habr Freelance",
        "search_url": "https://freelance.habr.com/tasks",
        "categories": [
            "python", "backend", "telegram", "автоматизация",
            "AI/ML", "API",
        ],
    },
]

# Наши услуги — что мы реально можем делать
OUR_SERVICES = [
    {
        "name": "Telegram-боты",
        "description": "Разработка Telegram-ботов на aiogram 3 с базой данных, оплатой, FSM",
        "price_range": "15 000 — 80 000 руб.",
        "time": "3-14 дней",
        "keywords": ["telegram", "бот", "bot", "aiogram", "чат-бот"],
    },
    {
        "name": "AI-интеграция",
        "description": "Подключение ChatGPT/Claude/Gemini к бизнес-процессам, RAG, чат-боты с AI",
        "price_range": "20 000 — 150 000 руб.",
        "time": "5-21 день",
        "keywords": ["ai", "ии", "нейросет", "chatgpt", "gpt", "claude", "llm", "rag"],
    },
    {
        "name": "Автоматизация бизнеса",
        "description": "Автоматизация через Python + API: CRM, рассылки, отчёты, парсинг",
        "price_range": "10 000 — 100 000 руб.",
        "time": "3-14 дней",
        "keywords": ["автоматизац", "парсинг", "scraping", "api", "интеграц", "crm"],
    },
    {
        "name": "Backend-разработка",
        "description": "REST API на FastAPI/Django, базы данных, деплой Docker",
        "price_range": "20 000 — 200 000 руб.",
        "time": "7-30 дней",
        "keywords": ["backend", "fastapi", "django", "api", "rest", "python", "postgresql"],
    },
    {
        "name": "Генерация контента",
        "description": "AI-генерация изображений, видео, текстов для соцсетей",
        "price_range": "5 000 — 50 000 руб.",
        "time": "1-7 дней",
        "keywords": ["контент", "генерация", "изображен", "видео", "соцсет", "instagram", "smm"],
    },
]


@dataclass
class FreelanceOrder:
    title: str
    platform: str
    url: str
    budget: str = ""
    description: str = ""
    match_service: str = ""
    match_score: float = 0.0
    response_draft: str = ""
    found_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class FreelanceAgent:
    """Searches freelance platforms and generates responses."""

    def __init__(self) -> None:
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("FREELANCE_MODEL", "claude-haiku-4-5-20251001")

    async def search_orders(self, custom_query: str = "") -> list[FreelanceOrder]:
        """Search freelance platforms for relevant orders."""
        all_queries = []

        if custom_query:
            all_queries.append(custom_query)
        else:
            # Build search queries from our services
            for service in OUR_SERVICES:
                all_queries.extend([
                    f"фриланс заказ {service['name']} 2026",
                    f"kwork {' '.join(service['keywords'][:3])}",
                ])

        results: list[FreelanceOrder] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            for q in all_queries[:8]:  # Limit queries
                try:
                    found = await self._ddg_search(client, q)
                    results.extend(found)
                except Exception as exc:
                    logger.warning("Search failed for %r: %s", q, exc)

        # Deduplicate
        seen: set[str] = set()
        unique: list[FreelanceOrder] = []
        for order in results:
            key = order.url or order.title
            if key not in seen:
                seen.add(key)
                unique.append(order)

        # Score relevance
        for order in unique:
            self._score_order(order)

        unique.sort(key=lambda x: x.match_score, reverse=True)
        return unique[:15]

    async def generate_response(self, order: FreelanceOrder) -> str:
        """Generate a personalized freelance response/proposal."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Напиши отклик на фриланс-заказ. Отклик должен быть:
- Профессиональный, но не формальный
- Показывать понимание задачи клиента
- Предлагать конкретное решение
- Упоминать релевантный опыт
- Содержать примерные сроки и стоимость

ЗАКАЗ:
Название: {order.title}
Платформа: {order.platform}
Бюджет клиента: {order.budget or 'не указан'}
Описание: {order.description}

НАША ЭКСПЕРТИЗА:
- Python (FastAPI, aiogram 3, SQLAlchemy)
- AI/ML интеграция (Claude API, RAG, BM25)
- Telegram-боты (FSM, оплата, админ-панели)
- Docker, PostgreSQL, Redis
- Генерация контента (fal.ai, Kling)
- Готовые кейсы: AI-консультант по сертификации, Instagram Factory

Напиши отклик от 100 до 250 слов. Без маркдауна. Начни с обращения к клиенту."""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        text = response.content[0].text
        order.response_draft = text
        return text

    async def create_kwork_services(self) -> str:
        """Generate descriptions for Kwork services (kwork.ru)."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = """Сгенерируй описания для 5 услуг на Kwork.ru.

Наша экспертиза:
- Telegram-боты (aiogram 3, FSM, оплата, админка)
- AI-интеграция (Claude/GPT, RAG, чат-боты с ИИ)
- Автоматизация (парсинг, API, CRM-интеграция)
- Backend (FastAPI, PostgreSQL, Docker)
- Генерация контента (AI-изображения, тексты для соцсетей)

Для каждой услуги напиши:

## [Номер]. [Название услуги для Kwork]
**Категория:** (категория на Kwork)
**Цена:** (стартовая цена)
**Срок:** (дней)
**Заголовок (до 100 символов):** привлекательный заголовок
**Описание (до 1000 символов):** что входит, что получит клиент, почему мы
**Теги:** 5 ключевых слов

Услуги должны быть разные по цене (от 1000 до 30000 руб.)
и покрывать разные запросы клиентов."""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return response.content[0].text

    async def list_services(self) -> str:
        """Return formatted list of our services."""
        lines = ["<b>Наши услуги для фриланса:</b>\n"]
        for i, s in enumerate(OUR_SERVICES, 1):
            lines.append(
                f"<b>{i}. {s['name']}</b>\n"
                f"   {s['description']}\n"
                f"   Цена: {s['price_range']}\n"
                f"   Сроки: {s['time']}\n"
            )
        return "\n".join(lines)

    # ─── internals ──────────────────────────────────────────

    async def _ddg_search(
        self, client: httpx.AsyncClient, query: str
    ) -> list[FreelanceOrder]:
        url = "https://html.duckduckgo.com/html/"
        resp = await client.post(url, data={"q": query}, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AIZavod/1.0)"
        })
        if resp.status_code != 200:
            return []
        return self._parse_results(resp.text)

    def _parse_results(self, html: str) -> list[FreelanceOrder]:
        results: list[FreelanceOrder] = []
        link_pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL
        )
        snippet_pattern = re.compile(
            r'class="result__snippet"[^>]*>(.*?)</[^>]+>', re.DOTALL
        )

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (url, title) in enumerate(links[:10]):
            title = re.sub(r"<[^>]+>", "", title).strip()
            snippet = ""
            if i < len(snippets):
                snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()

            if "uddg=" in url:
                match = re.search(r"uddg=([^&]+)", url)
                if match:
                    from urllib.parse import unquote
                    url = unquote(match.group(1))

            platform = "Другое"
            for p in ["kwork", "fl.ru", "freelance.habr", "upwork", "freelansim"]:
                if p in url.lower():
                    platform = p.replace(".ru", "").replace(".com", "").capitalize()
                    break

            # Extract budget from title/snippet
            budget = ""
            budget_match = re.search(r'(\d[\d\s]*(?:руб|₽|\$|USD))', f"{title} {snippet}")
            if budget_match:
                budget = budget_match.group(1).strip()

            results.append(FreelanceOrder(
                title=title,
                platform=platform,
                url=url,
                budget=budget,
                description=snippet,
            ))

        return results

    def _score_order(self, order: FreelanceOrder) -> None:
        """Score how well an order matches our services."""
        text = f"{order.title} {order.description}".lower()
        best_score = 0.0
        best_service = ""

        for service in OUR_SERVICES:
            matches = sum(1 for kw in service["keywords"] if kw in text)
            score = min(matches / 3.0, 1.0)
            if score > best_score:
                best_score = score
                best_service = service["name"]

        order.match_score = best_score
        order.match_service = best_service


_agent: FreelanceAgent | None = None


def get_freelance_agent() -> FreelanceAgent:
    global _agent
    if _agent is None:
        _agent = FreelanceAgent()
    return _agent
