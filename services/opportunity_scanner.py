"""OpportunityScanner — глубокий поиск и анализ конкурсов, грантов, хакатонов.

Полный цикл: поиск → анализ правил → генерация идей под конкурс →
Excel-калькуляция → генерация документов на подачу → сохранение идей.
"""
from __future__ import annotations

import json
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

RELEVANCE_KEYWORDS = [
    "искусственный интеллект", "ИИ", "AI", "нейросет", "машинное обучение",
    "ML", "NLP", "LLM", "чат-бот", "chatbot", "автоматизация", "SaaS",
    "мультиагент", "цифровая трансформация", "цифровизация",
    "стартап", "IT", "ИТ", "программное обеспечение", "ПО",
    "сертификация", "ЕАЭС", "малый бизнес", "МСП",
    "генерация контента", "computer vision", "обработка данных",
]

AI_ZAVOD_CONTEXT = """О НАС (AI Zavod):
- Мультиагентная SaaS-платформа для автоматизации бизнес-процессов
- 19 рабочих агентов, CONDUCTOR-маршрутизатор
- 37 категорий, 262 отрасли (ОКВЭД-2), целевая архитектура 148 агентов
- Стек: FastAPI, Claude API (Anthropic), PostgreSQL, Redis, Docker, aiogram 3
- Готовые модули: CERTIFIER (сертификация ТС ЕАЭС), Instagram Factory, LAWYER, ACCOUNTANT, SCHOLAR
- 1 человек (основатель, инженер МАЗ Москвич), вечерами + выходные
- Регистрация ООО планируется август 2026
- Локация: Набережные Челны, Татарстан → Москва
- Claude (Anthropic) — основной исполнитель всех задач
- Бюджет: ~0 руб (НЗ 4.5 млн неприкосновенны)
- Сервер: Hetzner (Германия), Docker 24/7"""


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
    """Глубокий поиск и анализ возможностей для AI Zavod."""

    def __init__(self) -> None:
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("SCANNER_MODEL", "claude-haiku-4-5-20251001")
        self._found: list[Opportunity] = []

    async def _call_llm(self, prompt: str, *, max_tokens: int = 3000, temperature: float = 0.4) -> str:
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.content[0].text

    # ─── 1. Поиск ───────────────────────────────────────────────────────────

    async def scan_web(self, query: str | None = None) -> list[Opportunity]:
        """Поиск конкурсов и грантов в интернете."""
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

        seen_urls: set[str] = set()
        unique: list[Opportunity] = []
        for opp in results:
            if opp.url not in seen_urls:
                seen_urls.add(opp.url)
                unique.append(opp)

        for opp in unique:
            opp.relevance_score = self._calc_relevance(opp)

        unique.sort(key=lambda x: x.relevance_score, reverse=True)
        self._found = unique[:20]
        return self._found

    # ─── 2. Глубокий анализ конкурса ────────────────────────────────────────

    async def deep_analyze(self, title: str, url: str, description: str = "") -> str:
        """Полный анализ конкурса: правила, требования, отчётность, сроки."""
        prompt = f"""Проведи ГЛУБОКИЙ анализ конкурса/гранта.

КОНКУРС: {title}
ССЫЛКА: {url}
ОПИСАНИЕ: {description}

{AI_ZAVOD_CONTEXT}

Дай ПОЛНЫЙ анализ по разделам:

## 1. Общая информация
- Организатор и фонд
- Тип (грант/конкурс/хакатон/акселератор)
- Сумма финансирования
- Сроки подачи заявки (дедлайн)
- Сроки реализации проекта

## 2. Правила участия
- Кто может участвовать (юрлицо/физлицо/ИП)
- Требования к команде (размер, квалификация)
- Требования к проекту (TRL, стадия, сфера)
- Ограничения (возраст, регион, ОПФ)
- Нужно ли ООО? (критично для нас — ООО будет только в августе 2026)

## 3. Требования к отчётности
- Промежуточные отчёты (частота, формат)
- Финальный отчёт
- Финансовая отчётность
- Подтверждающие документы
- Штрафы за невыполнение

## 4. Подходит ли AI Zavod?
- Оценка соответствия (0-10)
- Сильные стороны нашей заявки
- Слабые стороны / риски
- Что нужно доработать до подачи

## 5. Конкретные шаги для подачи
- Пошаговый чек-лист (5-10 пунктов)
- Документы для подготовки
- Ключевые даты"""
        return await self._call_llm(prompt, max_tokens=4000)

    # ─── 3. Генерация идей ПОД КОНКРЕТНЫЙ конкурс ───────────────────────────

    async def generate_ideas_for_grant(self, grant_title: str, grant_analysis: str) -> str:
        """Генерация идей именно для этого конкурса — быстрая реализация, мин. риски."""
        prompt = f"""Ты — стратегический советник AI Zavod.

КОНКУРС: {grant_title}

АНАЛИЗ КОНКУРСА:
{grant_analysis[:3000]}

{AI_ZAVOD_CONTEXT}

КОНТЕКСТ РФ — Стратегия развития до 2030-2035:
- Национальные проекты: «Экономика данных», «Кадры», «Молодёжь и дети»
- Цифровая трансформация: госуслуги, здравоохранение, образование, транспорт
- Импортозамещение ПО: реестр отечественного ПО, льготы IT-компаниям
- AI/ML: Национальная стратегия развития ИИ (Указ 490)
- Технологический суверенитет: микроэлектроника, ПО, телеком
- МСП: поддержка малого и среднего бизнеса, цифровизация МСП
- ЕАЭС: единые стандарты, сертификация, таможня

СГЕНЕРИРУЙ 5-7 ИДЕЙ ПРОЕКТОВ для этого конкурса.

Критерии (ВСЕ обязательны):
1. **Быстрая реализация** — MVP за 2-4 недели силами Claude + 1 человек
2. **Минимальные инвестиции** — 0 руб или покрывается из гранта
3. **Минимальные риски** — используем уже готовые модули AI Zavod
4. **Соответствие конкурсу** — точно попадает в требования
5. **Соответствие стратегии РФ 2030/2035** — связь с нацпроектами

Формат каждой идеи:
## Идея [N]: [Название]
- **Суть**: что конкретно делаем (2-3 предложения)
- **Связь с конкурсом**: почему подходит под требования
- **Связь с РФ 2030**: какой нацпроект/стратегию поддерживает
- **Используемые модули AI Zavod**: какие агенты задействованы
- **Срок MVP**: сколько дней/недель
- **Бюджет**: сколько нужно денег (0 = идеально)
- **Риски**: что может пойти не так
- **Ожидаемый результат**: метрики успеха"""
        return await self._call_llm(prompt, max_tokens=4000, temperature=0.6)

    # ─── 4. Генерация Excel-калькуляции ─────────────────────────────────────

    async def generate_budget_json(self, idea_title: str, grant_amount: str, duration: str) -> str:
        """Генерация структуры бюджета в JSON для последующей конвертации в Excel."""
        prompt = f"""Составь детальную смету проекта для грантовой заявки.

ПРОЕКТ: {idea_title}
СУММА ГРАНТА: {grant_amount}
СРОК РЕАЛИЗАЦИИ: {duration}

{AI_ZAVOD_CONTEXT}

Ответь СТРОГО в JSON формате (без markdown):
{{
  "project_title": "название",
  "total_budget": 0,
  "grant_amount": 0,
  "own_funds": 0,
  "duration_months": 0,
  "categories": [
    {{
      "name": "ФОТ (фонд оплаты труда)",
      "items": [
        {{"name": "Руководитель проекта", "unit": "мес", "quantity": 6, "price": 50000, "total": 300000}},
        {{"name": "Разработчик AI/ML", "unit": "мес", "quantity": 6, "price": 80000, "total": 480000}}
      ],
      "subtotal": 780000
    }},
    {{
      "name": "Инфраструктура",
      "items": [
        {{"name": "Облачный сервер (Hetzner)", "unit": "мес", "quantity": 6, "price": 5000, "total": 30000}},
        {{"name": "API Claude (Anthropic)", "unit": "мес", "quantity": 6, "price": 10000, "total": 60000}}
      ],
      "subtotal": 90000
    }},
    {{
      "name": "Прочие расходы",
      "items": [...],
      "subtotal": 0
    }}
  ],
  "timeline": [
    {{"stage": "Этап 1: MVP", "months": "1-2", "deliverables": ["MVP платформы"], "budget": 0}},
    {{"stage": "Этап 2: Тестирование", "months": "3-4", "deliverables": ["Пилот"], "budget": 0}}
  ]
}}

Правила:
- Смету считать близко к верхнему порогу гранта
- ФОТ максимальный в рамках разумного
- Учесть налоги на ФОТ (страховые взносы ~30% или 7.6% для IT)
- Все суммы в рублях
- Итого должно равняться сумме гранта"""
        return await self._call_llm(prompt, max_tokens=3000, temperature=0.2)

    # ─── 5. Генерация документов на подачу ──────────────────────────────────

    async def generate_submission_docs(self, idea_title: str, idea_description: str,
                                        grant_title: str, budget_json: str = "") -> str:
        """Генерация пакета документов для подачи заявки."""
        prompt = f"""Подготовь пакет документов для подачи заявки на грант/конкурс.

КОНКУРС: {grant_title}
ПРОЕКТ: {idea_title}
ОПИСАНИЕ: {idea_description}
БЮДЖЕТ: {budget_json[:2000] if budget_json else 'не указан'}

{AI_ZAVOD_CONTEXT}

Подготовь следующие документы:

## 1. ЗАЯВКА (аннотация проекта)
- Название проекта
- Аннотация (до 500 слов)
- Актуальность и проблема
- Цель и задачи
- Научная/техническая новизна
- Ожидаемые результаты
- Практическая значимость

## 2. ТЕХНИЧЕСКОЕ ЗАДАНИЕ
- Описание текущего состояния
- Требования к результату
- Этапы выполнения
- Критерии приёмки

## 3. ПЛАН РАБОТ
- Этапы с датами и ответственными
- Контрольные точки (milestones)
- Риски и митигация

## 4. ОБОСНОВАНИЕ БЮДЖЕТА
- По каждой статье: зачем нужно, почему такая сумма

## 5. ЧЕК-ЛИСТ ПОДАЧИ
- Все документы для прикрепления
- Форматы и требования
- Кто подписывает"""
        return await self._call_llm(prompt, max_tokens=4000)

    # ─── 6. Генерация общих идей ────────────────────────────────────────────

    async def generate_ideas(self, context: str = "") -> str:
        """Генерация идей заработка (общая, без привязки к конкурсу)."""
        prompt = f"""Ты — стратегический советник IT-стартапа AI Zavod.

{AI_ZAVOD_CONTEXT}

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
        return await self._call_llm(prompt, temperature=0.7)

    # ─── 7. Сводка источников ───────────────────────────────────────────────

    async def scan_sources_summary(self) -> str:
        """Форматированная сводка всех известных источников."""
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

    # ─── 8. Анализ отдельной возможности ────────────────────────────────────

    async def analyze_opportunity(self, opp: Opportunity) -> str:
        """Быстрый анализ найденной возможности."""
        prompt = f"""Проанализируй эту возможность для AI Zavod:

ВОЗМОЖНОСТЬ:
- Название: {opp.title}
- Тип: {opp.type}
- Источник: {opp.source}
- Дедлайн: {opp.deadline or 'не указан'}
- Приз/сумма: {opp.prize or 'не указано'}
- Описание: {opp.description}

{AI_ZAVOD_CONTEXT}

ОТВЕТЬ КРАТКО:
1. Подходит ли нам? (да/нет/частично) и почему
2. Что подать/показать
3. Шансы на победу (низкие/средние/высокие)
4. Конкретные шаги (3-5 пунктов)
5. Потенциальный выигрыш"""
        result = await self._call_llm(prompt, max_tokens=1500)
        opp.ai_analysis = result
        return result

    # ─── Internals ──────────────────────────────────────────────────────────

    async def _search_query(
        self, client: httpx.AsyncClient, query: str
    ) -> list[Opportunity]:
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
        results: list[Opportunity] = []
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

            opp_type = "grant"
            for kw, t in [("хакатон", "hackathon"), ("hackathon", "hackathon"),
                          ("конкурс", "competition"), ("contest", "competition"),
                          ("акселератор", "accelerator"), ("тендер", "tender")]:
                if kw in title.lower() or kw in snippet.lower():
                    opp_type = t
                    break

            results.append(Opportunity(
                title=title, source="DuckDuckGo", url=url,
                type=opp_type, description=snippet,
            ))
        return results

    def _calc_relevance(self, opp: Opportunity) -> float:
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
