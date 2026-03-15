"""Хендлеры раздела «Привлечь инвестиции» — кнопки callback."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.keyboards import back_to_money_kb, money_menu_kb

logger = logging.getLogger("aizavod.bot.opportunities")

router = Router()

MAX_TG_MSG = 4000


class MoneyStates(StatesGroup):
    waiting_proposal_input = State()
    waiting_market_input = State()
    waiting_competitors_input = State()


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


@router.callback_query(F.data == "money_scan")
async def cb_scan(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🔍 Сканирую гранты, хакатоны, конкурсы...")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    results = await scanner.scan_web()

    if not results:
        await callback.message.answer("Ничего не найдено.", reply_markup=back_to_money_kb())
        return

    lines = [f"Найдено: <b>{len(results)}</b> возможностей\n"]
    for i, r in enumerate(results[:10], 1):
        rel = "🟢" if r.relevance_score > 0.6 else "🟡" if r.relevance_score > 0.3 else "⚪"
        lines.append(f"{rel} <b>{i}. {r.title[:80]}</b>")
        if r.description:
            lines.append(f"   {r.description[:120]}")
        lines.append(f"   <a href=\"{r.url}\">Ссылка</a> | {r.type}\n")

    text = "\n".join(lines)[:MAX_TG_MSG]
    await callback.message.answer(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_to_money_kb())


@router.callback_query(F.data == "money_ideas")
async def cb_ideas(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("💡 Генерирую идеи для заработка...")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    ideas = await scanner.generate_ideas()

    for part in _split(ideas):
        await callback.message.answer(part)
    await callback.message.answer("⬆️ Идеи выше", reply_markup=back_to_money_kb())


@router.callback_query(F.data == "money_proposal")
async def cb_proposal_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(MoneyStates.waiting_proposal_input)
    await callback.message.answer(
        "📝 Напиши название конкурса и описание:\n\n"
        "Формат: <b>Название | Описание</b>\n"
        "Пример: <i>Цифровой прорыв | Хакатон по ИИ, приз 3 млн</i>",
        parse_mode="HTML",
    )


@router.message(MoneyStates.waiting_proposal_input)
async def on_proposal_input(message: Message, state: FSMContext):
    await state.clear()
    text = message.text.strip()
    parts = text.split("|", 1)
    name = parts[0].strip()
    desc = parts[1].strip() if len(parts) > 1 else ""

    await message.answer(f"📝 Готовлю заявку на: {name}...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.generate_proposal(name, desc)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Заявка выше", reply_markup=back_to_money_kb())


@router.callback_query(F.data == "money_market")
async def cb_market_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(MoneyStates.waiting_market_input)
    await callback.message.answer(
        "📈 Какой рынок проанализировать?\n\n"
        "Пример: <i>AI-боты для малого бизнеса</i>",
        parse_mode="HTML",
    )


@router.message(MoneyStates.waiting_market_input)
async def on_market_input(message: Message, state: FSMContext):
    await state.clear()
    topic = message.text.strip()
    await message.answer(f"📈 Анализирую рынок: {topic}...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.quick_market_scan(topic)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Анализ выше", reply_markup=back_to_money_kb())


@router.callback_query(F.data == "money_competitors")
async def cb_competitors_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(MoneyStates.waiting_competitors_input)
    await callback.message.answer(
        "🏢 Какую нишу проанализировать?\n\n"
        "Пример: <i>SaaS автоматизация бизнеса РФ</i>",
        parse_mode="HTML",
    )


@router.message(MoneyStates.waiting_competitors_input)
async def on_competitors_input(message: Message, state: FSMContext):
    await state.clear()
    niche = message.text.strip()
    await message.answer(f"🏢 Анализирую конкурентов: {niche}...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.analyze_competitors(niche)

    for part in _split(result):
        await message.answer(part)
    await message.answer("⬆️ Анализ выше", reply_markup=back_to_money_kb())


@router.callback_query(F.data == "money_sources")
async def cb_sources(callback: CallbackQuery):
    await callback.answer()
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    summary = await scanner.scan_sources_summary()
    await callback.message.answer(summary, parse_mode="HTML", reply_markup=back_to_money_kb())
