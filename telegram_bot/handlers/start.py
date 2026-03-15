"""Команда /start и главное меню."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from telegram_bot.keyboards import main_menu_kb

router = Router()

WELCOME_TEXT = """🤖 **AIZAVOD — Командный центр**

**Фабрика контента:**
📊 Дашборд — метрики и статистика
📋 Посты — предпросмотр постов
🎨 Создать — генерация нового контента
⚙️ Настройки — автоматизация

**Агенты заработка:**
/scan — поиск грантов, хакатонов, конкурсов
/ideas — генерация идей для заработка
/market тема — анализ рынка
/competitors ниша — анализ конкурентов
/proposal название — заявка на конкурс
/sources — все источники возможностей"""


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="Markdown")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="Markdown")
    await callback.answer()
