"""Обработчик свободного текста — прямой вызов Claude API."""
from __future__ import annotations

import logging
import os

import anthropic
from aiogram import Router
from aiogram.types import Message

from telegram_bot.keyboards import main_menu_kb

logger = logging.getLogger("aizavod.bot.conductor")

router = Router()

MAX_TG_MSG = 4000

SYSTEM_PROMPT = """Ты — AI-консультант платформы AI Zavod. Платформа предоставляет AI-агентов для автоматизации бизнеса.

Доступные AI-агенты (148 штук в 37 категориях):
- Юрист (договоры, регистрация ИП/ООО, трудовое право)
- Бухгалтер (налоги, отчётность, зарплата)
- Маркетолог (контент, SMM, email-рассылки)
- Менеджер продаж (холодные звонки, лиды, CRM)
- Сертификатор (ТР ТС, ЕАЭС, таможня)
- HR-агент (найм, онбординг, обучение)
- Аналитик рынка (конкуренты, ниши, тренды)
- Копирайтер (тексты, посты, сценарии)
- Голосовой агент (колл-центр, TTS, скрипты звонков)
- Финансист (бюджет, cash flow, инвестиции)
- Разработчик (боты, сайты, автоматизация)
- Дизайнер (UI/UX, брендинг, логотипы)
- И другие специализированные агенты

ПРАВИЛА ОТВЕТА:
1. Отвечай КРАТКО — максимум 5-7 строк
2. Формат ответа:
   👥 Нужные агенты: [перечисли 2-4 агента]
   💰 Подключение: [цена в рублях]
   📉 Экономия: [сколько сэкономит в год]
   🔗 Собрать команду: https://aizavod.ru/build
3. Цены подключения:
   - 1 агент: 5 000 ₽/мес
   - Пакет 3 агента: 12 000 ₽/мес
   - Пакет 5 агентов: 18 000 ₽/мес
   - Безлимит (все агенты): 45 000 ₽/мес
4. Экономию считай как замену штатного сотрудника (ЗП 60-150К + налоги 30%)
5. НЕ пиши длинные описания, технические детали, сложности проекта
6. НЕ оценивай сложность — просто скажи какие агенты нужны и сколько стоит
7. Отвечай на русском языке
"""


def _split(text: str, limit: int = MAX_TG_MSG) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            if current:
                parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)
    return parts


@router.message()
async def on_free_text(message: Message):
    """Любое текстовое сообщение — прямой вызов Claude API."""
    if not message.text:
        return

    query = message.text.strip()
    if not query or query.startswith("/"):
        return

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        await message.answer("❌ API ключ не настроен")
        return

    await message.answer("🔄 Анализирую запрос...")

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": query}],
            temperature=0.3,
        )
        answer = resp.content[0].text.strip()
    except Exception as e:
        logger.error("Claude API error: %s", e)
        await message.answer(f"❌ Ошибка: {e}")
        return

    for part in _split(answer):
        await message.answer(part)

    await message.answer("⬆️ Ответ AI Zavod", reply_markup=main_menu_kb())
