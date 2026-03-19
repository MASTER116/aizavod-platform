"""Хендлеры раздела «Привлечь инвестиции» — полный цикл грантов.

Поток (кнопочный):
1. Сканировать → список грантов (кнопки)
2. Клик по гранту → авто глубокий анализ + авто генерация идей → список идей (кнопки)
3. Клик по идее → авто Excel-калькуляция → файл в чат
4. Документы на подачу / Сохранить идею
"""
from __future__ import annotations

import json
import logging
import os
import re

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telegram_bot.keyboards import (
    back_to_money_kb, money_menu_kb,
    scan_results_kb, ideas_list_kb, idea_selected_kb,
    saved_ideas_kb,
)

logger = logging.getLogger("aizavod.bot.opportunities")

router = Router()

MAX_TG_MSG = 4000


class MoneyStates(StatesGroup):
    waiting_proposal_input = State()
    waiting_market_input = State()
    waiting_competitors_input = State()
    waiting_grant_url = State()


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


async def _safe_send(message, text: str, limit: int = MAX_TG_MSG, **kwargs):
    """Отправляет текст, при ошибке парсинга — повторяет без parse_mode."""
    from aiogram.exceptions import TelegramBadRequest
    for part in _split(text, limit):
        try:
            await message.answer(part, **kwargs)
        except TelegramBadRequest:
            await message.answer(part, parse_mode=None)


def _parse_ideas(ideas_text: str) -> list[dict]:
    """Парсим текст идей в список словарей {title, text}."""
    ideas: list[dict] = []
    # Ищем паттерн: ## Идея N: Название или ## N. Название
    pattern = re.compile(r"##\s*(?:Идея\s*)?\[?\d+\]?[.:]\s*(.+)")
    blocks = pattern.split(ideas_text)

    if len(blocks) < 2:
        # Fallback: разделяем по ## или по номерам
        alt_pattern = re.compile(r"(?:^|\n)##\s+(.+)")
        parts = alt_pattern.split(ideas_text)
        if len(parts) >= 2:
            blocks = parts

    # blocks: [preamble, title1, body1, title2, body2, ...]
    for i in range(1, len(blocks) - 1, 2):
        title = blocks[i].strip().strip("*").strip()
        body = blocks[i + 1].strip() if i + 1 < len(blocks) else ""
        if title:
            ideas.append({"title": title, "text": body})

    return ideas


# ─── 1. Сканирование грантов (кнопки результатов) ────────────────────────

@router.callback_query(F.data == "money_scan")
async def cb_scan(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("🔍 Ищу...")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    results = await scanner.scan_web()

    if not results:
        await callback.message.answer("Ничего не найдено.", reply_markup=back_to_money_kb())
        return

    # Сохраняем результаты в FSM для дальнейшей работы
    # Фильтруем инструкции/гайды — оставляем только конкурсы
    _guide_keywords = [
        "как получить", "как спланировать", "как подать", "пошаговая инструкция",
        "топ-", "топ ", "лучших инструментов", "обзор грантов", "рейтинг",
        "calendar", "календарь грантовых",
    ]
    filtered = []
    for r in results:
        text_lower = f"{r.title} {r.description}".lower()
        if any(kw in text_lower for kw in _guide_keywords):
            continue
        filtered.append(r)

    scan_data = []
    num = 0
    lines = [f"Найдено: <b>{len(filtered)}</b>\n"]
    for r in filtered:
        num += 1
        rel = "🟢" if r.relevance_score > 0.6 else "🟡" if r.relevance_score > 0.3 else "⚪"
        desc = r.description or ""
        # Убираем бесполезные описания
        if not desc or len(desc) < 30 or "?" in desc[:50]:
            desc = ""
        line = f'{rel} <b>{num}. {r.title[:80]}</b>'
        if desc:
            line += f"\n   {desc[:120]}"
        line += f'\n   <a href="{r.url}">Ссылка</a>\n'
        lines.append(line)
        scan_data.append({
            "title": r.title,
            "url": r.url,
            "type": r.type,
            "description": r.description or "",
            "relevance": r.relevance_score,
        })

    await state.update_data(scan_results=scan_data)

    # Разбиваем текст на части по лимиту Telegram
    full_text = "\n".join(lines)
    for part in _split(full_text):
        try:
            await callback.message.answer(
                part, parse_mode="HTML", disable_web_page_preview=True,
            )
        except Exception:
            await callback.message.answer(part, parse_mode=None)

    await callback.message.answer(
        "Нажми на конкурс для глубокого анализа:",
        parse_mode="HTML",
        reply_markup=scan_results_kb(scan_data),
    )


# ─── 2. Клик по гранту → только анализ ────────────────────────────────

@router.callback_query(F.data.startswith("scan_grant_"))
async def cb_scan_grant_click(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    idx = int(callback.data.split("_")[-1])

    data = await state.get_data()
    scan_results = data.get("scan_results", [])

    if idx >= len(scan_results):
        await callback.message.answer("Результат не найден. Сканируй заново.",
                                       reply_markup=money_menu_kb())
        return

    grant = scan_results[idx]
    title = grant["title"]
    url = grant["url"]
    desc = grant.get("description", "")

    await state.update_data(grant_title=title, grant_url=url)

    await callback.message.answer(
        "🔬 Анализ..."
    )

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    analysis = await scanner.deep_analyze(title, url, desc)

    await state.update_data(grant_analysis=analysis)

    await _safe_send(callback.message, analysis)

    from telegram_bot.keyboards import grant_actions_kb
    await callback.message.answer(
        "Что дальше?",
        reply_markup=grant_actions_kb(),
    )


# ─── 2.0.1. Добавить ссылку для анализа ──────────────────────────────────

@router.callback_query(F.data == "grant_add_url")
async def cb_grant_add_url(callback: CallbackQuery, state: FSMContext):
    """Пользователь хочет дать свою ссылку для анализа конкурса."""
    await callback.answer()
    await state.set_state(MoneyStates.waiting_grant_url)
    await callback.message.answer(
        "🔗 Отправь ссылку на страницу конкурса (или несколько через пробел):"
    )


@router.message(MoneyStates.waiting_grant_url)
async def on_grant_url_input(message: Message, state: FSMContext):
    """Получили URL(ы) от пользователя — анализируем конкурс по ним."""
    data = await state.get_data()
    grant_title = data.get("grant_title", "")
    grant_url = data.get("grant_url", "")

    if not grant_title:
        await state.clear()
        await message.answer("Сначала выбери конкурс.", reply_markup=money_menu_kb())
        return

    # Извлекаем URL из текста
    urls = re.findall(r"https?://\S+", message.text or "")
    if not urls:
        await message.answer("Не нашёл ссылок. Отправь URL, начинающийся с http:// или https://")
        return

    await state.set_state(None)
    await message.answer("🔬 Анализ...")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    analysis = await scanner.deep_analyze(
        grant_title, grant_url, custom_urls=urls,
    )

    await state.update_data(grant_analysis=analysis)
    await _safe_send(message, analysis)

    from telegram_bot.keyboards import grant_actions_kb
    await message.answer("Что дальше?", reply_markup=grant_actions_kb())


# ─── 2.1. Генерация идей по кнопке ──────────────────────────────────────

@router.callback_query(F.data == "grant_ideas")
async def cb_grant_ideas(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    grant_title = data.get("grant_title", "")
    grant_analysis = data.get("grant_analysis", "")

    if not grant_title or not grant_analysis:
        await callback.message.answer(
            "Сначала выбери конкурс из списка.",
            reply_markup=money_menu_kb(),
        )
        return

    await callback.message.answer(
        "💡 Генерирую идеи..."
    )

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    ideas_text = await scanner.generate_ideas_for_grant(grant_title, grant_analysis)
    await state.update_data(grant_ideas_text=ideas_text)

    parsed = _parse_ideas(ideas_text)
    if not parsed:
        await _safe_send(callback.message, ideas_text)
        await callback.message.answer(
            "Не удалось разбить идеи на список. Текст выше.",
            reply_markup=back_to_money_kb(),
        )
        return

    await state.update_data(parsed_ideas=[
        {"title": idea["title"], "text": idea["text"]} for idea in parsed
    ])

    await _safe_send(callback.message, ideas_text)

    await callback.message.answer(
        "Выбери идею для Excel-калькуляции:",
        reply_markup=ideas_list_kb([{"title": p["title"]} for p in parsed]),
    )


# ─── 3. Клик по идее → авто Excel ────────────────────────────────────────

@router.callback_query(F.data.startswith("idea_"))
async def cb_idea_click(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    idx = int(callback.data.split("_")[-1])

    data = await state.get_data()
    parsed_ideas = data.get("parsed_ideas", [])
    grant_title = data.get("grant_title", "")

    if idx >= len(parsed_ideas):
        await callback.message.answer("Идея не найдена.", reply_markup=money_menu_kb())
        return

    idea = parsed_ideas[idx]
    idea_title = idea["title"]
    idea_text = idea["text"]

    await state.update_data(
        selected_idea_idx=idx,
        idea_title=idea_title,
        idea_text=idea_text,
    )

    await callback.message.answer(
        "📊 Генерирую смету...",
    )

    # Извлекаем сумму из текста идеи или анализа гранта
    grant_analysis = data.get("grant_analysis", "")
    amount_match = re.search(r"(\d[\d\s]*(?:000|млн|руб))", grant_analysis)
    grant_amount = amount_match.group(1) if amount_match else "3 000 000 руб"
    duration = "12 мес"

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    budget_json = await scanner.generate_budget_json(
        f"{idea_title} ({grant_title})", grant_amount, duration
    )

    await state.update_data(budget_json=budget_json)

    # Генерируем Excel
    from services.excel_generator import generate_budget_excel
    excel_path = generate_budget_excel(budget_json)

    if excel_path and os.path.exists(excel_path):
        doc = FSInputFile(excel_path)
        await callback.message.answer_document(doc, caption=f"📊 Смета: {idea_title[:60]}")
        await state.update_data(excel_path=excel_path)
    else:
        await callback.message.answer("Не удалось сгенерировать Excel. Попробуй ещё раз.")

    await callback.message.answer(
        "Что дальше?",
        reply_markup=idea_selected_kb(idx),
    )


# ─── 3.1. Назад к списку идей ────────────────────────────────────────────

@router.callback_query(F.data == "back_to_ideas")
async def cb_back_to_ideas(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    parsed_ideas = data.get("parsed_ideas", [])

    if not parsed_ideas:
        await callback.message.answer("Идеи не найдены. Сканируй заново.",
                                       reply_markup=money_menu_kb())
        return

    await callback.message.answer(
        "Выбери идею для Excel-калькуляции:",
        reply_markup=ideas_list_kb([{"title": p["title"]} for p in parsed_ideas]),
    )


# ─── 4. Ручной глубокий анализ (кнопка из меню) ──────────────────────────

@router.callback_query(F.data == "money_deep_analyze")
async def cb_deep_analyze_manual(callback: CallbackQuery, state: FSMContext):
    """Если нажали 'Глубокий анализ' из меню — предлагаем сначала сканировать."""
    await callback.answer()
    data = await state.get_data()
    scan_results = data.get("scan_results", [])

    if scan_results:
        await callback.message.answer(
            "Выбери конкурс из списка:",
            reply_markup=scan_results_kb(scan_results),
        )
    else:
        await callback.message.answer(
            "Сначала сканируй гранты — нажми '🔍 Сканировать гранты и конкурсы'",
            reply_markup=money_menu_kb(),
        )


# ─── 5. Генерация документов на подачу ───────────────────────────────────

@router.callback_query(F.data == "grant_docs")
async def cb_grant_docs(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    grant_title = data.get("grant_title", "")
    idea_title = data.get("idea_title", "")
    grant_ideas_text = data.get("grant_ideas_text", "")
    budget_json = data.get("budget_json", "")

    if not grant_title:
        await callback.message.answer(
            "Сначала выбери конкурс через сканирование.",
            reply_markup=money_menu_kb(),
        )
        return

    description = idea_title or grant_ideas_text[:1000]
    await callback.message.answer(
        "📄 Генерирую документы...",
    )

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    docs = await scanner.generate_submission_docs(
        idea_title or "Проект Zavod-ii",
        description,
        grant_title,
        budget_json,
    )

    # Генерируем PDF
    from services.pdf_generator import generate_submission_pdf
    pdf_title = f"Заявка: {idea_title or grant_title}"[:80]
    pdf_path = generate_submission_pdf(docs, title=pdf_title)

    if pdf_path and os.path.exists(pdf_path):
        pdf_doc = FSInputFile(pdf_path)
        await callback.message.answer_document(pdf_doc, caption=f"📄 {pdf_title[:60]}")
    else:
        # Fallback — текстом
        await _safe_send(callback.message, docs)

    await callback.message.answer(
        "Что дальше?",
        reply_markup=idea_selected_kb(data.get("selected_idea_idx", 0)),
    )


# ─── 6. Сохранить текущую идею ───────────────────────────────────────────

@router.callback_query(F.data == "grant_save_idea")
async def cb_save_idea(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    grant_title = data.get("grant_title", "")
    idea_title = data.get("idea_title", grant_title)
    idea_text = data.get("idea_text", "")
    budget_json = data.get("budget_json", "")
    grant_analysis = data.get("grant_analysis", "")

    if not idea_title and not grant_title:
        await callback.message.answer(
            "Нечего сохранять. Сначала выбери конкурс и идею.",
            reply_markup=money_menu_kb(),
        )
        return

    try:
        from backend.database import SessionLocal
        from backend.models import SavedIdea, GrantAnalysis, IdeaStatus

        db = SessionLocal()
        try:
            grant = None
            if grant_title:
                grant = GrantAnalysis(
                    title=grant_title,
                    source_url=data.get("grant_url", ""),
                    full_analysis=grant_analysis,
                )
                db.add(grant)
                db.flush()

            idea = SavedIdea(
                grant_id=grant.id if grant else None,
                title=idea_title,
                description=idea_text[:5000] if idea_text else "",
                budget_json=budget_json,
                status=IdeaStatus.SAVED,
                excel_path=data.get("excel_path", ""),
                created_by="telegram",
            )
            db.add(idea)
            db.commit()

            await callback.message.answer(
                f"💾 Сохранено: <b>{idea_title[:60]}</b>\n"
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


# ─── 6.1. Сохранить все идеи ─────────────────────────────────────────────

@router.callback_query(F.data == "grant_save_all")
async def cb_save_all_ideas(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    grant_title = data.get("grant_title", "")
    grant_analysis = data.get("grant_analysis", "")
    parsed_ideas = data.get("parsed_ideas", [])

    if not parsed_ideas:
        await callback.message.answer("Нет идей для сохранения.", reply_markup=money_menu_kb())
        return

    try:
        from backend.database import SessionLocal
        from backend.models import SavedIdea, GrantAnalysis, IdeaStatus

        db = SessionLocal()
        try:
            grant = None
            if grant_title:
                grant = GrantAnalysis(
                    title=grant_title,
                    source_url=data.get("grant_url", ""),
                    full_analysis=grant_analysis,
                )
                db.add(grant)
                db.flush()

            saved = 0
            for idea in parsed_ideas:
                obj = SavedIdea(
                    grant_id=grant.id if grant else None,
                    title=idea["title"],
                    description=idea["text"][:5000],
                    status=IdeaStatus.SAVED,
                    created_by="telegram",
                )
                db.add(obj)
                saved += 1

            db.commit()

            await callback.message.answer(
                f"💾 Сохранено <b>{saved}</b> идей для конкурса: <b>{grant_title[:60]}</b>",
                parse_mode="HTML",
                reply_markup=money_menu_kb(),
            )
        finally:
            db.close()
    except Exception as e:
        logger.error("Ошибка сохранения идей: %s", e)
        await callback.message.answer(f"Ошибка: {e}", reply_markup=money_menu_kb())


# ─── 7. Мои идеи (просмотр сохранённых) ─────────────────────────────────

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

            lines = [f"<b>Сохранённые идеи ({len(ideas)}):</b>\n"]
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
        await callback.message.answer(f"Ошибка: {e}", reply_markup=money_menu_kb())


# ─── Старые хендлеры (без изменений) ────────────────────────────────────

@router.callback_query(F.data == "money_ideas")
async def cb_ideas(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("💡 Генерирую идеи...")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    ideas = await scanner.generate_ideas()

    await _safe_send(callback.message, ideas)
    await callback.message.answer("Идеи выше", reply_markup=back_to_money_kb())


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

    await message.answer("📝 Готовлю заявку...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.generate_proposal(name, desc)

    await _safe_send(message, result)
    await message.answer("Заявка выше", reply_markup=back_to_money_kb())


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
    await message.answer("📈 Анализирую рынок...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.quick_market_scan(topic)

    await _safe_send(message, result)
    await message.answer("Анализ выше", reply_markup=back_to_money_kb())


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
    await message.answer("🏢 Анализирую конкурентов...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.analyze_competitors(niche)

    await _safe_send(message, result)
    await message.answer("Анализ выше", reply_markup=back_to_money_kb())


@router.callback_query(F.data == "money_sources")
async def cb_sources(callback: CallbackQuery):
    await callback.answer()
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    summary = await scanner.scan_sources_summary()
    await callback.message.answer(summary, parse_mode="HTML", reply_markup=back_to_money_kb())
