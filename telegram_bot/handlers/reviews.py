"""Telegram handlers — AI-менеджер отзывов."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.review_manager_agent import (
    get_review_manager_agent,
    Review,
)

logger = logging.getLogger("aizavod.bot.reviews")
router = Router()


class ReviewStates(StatesGroup):
    waiting_reviews_text = State()
    waiting_approval = State()


# ─── Клавиатуры ─────────────────────────────────────────────────────

def reviews_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Ответить на отзывы", callback_data="rev_respond")],
        [InlineKeyboardButton(text="📊 Анализ тональности", callback_data="rev_analyze")],
        [InlineKeyboardButton(text="💡 Как работать с отзывами", callback_data="rev_help")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


def approval_kb(review_idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data=f"rev_approve_{review_idx}"),
            InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"rev_regen_{review_idx}"),
        ],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"rev_skip_{review_idx}")],
    ])


# ─── Вход в меню отзывов ────────────────────────────────────────────

@router.callback_query(F.data == "menu_reviews")
async def show_reviews_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "⭐ <b>AI-менеджер отзывов</b>\n\n"
        "Генерирую профессиональные ответы на отзывы "
        "Яндекс Карт и 2ГИС.\n\n"
        "Выберите действие:",
        reply_markup=reviews_menu_kb(),
        parse_mode="HTML",
    )


# ─── Ответы на отзывы ──────────────────────────────────────────────

@router.callback_query(F.data == "rev_respond")
async def ask_for_reviews(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 <b>Отправьте отзывы</b>\n\n"
        "Скопируйте отзывы и вставьте сюда. Формат:\n\n"
        "<i>⭐⭐⭐⭐⭐ Иван\n"
        "Отличный сервис, быстро сделали\n\n"
        "⭐⭐ Мария\n"
        "Долго ждали, качество среднее</i>\n\n"
        "Или просто вставьте текст — я разберусь.",
        parse_mode="HTML",
    )
    await state.set_state(ReviewStates.waiting_reviews_text)


@router.message(ReviewStates.waiting_reviews_text)
async def process_reviews_input(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Отправьте текст отзывов.")
        return

    await message.answer("🔍 Анализирую отзывы и генерирую ответы...")

    # Парсим отзывы из текста
    reviews = _parse_reviews_from_text(text)

    if not reviews:
        # Если не удалось распарсить — отправляем как есть в агент
        agent = get_review_manager_agent()
        result = await agent.process_query(
            f"Пользователь отправил отзывы, сгенерируй ответы:\n\n{text}"
        )
        await _safe_send(message, result)
        await state.clear()
        return

    # Генерируем ответы
    agent = get_review_manager_agent()
    reviews_with_responses = await agent.generate_batch_responses(reviews)

    # Сохраняем в state для одобрения
    await state.update_data(reviews=[
        {
            "author": r.author,
            "rating": r.rating,
            "text": r.text,
            "ai_response": r.ai_response,
        }
        for r in reviews_with_responses
    ])

    # Отправляем результаты
    for i, r in enumerate(reviews_with_responses):
        stars = "⭐" * r.rating + "☆" * (5 - r.rating)
        text_block = (
            f"<b>{stars} {r.author}</b>\n"
            f"<i>{r.text[:300]}</i>\n\n"
            f"💬 <b>AI-ответ:</b>\n{r.ai_response}"
        )
        await _safe_send(message, text_block, reply_markup=approval_kb(i))

    await state.clear()


# ─── Анализ тональности ─────────────────────────────────────────────

@router.callback_query(F.data == "rev_analyze")
async def ask_for_analysis(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📊 <b>Анализ тональности</b>\n\n"
        "Отправьте отзывы для анализа — я определю:\n"
        "• Средний рейтинг\n"
        "• Положительные и отрицательные темы\n"
        "• Срочные отзывы без ответа\n"
        "• Рекомендации",
        parse_mode="HTML",
    )
    await state.set_state(ReviewStates.waiting_reviews_text)


# ─── Справка ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "rev_help")
async def show_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "💡 <b>Как работать с отзывами</b>\n\n"
        "1. Скопируйте отзывы с Яндекс Карт / 2ГИС\n"
        "2. Отправьте мне — я сгенерирую ответы\n"
        "3. Одобрите или перегенерируйте\n"
        "4. Скопируйте ответ и вставьте на площадку\n\n"
        "📌 <b>Тарифы:</b>\n"
        "• 1 точка — 990 ₽/мес\n"
        "• До 10 точек — 2 990 ₽/мес\n"
        "• Безлимит — 4 990 ₽/мес\n\n"
        "🔜 Скоро: автопарсинг отзывов по ссылке",
        reply_markup=reviews_menu_kb(),
        parse_mode="HTML",
    )


# ─── Одобрение ответов ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("rev_approve_"))
async def approve_response(callback: CallbackQuery):
    await callback.answer("✅ Ответ одобрен! Скопируйте и вставьте на площадку.")


@router.callback_query(F.data.startswith("rev_regen_"))
async def regen_response(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    data = await state.get_data()
    reviews = data.get("reviews", [])
    if idx < len(reviews):
        r = reviews[idx]
        agent = get_review_manager_agent()
        review = Review(
            source="manual",
            author=r["author"],
            rating=r["rating"],
            text=r["text"],
            date="",
        )
        new_response = await agent.generate_response(review)
        stars = "⭐" * r["rating"] + "☆" * (5 - r["rating"])
        await callback.message.edit_text(
            f"<b>{stars} {r['author']}</b>\n"
            f"<i>{r['text'][:300]}</i>\n\n"
            f"💬 <b>AI-ответ (v2):</b>\n{new_response}",
            reply_markup=approval_kb(idx),
            parse_mode="HTML",
        )
    else:
        await callback.answer("Отзыв не найден")


@router.callback_query(F.data.startswith("rev_skip_"))
async def skip_response(callback: CallbackQuery):
    await callback.answer("⏭ Пропущено")
    await callback.message.delete()


# ─── Утилиты ─────────────────────────────────────────────────────────

def _parse_reviews_from_text(text: str) -> list[Review]:
    """Простой парсер отзывов из текста."""
    reviews = []
    # Разбиваем по двойным переводам строк
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue

        # Пытаемся найти рейтинг в первой строке
        first_line = lines[0]
        star_count = first_line.count("⭐")
        if star_count == 0:
            # Пытаемся найти цифру рейтинга
            import re
            m = re.search(r'(\d)\s*/?\s*5', first_line)
            if m:
                star_count = int(m.group(1))
            else:
                star_count = 3  # По умолчанию

        # Имя автора — убираем звёзды
        author = first_line.replace("⭐", "").replace("☆", "").strip()
        author = author.strip("- :")
        if not author:
            author = "Аноним"

        # Текст отзыва — остальные строки
        review_text = "\n".join(lines[1:]).strip()
        if not review_text and len(lines) == 1:
            # Весь блок — это текст
            review_text = first_line
            author = "Аноним"

        if review_text:
            reviews.append(Review(
                source="manual",
                author=author[:50],
                rating=max(1, min(5, star_count)),
                text=review_text[:1000],
                date="",
            ))

    return reviews


async def _safe_send(message: Message, text: str, limit: int = 4000, **kwargs):
    """Отправка с fallback на parse_mode=None."""
    from aiogram.exceptions import TelegramBadRequest

    for i in range(0, len(text), limit):
        part = text[i:i + limit]
        try:
            await message.answer(part, parse_mode="HTML", **kwargs)
        except TelegramBadRequest:
            await message.answer(part, parse_mode=None, **kwargs)
