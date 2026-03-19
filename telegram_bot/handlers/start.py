"""Главное меню Zavod-ii и навигация по разделам."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from telegram_bot.keyboards import (
    main_menu_kb, money_menu_kb, sales_menu_kb,
    content_menu_kb, status_menu_kb, task_menu_kb, legal_menu_kb,
)

router = Router()

WELCOME = """Zavod-ii — AI-команда для вашего бизнеса

21+ специализированных агентов: юрист, бухгалтер, маркетолог, аналитик, HR и другие.

Просто напишите вопрос — система направит к нужному специалисту. Или выберите раздел:"""

MONEY_TEXT = """Привлечь инвестиции

Агенты для поиска финансирования:
- Сканер грантов и конкурсов (РНФ, ФСИ)
- Генератор идей заработка
- Анализ рынка и конкурентов
- Подготовка заявок и КП"""

SALES_TEXT = """Продажи и фриланс

Агенты для продаж:
- Поиск заказов (Kwork, Upwork)
- Генерация откликов и КП
- Оценка стоимости проектов
- Холодные продажи и лид-генерация"""

CONTENT_TEXT = """Фабрика контента

Генерация контента для бизнеса:
- Посты для VK, Telegram, Instagram
- Email-рассылки
- Презентации и документы"""

TASK_TEXT = """Задача / Запрос

Опишите задачу — система разобьёт её на подзадачи и распределит между агентами:

- Финансовый директор
- Директор по продажам
- Директор по контенту
- Технический директор
- Юридический директор
- HR-директор

Или задайте любой вопрос — получите ответ от нужного специалиста."""

LEGAL_TEXT = """Юрист / Бухгалтер

Юридический отдел:
- Консультации по праву РФ
- Анализ и генерация договоров
- Регистрация ИП/ООО (сравнение вариантов 2026)
- Трудовое право, досудебные претензии

Бухгалтерия:
- Налоги: УСН / ОСНО / Патент / АУСН
- НДС 22% (2026) — оптимизация
- Календарь отчётности и сроки
- Расчёт зарплаты и взносов"""

STATUS_TEXT = """Статус системы

Мониторинг Zavod-ii:
- Здоровье агентов
- Расходы и токены
- Metering (лимиты)
- Compliance аудит"""


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(WELCOME, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_money")
async def cb_money_menu(callback: CallbackQuery):
    await callback.message.edit_text(MONEY_TEXT, reply_markup=money_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_sales")
async def cb_sales_menu(callback: CallbackQuery):
    await callback.message.edit_text(SALES_TEXT, reply_markup=sales_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_legal")
async def cb_legal_menu(callback: CallbackQuery):
    await callback.message.edit_text(LEGAL_TEXT, reply_markup=legal_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_content")
async def cb_content_menu(callback: CallbackQuery):
    await callback.message.edit_text(CONTENT_TEXT, reply_markup=content_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_task")
async def cb_task_menu(callback: CallbackQuery):
    await callback.message.edit_text(TASK_TEXT, reply_markup=task_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_status")
async def cb_status_menu(callback: CallbackQuery):
    await callback.message.edit_text(STATUS_TEXT, reply_markup=status_menu_kb())
    await callback.answer()
