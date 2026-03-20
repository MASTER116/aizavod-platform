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
    "Руководство": "🧠",
    "Финансы": "💰",
    "Продажи": "🛒",
    "Контент": "📱",
    "Продукт": "📋",
    "Юридический": "⚖️",
    "Бухгалтерия": "🧮",
    "Самообучение": "🧬",
    "Безопасность": "🛡",
    "Наука": "🎓",
    "Продвижение": "📢",
    "Нейминг": "✏️",
    "Патенты": "🔒",
    "Голос": "🎙",
    "Казначейство": "💵",
    "Хакатоны": "🏆",
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


    from services.conductor import get_conductor
    conductor = get_conductor()

    # Определить режим: оркестрация или роутер
    mode = conductor._detect_mode(query)

    if mode == "orchestrator":
        await _handle_orchestrate(message, query, conductor)
    else:
        await _handle_route(message, query, conductor)


async def _handle_route(message: Message, query: str, conductor):
    """Режим роутера — направить к одному агенту."""
    await message.answer("🔄 Анализирую запрос...")

    user_id = message.from_user.id if message.from_user else None
    result = await conductor.process(query, user_id=user_id, user_tier="pro")

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

    await message.answer("⬆️ Готово", reply_markup=main_menu_kb())


async def _handle_orchestrate(message: Message, task: str, conductor):
    """Режим оркестратора — полная 3-уровневая декомпозиция."""
    await message.answer(
        "🏗 <b>Декомпозиция задачи</b>\n\n"
        "Разбиваю на подзадачи:\n"
        f"<i>{task[:200]}</i>\n\n"
        "Это займёт 15-30 секунд...",
        parse_mode="HTML",
    )

    try:
        tree = await conductor.orchestrate(task, depth=3)
    except Exception as e:
        logger.error("Ошибка оркестрации: %s", e)
        await message.answer(f"❌ Ошибка: {e}")
        return

    if tree.get("status") == "error":
        await message.answer(f"❌ {tree.get('message', 'Ошибка декомпозиции')}")
        return

    # Форматируем дерево для Telegram
    lines = [
        f"📋 <b>Задача:</b> {task[:150]}",
        f"📊 <b>Анализ:</b> {tree.get('analysis', '')[:200]}",
        f"⏱ {tree.get('duration_ms', 0):.0f}ms",
        "",
    ]

    for d in tree.get("directors", []):
        role = d.get("role", "?")
        lines.append(f"👔 <b>{d.get('title', role)}</b>")
        lines.append(f"   {d.get('task', '')[:100]}")

        for dept in d.get("departments", []):
            dept_name = dept.get("department", "?")
            lines.append(f"   📁 {dept_name}: {dept.get('task', '')[:80]}")

            for spec in dept.get("specialists", []):
                spec_name = spec.get("specialist", "?")
                lines.append(f"      👤 {spec_name}: {spec.get('task', '')[:60]}")

        lines.append("")

    # Отчёт
    report = tree.get("report", {})
    if report:
        lines.append("─" * 30)
        lines.append(f"📊 <b>Итог:</b> {report.get('summary', '')[:200]}")
        for h in report.get("highlights", [])[:3]:
            lines.append(f"  ✅ {h[:80]}")
        for ns in report.get("next_steps", [])[:3]:
            lines.append(f"  ➡️ {ns[:80]}")

    # Токены CEO + стоимость
    tokens = tree.get("tokens", {})
    if tokens.get("total", 0) > 0:
        inp = tokens.get("input", 0)
        out = tokens.get("output", 0)
        total = tokens.get("total", 0)
        # Claude Haiku 4.5: $0.80/1M input, $4.00/1M output
        cost_usd = (inp * 0.80 + out * 4.00) / 1_000_000
        lines.append("")
        lines.append(
            f"🔢 <b>Токены:</b> {inp:,} in + {out:,} out = {total:,} total"
        )
        lines.append(f"💲 <b>Стоимость:</b> ${cost_usd:.4f}")

    full_text = "\n".join(lines)

    for part in _split(full_text):
        await message.answer(part, parse_mode="HTML")

    await message.answer("⬆️ Декомпозиция завершена", reply_markup=main_menu_kb())
