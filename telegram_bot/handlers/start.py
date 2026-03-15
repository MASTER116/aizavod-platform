"""Start command and main menu handler."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from telegram_bot.keyboards import main_menu_kb

router = Router()

WELCOME_TEXT = """🤖 **AIZAVOD — AI Instagram Factory**

Управление AI-фитнес аккаунтом в Instagram.

📊 Dashboard — метрики и статистика
📋 Next Posts — предпросмотр постов
🎨 Generate — генерация нового контента
📸 Stories — управление Stories
⚙️ Settings — настройки автономности
💰 Costs — отчет по расходам API
🔔 Alerts — уведомления"""


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="Markdown")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="Markdown")
    await callback.answer()
