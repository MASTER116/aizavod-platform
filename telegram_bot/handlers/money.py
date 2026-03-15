"""Telegram-команды для агентов заработка.

Фриланс:
  /freelance — поиск заказов на фрилансе
  /response заказ — сгенерировать отклик
  /kwork — сгенерировать описания услуг для Kwork
  /services — наши услуги и цены

Ценообразование:
  /estimate описание — оценить проект (сроки, цена)
  /kp клиент | проект — коммерческое предложение

Продажи:
  /segments — целевые сегменты клиентов
  /coldmsg сегмент | канал — холодное письмо
  /leads сегмент — где искать клиентов
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger("aizavod.bot.money")

router = Router()

MAX_TG_MSG = 4000


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


async def _send(message: Message, text: str, **kwargs):
    for part in _split(text):
        await message.answer(part, **kwargs)


# ─── Фриланс ────────────────────────────────────────────────────────────


@router.message(Command("freelance"))
async def cmd_freelance(message: Message):
    """Поиск заказов на фрилансе."""
    await message.answer("Ищу подходящие заказы на фрилансе...")

    from services.freelance_agent import get_freelance_agent
    agent = get_freelance_agent()

    query = message.text.replace("/freelance", "").strip()
    orders = await agent.search_orders(query)

    if not orders:
        await message.answer("Заказы не найдены. Попробуй: /freelance telegram бот")
        return

    lines = [f"Найдено: {len(orders)} заказов\n"]
    for i, o in enumerate(orders[:10], 1):
        score = "🟢" if o.match_score > 0.6 else "🟡" if o.match_score > 0.3 else "⚪"
        lines.append(f"{score} <b>{i}. {o.title[:80]}</b>")
        if o.match_service:
            lines.append(f"   Подходит: {o.match_service}")
        if o.budget:
            lines.append(f"   Бюджет: {o.budget}")
        if o.description:
            lines.append(f"   {o.description[:120]}")
        lines.append(f"   <a href=\"{o.url}\">Ссылка</a> | {o.platform}\n")

    await message.answer(
        "\n".join(lines)[:MAX_TG_MSG],
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command("response"))
async def cmd_response(message: Message):
    """Сгенерировать отклик на фриланс-заказ."""
    text = message.text.replace("/response", "").strip()
    if not text:
        await message.answer(
            "Формат: /response Описание заказа\n"
            "Пример: /response Нужен Telegram-бот для записи в салон красоты"
        )
        return

    await message.answer("Генерирую отклик...")

    from services.freelance_agent import get_freelance_agent, FreelanceOrder
    agent = get_freelance_agent()

    order = FreelanceOrder(title=text, platform="Ручной ввод", url="")
    response = await agent.generate_response(order)
    await _send(message, response)


@router.message(Command("kwork"))
async def cmd_kwork(message: Message):
    """Сгенерировать описания услуг для Kwork."""
    await message.answer("Генерирую описания 5 услуг для Kwork...")

    from services.freelance_agent import get_freelance_agent
    agent = get_freelance_agent()
    result = await agent.create_kwork_services()
    await _send(message, result)


@router.message(Command("services"))
async def cmd_services(message: Message):
    """Наши услуги."""
    from services.freelance_agent import get_freelance_agent
    agent = get_freelance_agent()
    result = await agent.list_services()
    await message.answer(result, parse_mode="HTML")


# ─── Ценообразование ────────────────────────────────────────────────────


@router.message(Command("estimate"))
async def cmd_estimate(message: Message):
    """Оценить проект (сроки + цена)."""
    desc = message.text.replace("/estimate", "").strip()
    if not desc:
        await message.answer(
            "Формат: /estimate Описание проекта\n"
            "Пример: /estimate Telegram-бот для записи в клинику с оплатой через ЮKassa"
        )
        return

    await message.answer("Оцениваю проект...")

    from services.pricing_agent import get_pricing_agent
    agent = get_pricing_agent()
    result = await agent.estimate_project(desc)
    await _send(message, result)


@router.message(Command("kp"))
async def cmd_kp(message: Message):
    """Коммерческое предложение."""
    text = message.text.replace("/kp", "").strip()
    if not text or "|" not in text:
        await message.answer(
            "Формат: /kp Имя клиента | Описание проекта\n"
            "Пример: /kp ООО Ромашка | Бот для записи клиентов + CRM"
        )
        return

    parts = text.split("|", 1)
    client_name = parts[0].strip()
    project = parts[1].strip()

    await message.answer(f"Готовлю КП для {client_name}...")

    from services.pricing_agent import get_pricing_agent
    agent = get_pricing_agent()
    result = await agent.generate_proposal(client_name, project)
    await _send(message, result)


# ─── Продажи ────────────────────────────────────────────────────────────


@router.message(Command("segments"))
async def cmd_segments(message: Message):
    """Целевые сегменты."""
    from services.outreach_agent import get_outreach_agent
    agent = get_outreach_agent()
    result = await agent.list_segments()
    await message.answer(result, parse_mode="HTML")


@router.message(Command("coldmsg"))
async def cmd_coldmsg(message: Message):
    """Холодное сообщение для клиента."""
    text = message.text.replace("/coldmsg", "").strip()
    if not text:
        await message.answer(
            "Формат: /coldmsg сегмент | канал\n"
            "Пример: /coldmsg Фитнес-тренеры | telegram\n"
            "Каналы: email, telegram, instagram"
        )
        return

    parts = text.split("|", 1)
    segment = parts[0].strip()
    channel = parts[1].strip() if len(parts) > 1 else "email"

    await message.answer(f"Генерирую сообщение для: {segment}...")

    from services.outreach_agent import get_outreach_agent
    agent = get_outreach_agent()
    result = await agent.generate_cold_message(segment, channel)
    await _send(message, result)


@router.message(Command("leads"))
async def cmd_leads(message: Message):
    """Где искать клиентов."""
    segment = message.text.replace("/leads", "").strip()
    if not segment:
        await message.answer(
            "Формат: /leads сегмент\n"
            "Пример: /leads салоны красоты"
        )
        return

    await message.answer(f"Ищу каналы привлечения для: {segment}...")

    from services.outreach_agent import get_outreach_agent
    agent = get_outreach_agent()
    result = await agent.find_leads(segment)
    await _send(message, result)
