"""OutreachAgent — холодные продажи, генерация писем, поиск клиентов.

Находит потенциальных клиентов и генерирует персонализированные
письма/сообщения для первого контакта.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("aizavod.outreach_agent")

# Целевые сегменты для холодных продаж
TARGET_SEGMENTS = [
    {
        "segment": "Сертификационные агентства",
        "pain": "Рутинные консультации по ТР ТС отнимают время специалистов",
        "solution": "AI-бот CERTIFIER отвечает на типовые вопросы 24/7",
        "channels": ["email", "telegram", "linkedin"],
        "search_queries": ["сертификация ТС ЕАЭС", "орган по сертификации", "СБКТС оформление"],
    },
    {
        "segment": "Фитнес-тренеры / нутрициологи",
        "pain": "Нет времени на создание контента для Instagram",
        "solution": "AI генерирует 30 постов/месяц с автопубликацией",
        "channels": ["instagram DM", "telegram"],
        "search_queries": ["фитнес тренер инстаграм", "нутрициолог блог"],
    },
    {
        "segment": "Малый бизнес (салоны, клиники, рестораны)",
        "pain": "Нет автоматизации: записи, напоминания, FAQ вручную",
        "solution": "Telegram-бот с записью, напоминаниями, FAQ, оплатой",
        "channels": ["telegram", "email", "avito"],
        "search_queries": ["telegram бот для бизнеса", "автоматизация салона красоты"],
    },
    {
        "segment": "Логистические компании",
        "pain": "Сложности с сертификацией, таможней, документами",
        "solution": "AI-консультант по сертификации + автоматизация документооборота",
        "channels": ["email", "linkedin"],
        "search_queries": ["логистика импорт авто", "таможенный брокер"],
    },
    {
        "segment": "Маркетинговые агентства",
        "pain": "Клиенты хотят AI, а агентство не умеет",
        "solution": "White-label AI-решения: боты, генерация контента, аналитика",
        "channels": ["email", "telegram", "linkedin"],
        "search_queries": ["маркетинговое агентство", "digital агентство"],
    },
]


class OutreachAgent:
    """Generates outreach messages and finds potential clients."""

    def __init__(self) -> None:
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("OUTREACH_MODEL", "claude-haiku-4-5-20251001")

    async def list_segments(self) -> str:
        """Return formatted list of target segments."""
        lines = ["<b>Целевые сегменты для продаж:</b>\n"]
        for i, seg in enumerate(TARGET_SEGMENTS, 1):
            lines.append(
                f"<b>{i}. {seg['segment']}</b>\n"
                f"   Боль: {seg['pain']}\n"
                f"   Решение: {seg['solution']}\n"
                f"   Каналы: {', '.join(seg['channels'])}\n"
            )
        return "\n".join(lines)

    async def generate_cold_message(
        self, segment: str, channel: str = "email", context: str = ""
    ) -> str:
        """Generate a personalized cold outreach message."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        # Find matching segment
        seg_info = None
        for s in TARGET_SEGMENTS:
            if segment.lower() in s["segment"].lower():
                seg_info = s
                break

        import anthropic

        prompt = f"""Напиши холодное сообщение для первого контакта с потенциальным клиентом.

СЕГМЕНТ: {segment}
{f'БОЛЬ КЛИЕНТА: {seg_info["pain"]}' if seg_info else ''}
{f'НАШЕ РЕШЕНИЕ: {seg_info["solution"]}' if seg_info else ''}
КАНАЛ: {channel}
{f'ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ: {context}' if context else ''}

О НАС:
AI Zavod — разработка AI-решений для бизнеса.
Готовые продукты: AI-консультант, генерация контента, Telegram-боты.

ПРАВИЛА:
1. Короткое (до 150 слов для email, до 80 для telegram/instagram)
2. Начни с боли клиента, не с себя
3. Конкретное предложение (не "давайте поговорим")
4. Призыв к действию (демо, бесплатный аудит, пробный период)
5. Без агрессивных продаж, без "уникальное предложение"
6. Человечный тон, без корпоративного булшита

Если канал = email — добавь тему письма.
Если канал = telegram — формат сообщения в ТГ.
Если канал = instagram — формат DM."""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.content[0].text

    async def find_leads(self, segment: str) -> str:
        """Search for potential clients in a segment."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Помоги найти потенциальных клиентов в сегменте: "{segment}"

Контекст: мы продаём AI-решения для бизнеса в России.
У нас нет бюджета на рекламу. Только органические каналы.

Дай конкретный план:

## Где искать клиентов (10 конкретных мест)
Формат: [Канал] — [Конкретное действие] — [Ожидаемый результат]

## Готовые площадки для размещения
- Каталоги, агрегаторы, маркетплейсы (с ссылками)

## Telegram-каналы и группы
- 5-10 конкретных каналов/групп по теме (название, примерный размер)

## Стратегия первого контакта
- Что писать, когда, как часто
- Как не попасть в бан за спам

## План на первую неделю
Пн-Пт: конкретные действия по дням"""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return response.content[0].text


_agent: OutreachAgent | None = None


def get_outreach_agent() -> OutreachAgent:
    global _agent
    if _agent is None:
        _agent = OutreachAgent()
    return _agent
