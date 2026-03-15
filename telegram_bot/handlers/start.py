"""Главное меню AI Zavod и навигация по разделам."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from telegram_bot.keyboards import (
    main_menu_kb, money_menu_kb, sales_menu_kb,
    content_menu_kb, status_menu_kb, task_menu_kb,
)

router = Router()

WELCOME = """🏭 **AI ZAVOD — Командный центр**

Ты — идейный вдохновитель.
Я — генеральный директор (CEO-агент).

Выбери направление работы:"""

MONEY_TEXT = """💰 **Привлечь инвестиции**

Агенты для поиска денег:
• Сканер грантов и конкурсов
• Генератор идей заработка
• Анализ рынка и конкурентов
• Подготовка заявок"""

SALES_TEXT = """🛒 **Продажи и фриланс**

Агенты для продаж:
• Поиск заказов на фрилансе
• Генерация откликов и КП
• Оценка проектов
• Холодные продажи"""

CONTENT_TEXT = """📱 **Фабрика контента**

Instagram Factory:
• Генерация и публикация контента
• Управление автоматизацией
• Мониторинг расходов"""

TASK_TEXT = """🧠 **Задача / Запрос**

Ты ставишь задачу — я распределяю между директорами:
• 💰 Финансовый директор
• 🛒 Директор по продажам
• 📱 Директор по контенту
• 🔧 Технический директор

Могу ответить на любой стратегический вопрос."""

STATUS_TEXT = """📊 **Статус системы**

Мониторинг AI Zavod:
• Сервер и контейнеры
• База данных
• Состояние агентов"""


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(WELCOME, reply_markup=main_menu_kb(), parse_mode="Markdown")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(WELCOME, reply_markup=main_menu_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_money")
async def cb_money_menu(callback: CallbackQuery):
    await callback.message.edit_text(MONEY_TEXT, reply_markup=money_menu_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_sales")
async def cb_sales_menu(callback: CallbackQuery):
    await callback.message.edit_text(SALES_TEXT, reply_markup=sales_menu_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_content")
async def cb_content_menu(callback: CallbackQuery):
    await callback.message.edit_text(CONTENT_TEXT, reply_markup=content_menu_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_task")
async def cb_task_menu(callback: CallbackQuery):
    await callback.message.edit_text(TASK_TEXT, reply_markup=task_menu_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_status")
async def cb_status_menu(callback: CallbackQuery):
    await callback.message.edit_text(STATUS_TEXT, reply_markup=status_menu_kb(), parse_mode="Markdown")
    await callback.answer()
