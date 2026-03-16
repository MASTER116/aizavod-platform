"""Хендлеры раздела «Задача / Запрос» — Генеральный директор (оркестратор)."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.keyboards import back_to_main_kb, task_menu_kb

logger = logging.getLogger("aizavod.bot.ceo")

router = Router()

MAX_TG_MSG = 4000


class CEOStates(StatesGroup):
    waiting_question = State()
    waiting_task = State()


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


@router.callback_query(F.data == "task_ask")
async def cb_ask_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CEOStates.waiting_question)
    await callback.message.answer(
        "🧠 Задай вопрос Генеральному директору.\n\n"
        "Я проанализирую и дам рекомендацию с распределением по директорам.\n\n"
        "Примеры:\n"
        "• <i>Как заработать первые 10 000 руб. за неделю?</i>\n"
        "• <i>Стоит ли подавать на грант ФАСИ?</i>\n"
        "• <i>Какой модуль разработать следующим?</i>",
        parse_mode="HTML",
    )


@router.message(CEOStates.waiting_question)
async def on_question(message: Message, state: FSMContext):
    await state.clear()
    question = message.text.strip()

    await message.answer("🧠 Анализирую...")

    from services.ceo_agent import get_ceo_agent
    ceo = get_ceo_agent()
    result = await ceo.process_question(question)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Ответ Генеральный директора", reply_markup=task_menu_kb())


@router.callback_query(F.data == "task_assign")
async def cb_task_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CEOStates.waiting_task)
    await callback.message.answer(
        "📋 Поставь задачу.\n\n"
        "Генеральный директор разобьёт её на подзадачи и распределит между директорами.\n\n"
        "Примеры:\n"
        "• <i>Найти 3 клиентов на Telegram-ботов</i>\n"
        "• <i>Подготовить заявку на Цифровой прорыв</i>\n"
        "• <i>Запустить продажи на Kwork</i>",
        parse_mode="HTML",
    )


@router.message(CEOStates.waiting_task)
async def on_task(message: Message, state: FSMContext):
    await state.clear()
    task = message.text.strip()

    await message.answer("📋 Составляю план...")

    from services.ceo_agent import get_ceo_agent
    ceo = get_ceo_agent()
    result = await ceo.assign_task(task)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ План выполнения", reply_markup=task_menu_kb())


@router.callback_query(F.data == "task_strategy")
async def cb_strategy(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🔄 Составляю стратегию...")

    from services.ceo_agent import get_ceo_agent
    ceo = get_ceo_agent()
    result = await ceo.strategic_plan()

    for part in _split(result):
        await callback.message.answer(part)
    await callback.message.answer("⬆️ Стратегический план", reply_markup=task_menu_kb())
