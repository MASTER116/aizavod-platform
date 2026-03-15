"""CONDUCTOR handler — свободный ввод текста маршрутизируется к нужному агенту."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

from telegram_bot.keyboards import main_menu_kb

logger = logging.getLogger("aizavod.bot.conductor")

router = Router()

MAX_TG_MSG = 4000

DEPT_EMOJI = {
    "CEO": "🧠",
    "Финансы": "💰",
    "Продажи": "🛒",
    "Контент": "📱",
    "Продукт": "📋",
    "Юридический": "⚖️",
    "Бухгалтерия": "🧮",
    "Самообучение": "🧬",
    "Безопасность": "🛡",
    "Наука": "🎓",
    "DevRel": "📢",
    "Нейминг": "✏️",
    "IP/Патенты": "🔒",
    "Голос": "🎙",
    "Финансы/Казначей": "💵",
}


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
    """Любое текстовое сообщение без команды — маршрутизируем через CONDUCTOR."""
    if not message.text:
        return

    query = message.text.strip()
    if not query or query.startswith("/"):
        return

    emoji = "🔄"
    await message.answer(f"{emoji} CONDUCTOR анализирует запрос...")

    from services.conductor import get_conductor
    conductor = get_conductor()
    result = await conductor.process(query)

    dept_emoji = DEPT_EMOJI.get(result.department, "🤖")

    header = (
        f"{dept_emoji} <b>{result.department}</b> → {result.agent_name}\n"
        f"Уверенность: {result.route.confidence:.0%} | {result.route.reasoning}\n"
        f"⏱ {result.duration_ms:.0f}ms\n"
        f"{'─' * 30}\n\n"
    )

    full_text = header + result.response

    for part in _split(full_text):
        await message.answer(part, parse_mode="HTML")

    # Вторичные ответы
    if result.secondary_responses:
        for agent_name, resp in result.secondary_responses.items():
            sec_header = f"\n📎 <b>Дополнительно ({agent_name})</b>\n{'─' * 20}\n\n"
            for part in _split(sec_header + resp):
                await message.answer(part, parse_mode="HTML")

    await message.answer("⬆️ Ответ CONDUCTOR", reply_markup=main_menu_kb())
