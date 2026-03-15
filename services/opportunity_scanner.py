"""OpportunityScanner — поиск конкурсов, грантов, хакатонов, тендеров.

Сканирует источники, фильтрует по релевантности для AI Zavod,
генерирует краткую сводку через Claude API.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger("aizavod.opportunity_scanner")

# ─── Источники ──────────────────────────────────────────────────────────────

SOURCES: list[dict[str, str]] = [
    # Гранты РФ
    {"name": "ФАСИ (Фонд содействия инновациям)", "url": "https://fasie.ru", "type": "grant",
     "programs": "Старт-ИИ, Студенческий стартап, Развитие-ИИ, Коммерциализация, Бизнес-Старт"},
    {"name": "РНФ (Российский научный фонд)", "url": "https://rscf.ru", "type": "grant",
     "programs": "Малые группы (дедлайн 16.06.2026), Отдельные проекты"},
    {"name": "Фонд Сколково", "url": "https://sk.ru", "type": "grant",
     "programs": "Грант до 5 млн руб. на R&D, микрогранты до 1.5 млн"},
    {"name": "ФСИ (Фонд развития интернет-инициатив)", "url": "https://iidf.ru", "type": "accelerator",
     "programs": "Акселератор, инвестиции до 25 млн руб."},
    {"name": "Платформа НТИ", "url": "https://nti.one", "type": "grant",
     "programs": "Цифровые технологии, ИИ, маркетплейсы НТИ"},
    {"name": "АСИ (Агентство стратегических инициатив)", "url": "https://asi.ru", "type": "competition",
     "programs": "100 лидеров, Сильные идеи для нового времени"},

    # Хакатоны
    {"name": "Цифровой прорыв", "url": "https://hacks-ai.ru", "type": "hackathon",
     "programs": "Всероссийские хакатоны по ИИ, призы до 3 млн руб."},
    {"name": "Leaders of Digital", "url": "https://leadersofdigital.ru", "type": "hackathon",
     "programs": "IT-хакатоны, цифровая трансформация"},
    {"name": "DevPost", "url": "https://devpost.com/hackathons", "type": "hackathon",
     "programs": "Международные хакатоны (AI, ML, Web3)"},
    {"name": "MLContest", "url": "https://mlcontests.com", "type": "competition",
     "programs": "ML соревнования с призами"},

    # IT-конкурсы и акселераторы РФ
    {"name": "Иннополис", "url": "https://innopolis.com", "type": "accelerator",
     "programs": "Акселератор стартапов, AI/ML трек"},
    {"name": "GenerationS", "url": "https://generations.vc", "type": "accelerator",
     "programs": "Корпоративный акселератор РВК"},
    {"name": "Мой бизнес", "url": "https://мойбизнес.рф", "type": "grant",
     "programs": "Субсидии для МСП, гранты до 500K на ИТ"},

    # Международные
    {"name": "Anthropic Hackathons", "url": "https://anthropic.com", "type": "hackathon",
     "programs": "Хакатоны Claude API"},
    {"name": "Google AI Challenge", "url": "https://ai.google", "type": "competition",
     "programs": "AI/ML соревнования"},
    {"name": "Kaggle", "url": "https://kaggle.com/competitions", "type": "competition",
     "programs": "ML соревнования, призы $10K-$1M"},
]

# Ключевые слова AI Zavod для фильтрации
RELEVANCE_KEYWORDS = [
    "искусственный интеллект", "ИИ", "AI", "нейросет", "машинное обучение",
    "ML", "NLP", "LLM", "чат-бот", "chatbot", "автоматизация", "SaaS",
    "мультиагент", "цифровая трансформация", "цифровизация",
    "стартап", "IT", "ИТ", "программное обеспечение", "ПО",
    "сертификация", "ЕАЭС", "малый бизнес", "МСП",
    "генерация контента", "computer vision", "обработка данных",
]


@dataclass
class Opportunity:
    title: str
    source: str
    url: str
    type: str  # grant, hackathon, competition, accelerator, tender
    deadline: str = ""
    prize: str = ""
    description: str = ""
    relevance_score: float = 0.0
    ai_analysis: str = ""
    found_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class OpportunityScanner:
    """Scans multiple sources for money-making opportunities."""

    def __init__(self) -> None:
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("SCANNER_MODEL", "claude-haiku-4-5-20251001")
        self._found: list[Opportunity] = []

    async def scan_web(self, query: str | None = None) -> list[Opportunity]:
        """Search the web for current opportunities matching AI Zavod profile."""
        queries = [
            query or "гранты ИИ стартап Россия 2026",
            "хакатон искусственный интеллект Россия 2026 призы",
            "AI hackathon 2026 prizes open",
            "конкурс IT стартап грант ФАСИ Сколково 2026",
            "тендер разработка ИИ автоматизация 2026",
        ]

        results: list[Opportunity] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            for q in queries:
                try:
                    found = await self._search_query(client, q)
                    results.extend(found)
                except Exception as exc:
                    logger.warning("Search failed for %r: %s", q, exc)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique: list[Opportunity] = []
        for opp in results:
            if opp.url not in seen_urls:
                seen_urls.add(opp.url)
                unique.append(opp)

        # Score relevance
        for opp in unique:
            opp.relevance_score = self._calc_relevance(opp)

        # Sort by relevance
        unique.sort(key=lambda x: x.relevance_score, reverse=True)
        self._found = unique[:20]  # top 20
        return self._found

    async def analyze_opportunity(self, opp: Opportunity) -> str:
        """Deep analysis of a specific opportunity using Claude."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Проанализируй эту возможность для IT-стартапа AI Zavod:

ВОЗМОЖНОСТЬ:
- Название: {opp.title}
- Тип: {opp.type}
- Источник: {opp.source}
- Дедлайн: {opp.deadline or 'не указан'}
- Приз/сумма: {opp.prize or 'не указано'}
- Описание: {opp.description}

О НАС (AI Zavod):
- Мультиагентная SaaS-платформа для автоматизации бизнес-процессов
- 37 категорий, 262 отрасли, 148 AI-агентов
- Стек: FastAPI, Claude API, PostgreSQL, Docker, Telegram
- Готовые модули: CERTIFIER (сертификация ТС ЕАЭС), Instagram Factory (генерация контента)
- 1 человек (основатель), регистрация ООО планируется август 2026
- Локация: Россия (Набережные Челны)

ОТВЕТЬ КРАТКО:
1. Подходит ли нам? (да/нет/частично) и почему
2. Что подать/показать (конкретный модуль или идея)
3. Шансы на победу (низкие/средние/высокие)
4. Конкретные шаги (3-5 пунктов)
5. Потенциальный выигрыш (деньги, связи, клиенты)"""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        analysis = response.content[0].text
        opp.ai_analysis = analysis
        return analysis

    async def generate_ideas(self, context: str = "") -> str:
        """Generate money-making ideas based on current AI Zavod capabilities."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Ты — стратегический советник IT-стартапа AI Zavod.

ТЕКУЩИЕ ВОЗМОЖНОСТИ:
- Мультиагентная SaaS-платформа (FastAPI + Claude API + PostgreSQL)
- Telegram-боты (aiogram 3)
- Генерация контента (изображения через fal.ai, видео через Kling)
- Instagram/TikTok автопубликация
- RAG-система с BM25
- Сервер Hetzner (Docker, 24/7)

ГОТОВЫЕ МОДУЛИ:
- CERTIFIER: AI-консультант по сертификации ТС ЕАЭС
- Instagram Factory: автоматическая генерация и публикация фитнес-контента

ОГРАНИЧЕНИЯ:
- 1 человек (работает вечерами после основной работы)
- Бюджет: ~0 руб (есть НЗ 4.5 млн, но его нельзя трогать)
- Нет ООО (планируется август 2026)
- Нет портфолио клиентов

{f'ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ: {context}' if context else ''}

СГЕНЕРИРУЙ 10 КОНКРЕТНЫХ ИДЕЙ для заработка, отсортированных по:
- Скорость получения денег (дни, не месяцы)
- Минимальные вложения
- Использование уже готовых модулей

Формат каждой идеи:
## [Номер]. [Название]
- **Что:** конкретное описание
- **Кому продать:** целевой клиент
- **Сколько:** ожидаемый доход
- **Срок:** время до первых денег
- **Как начать:** 3 конкретных шага"""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.content[0].text

    async def scan_sources_summary(self) -> str:
        """Return formatted summary of all known sources."""
        lines = ["<b>Источники возможностей для AI Zavod:</b>\n"]
        by_type: dict[str, list[dict]] = {}
        for s in SOURCES:
            by_type.setdefault(s["type"], []).append(s)

        type_labels = {
            "grant": "Гранты",
            "hackathon": "Хакатоны",
            "competition": "Конкурсы/Соревнования",
            "accelerator": "Акселераторы",
        }

        for t, label in type_labels.items():
            sources = by_type.get(t, [])
            if not sources:
                continue
            lines.append(f"\n<b>{label}:</b>")
            for s in sources:
                lines.append(f"• <b>{s['name']}</b> — {s['programs']}")

        return "\n".join(lines)

    # ─── internals ──────────────────────────────────────────

    async def _search_query(
        self, client: httpx.AsyncClient, query: str
    ) -> list[Opportunity]:
        """Search using a simple web search approach."""
        # Use DuckDuckGo HTML (no API key needed)
        url = "https://html.duckduckgo.com/html/"
        try:
            resp = await client.post(url, data={"q": query}, headers={
                "User-Agent": "Mozilla/5.0 (compatible; AIZavod/1.0)"
            })
            if resp.status_code != 200:
                return []
            return self._parse_ddg_results(resp.text, query)
        except Exception as exc:
            logger.warning("DuckDuckGo search failed: %s", exc)
            return []

    def _parse_ddg_results(self, html: str, query: str) -> list[Opportunity]:
        """Parse DuckDuckGo HTML results into Opportunity objects."""
        results: list[Opportunity] = []

        # Simple regex parsing of DDG HTML results
        # Look for result links and snippets
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

            # Decode DDG redirect URL
            if "uddg=" in url:
                match = re.search(r"uddg=([^&]+)", url)
                if match:
                    from urllib.parse import unquote
                    url = unquote(match.group(1))

            opp_type = "grant"
            for kw, t in [("хакатон", "hackathon"), ("hackathon", "hackathon"),
                          ("конкурс", "competition"), ("contest", "competition"),
                          ("акселератор", "accelerator"), ("тендер", "tender")]:
                if kw in title.lower() or kw in snippet.lower():
                    opp_type = t
                    break

            results.append(Opportunity(
                title=title,
                source="DuckDuckGo",
                url=url,
                type=opp_type,
                description=snippet,
            ))

        return results

    def _calc_relevance(self, opp: Opportunity) -> float:
        """Calculate relevance score 0-1 based on keyword matching."""
        text = f"{opp.title} {opp.description}".lower()
        matches = sum(1 for kw in RELEVANCE_KEYWORDS if kw.lower() in text)
        return min(matches / 5.0, 1.0)


# Singleton
_scanner: OpportunityScanner | None = None


def get_scanner() -> OpportunityScanner:
    global _scanner
    if _scanner is None:
        _scanner = OpportunityScanner()
    return _scanner
