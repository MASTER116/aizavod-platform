"""MarketAnalyzer — анализ конкурентов, рынка, идей для заявок.

Использует Claude API для глубокого анализа.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("aizavod.market_analyzer")


class MarketAnalyzer:
    """AI-powered market and competitor analysis."""

    def __init__(self) -> None:
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("ANALYZER_MODEL", "claude-haiku-4-5-20251001")

    async def analyze_competitors(self, niche: str) -> str:
        """Analyze competitors in a specific niche."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Проведи конкурентный анализ для ниши: "{niche}"

Контекст: Zavod-ii — мультиагентная SaaS-платформа для автоматизации бизнес-процессов.
Рынок: Россия, СНГ (ЕАЭС). Стек: FastAPI, Claude API, Telegram-боты.

Ответь по структуре:

## Ключевые конкуренты (5-7 компаний)
Для каждого: название, сайт, что делают, цены, сильные/слабые стороны

## Размер рынка
- TAM / SAM / SOM оценка для РФ
- Темпы роста

## Наше конкурентное преимущество
- Что мы можем сделать лучше/дешевле/быстрее
- Незанятые ниши

## Стратегия входа
- 3 конкретных шага для быстрого старта
- Ценообразование (что ставить на старте)

## Риски
- Главные угрозы и как их митигировать"""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.content[0].text

    async def generate_proposal(self, competition_name: str, description: str) -> str:
        """Generate a competition/grant application idea."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Сгенерируй заявку/идею для конкурса:

КОНКУРС: {competition_name}
ОПИСАНИЕ: {description}

О НАС (Zavod-ii):
- Мультиагентная SaaS-платформа, 37 категорий, 262 отрасли, 148 агентов
- Готовые модули: CERTIFIER (сертификация ТС), Instagram Factory (контент)
- Стек: FastAPI, Claude API, PostgreSQL, Docker, Telegram-боты
- 1 основатель, Россия, Набережные Челны
- Нет ООО (план на август 2026)

НАПИШИ:

## Название проекта
(цепляющее, для жюри)

## Проблема
(какую боль решаем, статистика)

## Решение
(как Zavod-ii решает проблему, технически)

## Уникальность
(чем отличаемся от аналогов)

## Целевая аудитория
(кто платит, сколько их)

## Бизнес-модель
(как зарабатываем)

## Команда
(как подать одного человека + AI как преимущество)

## Дорожная карта
(3-6 месяцев, конкретные milestones)

## Запрашиваемое финансирование
(сколько просить, на что)

## Ожидаемые результаты
(метрики через 6-12 месяцев)"""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return response.content[0].text

    async def quick_market_scan(self, topic: str) -> str:
        """Quick market size and opportunity assessment."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Быстрая оценка рынка для: "{topic}"

Ответь кратко (до 500 слов):
1. Размер рынка в РФ (руб/год)
2. Ключевые игроки (3-5)
3. Есть ли место для нового SaaS?
4. Оптимальная цена входа
5. Где брать первых клиентов
6. Оценка: стоит ли входить (да/нет) и почему"""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.content[0].text


_analyzer: MarketAnalyzer | None = None


def get_analyzer() -> MarketAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = MarketAnalyzer()
    return _analyzer
