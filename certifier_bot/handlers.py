"""CERTIFIER bot handlers — /start, text questions, /help."""
from __future__ import annotations

import logging
import os

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from .rate_limiter import check_limit, FREE_DAILY_LIMIT

logger = logging.getLogger("aizavod.certifier_bot")

router = Router()

WELCOME = (
    "<b>CERTIFIER — AI-консультант по сертификации ТС</b>\n\n"
    "Я помогу разобраться в сертификации транспортных средств "
    "по техническим регламентам Таможенного союза (ЕАЭС).\n\n"
    "Просто напишите ваш вопрос, например:\n"
    "• <i>Какой сертификат нужен для импорта авто?</i>\n"
    "• <i>Сколько стоит СБКТС?</i>\n"
    "• <i>Как установить ГБО по закону?</i>\n"
    "• <i>Что такое ЭРА-ГЛОНАСС?</i>\n\n"
    f"Бесплатно: <b>{FREE_DAILY_LIMIT} вопроса в день</b>.\n"
    "Для безлимита — тариф STARTER."
)

HELP = (
    "<b>Что я умею:</b>\n\n"
    "• Консультирую по ТР ТС 018/2011 (безопасность ТС)\n"
    "• Объясняю разницу ОТТС / СБКТС\n"
    "• Рассказываю про параллельный импорт\n"
    "• Помогаю с ЭРА-ГЛОНАСС, переоборудованием, ГБО\n"
    "• Даю оценку стоимости и сроков\n\n"
    "<b>Команды:</b>\n"
    "/start — начало\n"
    "/help — эта справка\n\n"
    "Разработано: Zavod-ii (aizavod.ru)"
)

LIMIT_REACHED = (
    "Вы использовали все <b>{limit} бесплатных вопроса</b> на сегодня.\n\n"
    "Завтра лимит обновится, или переходите на тариф "
    "<b>STARTER</b> для безлимитных консультаций."
)


def _starter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Тариф STARTER (скоро)", callback_data="starter_info")],
    ])


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP)


@router.callback_query(F.data == "starter_info")
async def cb_starter(callback: CallbackQuery):
    await callback.answer(
        "Тариф STARTER с безлимитными вопросами скоро будет доступен!",
        show_alert=True,
    )


@router.message(F.text)
async def handle_question(message: Message):
    """Handle free-text questions."""
    user_id = message.from_user.id
    question = message.text.strip()

    if len(question) < 3:
        await message.answer("Задайте вопрос подробнее (минимум 3 символа).")
        return

    # Rate limit
    allowed, remaining = check_limit(user_id)
    if not allowed:
        await message.answer(
            LIMIT_REACHED.format(limit=FREE_DAILY_LIMIT),
            reply_markup=_starter_kb(),
        )
        return

    # Show typing
    await message.bot.send_chat_action(message.chat.id, "typing")

    # Call certifier service
    try:
        from services.certifier_service import get_certifier_service

        service = get_certifier_service()
        result = await service.query(question)

        answer = result["answer"]
        model = result["model"]
        confidence = result["confidence"]

        footer = f"\n\n<i>Осталось вопросов: {remaining}/{FREE_DAILY_LIMIT}</i>"
        if confidence == "low":
            footer += "\n<i>⚠ Ответ может быть неточным — рекомендуем проверить в первоисточнике.</i>"

        await message.answer(answer + footer)

        logger.info(
            "user=%s q=%r model=%s confidence=%s remaining=%d",
            user_id, question[:50], model, confidence, remaining,
        )

    except Exception as exc:
        logger.error("Certifier query failed: %s", exc, exc_info=True)
        await message.answer(
            "Произошла ошибка при обработке вопроса. Попробуйте позже.\n"
            f"<i>Осталось вопросов: {remaining}/{FREE_DAILY_LIMIT}</i>"
        )
