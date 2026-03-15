"""Хендлеры раздела «Юрист / Бухгалтер» — кнопки callback."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.keyboards import back_to_legal_kb

logger = logging.getLogger("aizavod.bot.legal")

router = Router()

MAX_TG_MSG = 4000


class LegalStates(StatesGroup):
    waiting_legal_consult = State()
    waiting_contract = State()
    waiting_ip_reg = State()
    waiting_labor = State()
    waiting_acc_consult = State()
    waiting_tax_compare = State()
    waiting_payroll = State()


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


# ─── Юрист ───────────────────────────────────────────────────────────────


@router.callback_query(F.data == "legal_consult")
async def cb_legal_consult(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(LegalStates.waiting_legal_consult)
    await callback.message.answer(
        "⚖️ Задай юридический вопрос:\n\n"
        "Примеры:\n"
        "• <i>Нужна ли лицензия для IT-компании?</i>\n"
        "• <i>Как расторгнуть договор аренды досрочно?</i>\n"
        "• <i>Ответственность директора ООО</i>",
        parse_mode="HTML",
    )


@router.message(LegalStates.waiting_legal_consult)
async def on_legal_consult(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⚖️ Юрист анализирует вопрос...")
    from services.lawyer_agent import get_lawyer_agent
    agent = get_lawyer_agent()
    result = await agent.consult(message.text.strip())
    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Консультация юриста", reply_markup=back_to_legal_kb())


@router.callback_query(F.data == "legal_contract")
async def cb_legal_contract(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(LegalStates.waiting_contract)
    await callback.message.answer(
        "📄 Опиши договор для анализа:\n\n"
        "Пример: <i>Договор аренды офиса, арендодатель ООО, срок 1 год, "
        "предоплата 2 месяца, штраф за досрочное расторжение 3 месяца</i>",
        parse_mode="HTML",
    )


@router.message(LegalStates.waiting_contract)
async def on_contract(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📄 Анализирую договор...")
    from services.lawyer_agent import get_lawyer_agent
    agent = get_lawyer_agent()
    result = await agent.check_contract(message.text.strip())
    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Анализ договора", reply_markup=back_to_legal_kb())


@router.callback_query(F.data == "legal_ip_reg")
async def cb_ip_reg(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(LegalStates.waiting_ip_reg)
    await callback.message.answer(
        "📝 Какой вид деятельности?\n\n"
        "Пример: <i>Разработка Telegram-ботов и AI-сервисов</i>",
        parse_mode="HTML",
    )


@router.message(LegalStates.waiting_ip_reg)
async def on_ip_reg(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📝 Готовлю инструкцию по регистрации ИП...")
    from services.lawyer_agent import get_lawyer_agent
    agent = get_lawyer_agent()
    result = await agent.ip_registration(message.text.strip())
    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Инструкция выше", reply_markup=back_to_legal_kb())


@router.callback_query(F.data == "legal_labor")
async def cb_labor(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(LegalStates.waiting_labor)
    await callback.message.answer(
        "👷 Задай вопрос по трудовому праву:\n\n"
        "Примеры:\n"
        "• <i>Как оформить сотрудника по ГПХ?</i>\n"
        "• <i>Сколько дней отпуска положено?</i>",
        parse_mode="HTML",
    )


@router.message(LegalStates.waiting_labor)
async def on_labor(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👷 Анализирую вопрос по ТК РФ...")
    from services.lawyer_agent import get_lawyer_agent
    agent = get_lawyer_agent()
    result = await agent.labor_law(message.text.strip())
    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Ответ выше", reply_markup=back_to_legal_kb())


# ─── Бухгалтер ───────────────────────────────────────────────────────────


@router.callback_query(F.data == "acc_consult")
async def cb_acc_consult(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(LegalStates.waiting_acc_consult)
    await callback.message.answer(
        "🧮 Задай вопрос по налогам/бухгалтерии:\n\n"
        "Примеры:\n"
        "• <i>Какие взносы платит ИП на УСН 6%?</i>\n"
        "• <i>Нужна ли онлайн-касса для IT-услуг?</i>",
        parse_mode="HTML",
    )


@router.message(LegalStates.waiting_acc_consult)
async def on_acc_consult(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🧮 Бухгалтер считает...")
    from services.accountant_agent import get_accountant_agent
    agent = get_accountant_agent()
    result = await agent.consult(message.text.strip())
    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Ответ выше", reply_markup=back_to_legal_kb())


@router.callback_query(F.data == "acc_tax_compare")
async def cb_tax_compare(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(LegalStates.waiting_tax_compare)
    await callback.message.answer(
        "📊 Опиши бизнес для сравнения систем налогообложения:\n\n"
        "Формат: <b>Деятельность | Выручка/мес | Расходы/мес</b>\n"
        "Пример: <i>IT-услуги | 200 000 руб | 50 000 руб</i>",
        parse_mode="HTML",
    )


@router.message(LegalStates.waiting_tax_compare)
async def on_tax_compare(message: Message, state: FSMContext):
    await state.clear()
    text = message.text.strip()
    parts = text.split("|")
    activity = parts[0].strip() if parts else text
    revenue = parts[1].strip() if len(parts) > 1 else "не указана"
    expenses = parts[2].strip() if len(parts) > 2 else "не указаны"

    await message.answer("📊 Сравниваю системы налогообложения...")
    from services.accountant_agent import get_accountant_agent
    agent = get_accountant_agent()
    result = await agent.compare_tax_systems(revenue, expenses, activity)
    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Сравнение выше", reply_markup=back_to_legal_kb())


@router.callback_query(F.data == "acc_calendar")
async def cb_calendar(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("📅 Составляю календарь отчетности для ИП УСН 6%...")
    from services.accountant_agent import get_accountant_agent
    agent = get_accountant_agent()
    result = await agent.reporting_calendar("ИП УСН 6%")
    for part in _split(result):
        await callback.message.answer(part)
    await callback.message.answer("⬆️ Календарь выше", reply_markup=back_to_legal_kb())


@router.callback_query(F.data == "acc_payroll")
async def cb_payroll(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(LegalStates.waiting_payroll)
    await callback.message.answer(
        "💰 Укажи оклад сотрудника:\n\n"
        "Пример: <i>80 000 руб</i>",
        parse_mode="HTML",
    )


@router.message(LegalStates.waiting_payroll)
async def on_payroll(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("💰 Рассчитываю зарплатные налоги...")
    from services.accountant_agent import get_accountant_agent
    agent = get_accountant_agent()
    result = await agent.payroll_calc(message.text.strip())
    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Расчет выше", reply_markup=back_to_legal_kb())
