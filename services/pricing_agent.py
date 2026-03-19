"""PricingAgent — расчёт цен, генерация КП, оценка проектов.

Помогает правильно оценить стоимость услуг и подготовить
коммерческое предложение для клиента.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("aizavod.pricing_agent")


class PricingAgent:
    """Calculates prices and generates commercial proposals."""

    def __init__(self) -> None:
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("PRICING_MODEL", "claude-haiku-4-5-20251001")

    async def estimate_project(self, description: str) -> str:
        """Estimate project cost, time, and complexity."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Оцени проект как IT-фрилансер с опытом в Python/FastAPI/Telegram-ботах/AI.

ОПИСАНИЕ ПРОЕКТА:
{description}

МОЙ СТЕК:
- Python 3.11+, FastAPI, aiogram 3, SQLAlchemy
- Claude API, GPT API, RAG (BM25)
- PostgreSQL, Redis, Docker
- fal.ai (генерация изображений), Kling (видео)
- Деплой на VPS (Docker Compose)

ОЦЕНИ:

## Сложность
(простой / средний / сложный / очень сложный)

## Срок разработки
(дни — минимум и максимум)

## Стоимость
- Минимум (базовый функционал): ₽
- Оптимум (полный функционал): ₽
- Максимум (с запасом на правки): ₽

## Декомпозиция задач
Пронумерованный список подзадач с оценкой часов на каждую

## Риски
Что может пойти не так, где заложить буфер

## Рекомендация
Какую цену назвать клиенту и почему"""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return response.content[0].text

    async def generate_proposal(self, client_name: str, project_desc: str, price: str = "") -> str:
        """Generate a commercial proposal (КП)."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Напиши коммерческое предложение (КП) для клиента.

КЛИЕНТ: {client_name}
ПРОЕКТ: {project_desc}
{f'БЮДЖЕТ КЛИЕНТА: {price}' if price else ''}

ОТ КОГО: Zavod-ii — разработка AI-решений и автоматизации
ОСНОВАТЕЛЬ: Азат (Python-разработчик, опыт: Telegram-боты, AI-интеграция, FastAPI)

Структура КП:

## Коммерческое предложение

**Для:** {client_name}
**От:** Zavod-ii
**Дата:** [текущая дата]

### Задача
(своими словами, показать понимание)

### Решение
(что мы предлагаем, технически)

### Этапы работ
| Этап | Описание | Срок |
|------|----------|------|
(3-5 этапов)

### Стоимость
(с разбивкой по этапам, итого)

### Что входит
- список того, что получит клиент

### Что НЕ входит
- чтобы избежать scope creep

### Гарантии
- правки, поддержка, SLA

### Следующий шаг
(конкретное действие: встреча, ТЗ, оплата)

Пиши профессионально, но не сухо. Без маркдауна в тексте — только структура."""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.content[0].text


_agent: PricingAgent | None = None


def get_pricing_agent() -> PricingAgent:
    global _agent
    if _agent is None:
        _agent = PricingAgent()
    return _agent
