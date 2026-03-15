"""Хендлеры раздела «Продажи и фриланс» — кнопки callback."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.keyboards import back_to_sales_kb

logger = logging.getLogger("aizavod.bot.sales")

router = Router()

MAX_TG_MSG = 4000


class SalesStates(StatesGroup):
    waiting_response_input = State()
    waiting_estimate_input = State()
    waiting_kp_input = State()
    waiting_coldmsg_input = State()
    waiting_leads_input = State()


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


# ─── Фриланс ────────────────────────────────────────────────────────────


@router.callback_query(F.data == "sales_freelance")
async def cb_freelance(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🔎 Ищу заказы на фрилансе...")

    from services.freelance_agent import get_freelance_agent
    agent = get_freelance_agent()
    orders = await agent.search_orders()

    if not orders:
        await callback.message.answer("Заказы не найдены.", reply_markup=back_to_sales_kb())
        return

    lines = [f"Найдено: <b>{len(orders)}</b> заказов\n"]
    for i, o in enumerate(orders[:10], 1):
        score = "🟢" if o.match_score > 0.6 else "🟡" if o.match_score > 0.3 else "⚪"
        lines.append(f"{score} <b>{i}. {o.title[:80]}</b>")
        if o.match_service:
            lines.append(f"   Подходит: {o.match_service}")
        if o.budget:
            lines.append(f"   Бюджет: {o.budget}")
        lines.append(f"   <a href=\"{o.url}\">Ссылка</a> | {o.platform}\n")

    text = "\n".join(lines)[:MAX_TG_MSG]
    await callback.message.answer(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_to_sales_kb())


@router.callback_query(F.data == "sales_response")
async def cb_response_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SalesStates.waiting_response_input)
    await callback.message.answer(
        "✍️ Опиши заказ, на который нужен отклик:\n\n"
        "Пример: <i>Нужен Telegram-бот для записи в салон красоты</i>",
        parse_mode="HTML",
    )


@router.message(SalesStates.waiting_response_input)
async def on_response_input(message: Message, state: FSMContext):
    await state.clear()
    text = message.text.strip()
    await message.answer("✍️ Генерирую отклик...")

    from services.freelance_agent import get_freelance_agent, FreelanceOrder
    agent = get_freelance_agent()
    order = FreelanceOrder(title=text, platform="Ручной ввод", url="")
    response = await agent.generate_response(order)

    for part in _split(response):
        await message.answer(part)
    await message.answer("⬆️ Отклик выше. Скопируй и отправь клиенту.", reply_markup=back_to_sales_kb())


@router.callback_query(F.data == "sales_kwork")
async def cb_kwork(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🏷 Генерирую описания 5 услуг для Kwork...")

    from services.freelance_agent import get_freelance_agent
    agent = get_freelance_agent()
    result = await agent.create_kwork_services()

    for part in _split(result):
        await callback.message.answer(part)
    await callback.message.answer("⬆️ Описания выше", reply_markup=back_to_sales_kb())


@router.callback_query(F.data == "sales_services")
async def cb_services(callback: CallbackQuery):
    await callback.answer()
    from services.freelance_agent import get_freelance_agent
    agent = get_freelance_agent()
    result = await agent.list_services()
    await callback.message.answer(result, parse_mode="HTML", reply_markup=back_to_sales_kb())


# ─── Ценообразование ────────────────────────────────────────────────────


@router.callback_query(F.data == "sales_estimate")
async def cb_estimate_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SalesStates.waiting_estimate_input)
    await callback.message.answer(
        "💵 Опиши проект для оценки:\n\n"
        "Пример: <i>Telegram-бот для клиники с записью и оплатой через ЮKassa</i>",
        parse_mode="HTML",
    )


@router.message(SalesStates.waiting_estimate_input)
async def on_estimate_input(message: Message, state: FSMContext):
    await state.clear()
    desc = message.text.strip()
    await message.answer("💵 Оцениваю проект...")

    from services.pricing_agent import get_pricing_agent
    agent = get_pricing_agent()
    result = await agent.estimate_project(desc)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Оценка выше", reply_markup=back_to_sales_kb())


@router.callback_query(F.data == "sales_kp")
async def cb_kp_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SalesStates.waiting_kp_input)
    await callback.message.answer(
        "📄 Введи данные для КП:\n\n"
        "Формат: <b>Имя клиента | Описание проекта</b>\n"
        "Пример: <i>ООО Ромашка | Бот для записи + CRM</i>",
        parse_mode="HTML",
    )


@router.message(SalesStates.waiting_kp_input)
async def on_kp_input(message: Message, state: FSMContext):
    await state.clear()
    text = message.text.strip()
    if "|" not in text:
        await message.answer("Нужен формат: Клиент | Проект", reply_markup=back_to_sales_kb())
        return

    parts = text.split("|", 1)
    client_name = parts[0].strip()
    project = parts[1].strip()

    await message.answer(f"📄 Готовлю КП для {client_name}...")

    from services.pricing_agent import get_pricing_agent
    agent = get_pricing_agent()
    result = await agent.generate_proposal(client_name, project)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ КП выше", reply_markup=back_to_sales_kb())


# ─── Продажи ────────────────────────────────────────────────────────────


@router.callback_query(F.data == "sales_segments")
async def cb_segments(callback: CallbackQuery):
    await callback.answer()
    from services.outreach_agent import get_outreach_agent
    agent = get_outreach_agent()
    result = await agent.list_segments()
    await callback.message.answer(result, parse_mode="HTML", reply_markup=back_to_sales_kb())


@router.callback_query(F.data == "sales_coldmsg")
async def cb_coldmsg_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SalesStates.waiting_coldmsg_input)
    await callback.message.answer(
        "📨 Для кого холодное письмо?\n\n"
        "Формат: <b>Сегмент | Канал</b>\n"
        "Пример: <i>Фитнес-тренеры | telegram</i>\n"
        "Каналы: email, telegram, instagram",
        parse_mode="HTML",
    )


@router.message(SalesStates.waiting_coldmsg_input)
async def on_coldmsg_input(message: Message, state: FSMContext):
    await state.clear()
    text = message.text.strip()
    parts = text.split("|", 1)
    segment = parts[0].strip()
    channel = parts[1].strip() if len(parts) > 1 else "email"

    await message.answer(f"📨 Генерирую сообщение для: {segment}...")

    from services.outreach_agent import get_outreach_agent
    agent = get_outreach_agent()
    result = await agent.generate_cold_message(segment, channel)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Письмо выше", reply_markup=back_to_sales_kb())


@router.callback_query(F.data == "sales_leads")
async def cb_leads_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SalesStates.waiting_leads_input)
    await callback.message.answer(
        "📍 Какой сегмент?\n\n"
        "Пример: <i>салоны красоты</i>",
        parse_mode="HTML",
    )


@router.message(SalesStates.waiting_leads_input)
async def on_leads_input(message: Message, state: FSMContext):
    await state.clear()
    segment = message.text.strip()
    await message.answer(f"📍 Ищу каналы привлечения для: {segment}...")

    from services.outreach_agent import get_outreach_agent
    agent = get_outreach_agent()
    result = await agent.find_leads(segment)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ План выше", reply_markup=back_to_sales_kb())
