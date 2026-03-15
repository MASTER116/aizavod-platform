"""Хендлеры раздела «Привлечь инвестиции» — полный цикл грантов.

Поток: сканирование → выбор конкурса → глубокий анализ → генерация идей →
Excel-калькуляция → документы на подачу → сохранение идей.
"""
from __future__ import annotations

import json
import logging
import os

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.keyboards import (
    back_to_money_kb, money_menu_kb, grant_actions_kb,
    idea_actions_kb, saved_ideas_kb,
)

logger = logging.getLogger("aizavod.bot.opportunities")

router = Router()

MAX_TG_MSG = 4000


class MoneyStates(StatesGroup):
    waiting_proposal_input = State()
    waiting_market_input = State()
    waiting_competitors_input = State()
    waiting_grant_url = State()
    waiting_grant_choice = State()
    waiting_idea_choice = State()
    waiting_budget_params = State()


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


# ─── 1. Сканирование грантов ────────────────────────────────────────────

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

    lines.append("\nВыбери номер конкурса для глубокого анализа (отправь цифру)")
    lines.append("Или нажми кнопку ниже")

    text = "\n".join(lines)[:MAX_TG_MSG]
    await callback.message.answer(
        text, parse_mode="HTML", disable_web_page_preview=True,
        reply_markup=back_to_money_kb(),
    )


# ─── 2. Глубокий анализ конкурса ────────────────────────────────────────

@router.callback_query(F.data == "money_deep_analyze")
async def cb_deep_analyze_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(MoneyStates.waiting_grant_url)
    await callback.message.answer(
        "🔍 Введи название конкурса и ссылку:\n\n"
        "Формат: <b>Название | Ссылка</b>\n"
        "Пример: <i>Старт-ИИ | https://fasie.ru/programs/start-ai/</i>\n\n"
        "Или просто название — проанализирую на основе знаний.",
        parse_mode="HTML",
    )


@router.message(MoneyStates.waiting_grant_url)
async def on_grant_url(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split("|", 1)
    title = parts[0].strip()
    url = parts[1].strip() if len(parts) > 1 else ""

    await state.update_data(grant_title=title, grant_url=url)
    await state.clear()

    await message.answer(f"🔍 Анализирую конкурс: <b>{title}</b>...", parse_mode="HTML")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    analysis = await scanner.deep_analyze(title, url)

    # Сохраняем анализ в state для следующих шагов
    await state.update_data(
        grant_title=title,
        grant_url=url,
        grant_analysis=analysis,
    )

    for part in _split(analysis):
        await message.answer(part)

    await message.answer(
        "⬆️ Анализ конкурса выше. Что дальше?",
        reply_markup=grant_actions_kb(),
    )


# ─── 3. Генерация идей ПОД КОНКУРС ─────────────────────────────────────

@router.callback_query(F.data == "grant_ideas")
async def cb_grant_ideas(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    grant_title = data.get("grant_title", "")
    grant_analysis = data.get("grant_analysis", "")

    if not grant_title:
        await callback.message.answer(
            "Сначала выбери конкурс через '🔍 Глубокий анализ'",
            reply_markup=money_menu_kb(),
        )
        return

    await callback.message.answer(
        f"💡 Генерирую идеи для: <b>{grant_title}</b>...",
        parse_mode="HTML",
    )

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    ideas = await scanner.generate_ideas_for_grant(grant_title, grant_analysis)

    await state.update_data(grant_ideas=ideas)

    for part in _split(ideas):
        await callback.message.answer(part)

    await callback.message.answer(
        "⬆️ Идеи выше. Что дальше?",
        reply_markup=idea_actions_kb(),
    )


# ─── 4. Excel-калькуляция ───────────────────────────────────────────────

@router.callback_query(F.data == "grant_excel")
async def cb_grant_excel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    grant_title = data.get("grant_title", "")

    if not grant_title:
        await callback.message.answer(
            "Сначала выбери конкурс и сгенерируй идеи",
            reply_markup=money_menu_kb(),
        )
        return

    await state.set_state(MoneyStates.waiting_budget_params)
    await callback.message.answer(
        "📊 Укажи параметры для калькуляции:\n\n"
        "Формат: <b>Название идеи | Сумма гранта | Срок (мес)</b>\n"
        "Пример: <i>AI-ассистент для МСП | 3 000 000 руб | 12 мес</i>",
        parse_mode="HTML",
    )


@router.message(MoneyStates.waiting_budget_params)
async def on_budget_params(message: Message, state: FSMContext):
    await state.clear()
    text = message.text.strip()
    parts = text.split("|")
    idea_title = parts[0].strip() if parts else text
    grant_amount = parts[1].strip() if len(parts) > 1 else "3 000 000 руб"
    duration = parts[2].strip() if len(parts) > 2 else "12 мес"

    data = await state.get_data()
    grant_title = data.get("grant_title", idea_title)

    await message.answer("📊 Генерирую смету и Excel-файл...")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    budget_json = await scanner.generate_budget_json(idea_title, grant_amount, duration)

    # Сохраняем JSON
    await state.update_data(
        idea_title=idea_title,
        budget_json=budget_json,
        grant_amount=grant_amount,
        duration=duration,
    )

    # Генерируем Excel
    from services.excel_generator import generate_budget_excel
    excel_path = generate_budget_excel(budget_json)

    if excel_path and os.path.exists(excel_path):
        doc = FSInputFile(excel_path)
        await message.answer_document(
            doc,
            caption=f"📊 Смета: {idea_title}\nСумма: {grant_amount}\nСрок: {duration}",
        )
        await state.update_data(excel_path=excel_path)
    else:
        # Отправляем текстом если Excel не удалось создать
        for part in _split(budget_json):
            await message.answer(f"<pre>{part[:4000]}</pre>", parse_mode="HTML")

    await message.answer(
        "⬆️ Калькуляция выше. Файл можно открыть в Excel и редактировать.",
        reply_markup=idea_actions_kb(),
    )


# ─── 5. Генерация документов на подачу ──────────────────────────────────

@router.callback_query(F.data == "grant_docs")
async def cb_grant_docs(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    grant_title = data.get("grant_title", "")
    idea_title = data.get("idea_title", "")
    grant_ideas = data.get("grant_ideas", "")
    budget_json = data.get("budget_json", "")

    if not grant_title:
        await callback.message.answer(
            "Сначала выбери конкурс и сгенерируй идеи",
            reply_markup=money_menu_kb(),
        )
        return

    description = idea_title or grant_ideas[:1000]
    await callback.message.answer(
        f"📄 Генерирую документы для подачи на: <b>{grant_title}</b>...",
        parse_mode="HTML",
    )

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    docs = await scanner.generate_submission_docs(
        idea_title or "Проект AI Zavod",
        description,
        grant_title,
        budget_json,
    )

    for part in _split(docs):
        await callback.message.answer(part)

    await callback.message.answer(
        "⬆️ Пакет документов выше",
        reply_markup=idea_actions_kb(),
    )


# ─── 6. Сохранить идею ─────────────────────────────────────────────────

@router.callback_query(F.data == "grant_save_idea")
async def cb_save_idea(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    grant_title = data.get("grant_title", "")
    idea_title = data.get("idea_title", grant_title)
    grant_ideas = data.get("grant_ideas", "")
    budget_json = data.get("budget_json", "")
    grant_analysis = data.get("grant_analysis", "")

    if not idea_title and not grant_title:
        await callback.message.answer(
            "Нечего сохранять. Сначала выбери конкурс и сгенерируй идеи.",
            reply_markup=money_menu_kb(),
        )
        return

    try:
        from backend.database import SessionLocal
        from backend.models import SavedIdea, GrantAnalysis, IdeaStatus

        db = SessionLocal()
        try:
            # Сохраняем анализ гранта
            grant = None
            if grant_title:
                grant = GrantAnalysis(
                    title=grant_title,
                    source_url=data.get("grant_url", ""),
                    full_analysis=grant_analysis,
                )
                db.add(grant)
                db.flush()

            # Сохраняем идею
            idea = SavedIdea(
                grant_id=grant.id if grant else None,
                title=idea_title,
                description=grant_ideas[:5000] if grant_ideas else "",
                budget_json=budget_json,
                status=IdeaStatus.SAVED,
                excel_path=data.get("excel_path", ""),
                created_by="telegram",
            )
            db.add(idea)
            db.commit()

            await callback.message.answer(
                f"✅ Идея сохранена: <b>{idea_title}</b>\n"
                f"ID: {idea.id}\n"
                f"Конкурс: {grant_title or 'не указан'}",
                parse_mode="HTML",
                reply_markup=money_menu_kb(),
            )
        finally:
            db.close()
    except Exception as e:
        logger.error("Ошибка сохранения идеи: %s", e)
        await callback.message.answer(
            f"Ошибка сохранения: {e}\n\nИдея не потеряна — она выше в чате.",
            reply_markup=money_menu_kb(),
        )


# ─── 7. Мои идеи (просмотр сохранённых) ────────────────────────────────

@router.callback_query(F.data == "money_my_ideas")
async def cb_my_ideas(callback: CallbackQuery):
    await callback.answer()

    try:
        from backend.database import SessionLocal
        from backend.models import SavedIdea

        db = SessionLocal()
        try:
            ideas = (
                db.query(SavedIdea)
                .order_by(SavedIdea.created_at.desc())
                .limit(20)
                .all()
            )

            if not ideas:
                await callback.message.answer(
                    "Нет сохранённых идей. Сканируй конкурсы и сохраняй!",
                    reply_markup=money_menu_kb(),
                )
                return

            lines = [f"📋 <b>Сохранённые идеи ({len(ideas)}):</b>\n"]
            for idea in ideas:
                status_val = idea.status.value if hasattr(idea.status, 'value') else str(idea.status)
                status_emoji = {
                    "draft": "📝", "saved": "💾", "in_progress": "🔄",
                    "submitted": "📨", "won": "🏆", "rejected": "❌",
                }.get(status_val, "📝")
                lines.append(
                    f"{status_emoji} <b>{idea.id}. {idea.title[:60]}</b>\n"
                    f"   Статус: {status_val} | "
                    f"{idea.created_at.strftime('%d.%m.%Y')}\n"
                )

            text = "\n".join(lines)[:MAX_TG_MSG]
            await callback.message.answer(
                text, parse_mode="HTML",
                reply_markup=saved_ideas_kb(),
            )
        finally:
            db.close()
    except Exception as e:
        logger.error("Ошибка загрузки идей: %s", e)
        await callback.message.answer(
            f"Ошибка загрузки: {e}",
            reply_markup=money_menu_kb(),
        )


# ─── Старые хендлеры (без изменений) ────────────────────────────────────

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
