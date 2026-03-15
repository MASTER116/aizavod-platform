"""Команда /start и главное меню."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from telegram_bot.keyboards import main_menu_kb

router = Router()

WELCOME_TEXT = """🤖 **AIZAVOD — Командный центр**

**Фабрика контента:**
📊 Дашборд | 📋 Посты | 🎨 Создать | ⚙️ Настройки

**Поиск возможностей:**
/scan — гранты, хакатоны, конкурсы
/ideas — идеи для заработка
/sources — все источники

**Фриланс:**
/freelance — поиск заказов
/response описание — отклик на заказ
/kwork — описания услуг для Kwork
/services — наши услуги и цены

**Продажи:**
/estimate проект — оценка (сроки + цена)
/kp клиент | проект — коммерческое предложение
/segments — целевые сегменты
/coldmsg сегмент | канал — холодное письмо
/leads сегмент — где искать клиентов

**Аналитика:**
/market тема — анализ рынка
/competitors ниша — конкуренты
/proposal конкурс — заявка на конкурс"""


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="Markdown")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="Markdown")
    await callback.answer()
