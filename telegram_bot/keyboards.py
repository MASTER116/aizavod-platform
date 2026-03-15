"""Inline-клавиатуры для Telegram-бота AI Zavod."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ─── Главное меню ────────────────────────────────────────────────────────


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Привлечь инвестиции", callback_data="menu_money")],
        [InlineKeyboardButton(text="🛒 Продажи и фриланс", callback_data="menu_sales")],
        [InlineKeyboardButton(text="📱 Фабрика контента", callback_data="menu_content")],
        [InlineKeyboardButton(text="🧠 Задача / Запрос", callback_data="menu_task")],
        [InlineKeyboardButton(text="📊 Статус системы", callback_data="menu_status")],
    ])


# ─── Привлечь инвестиции ─────────────────────────────────────────────────


def money_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Сканировать гранты и конкурсы", callback_data="money_scan")],
        [InlineKeyboardButton(text="💡 Идеи для заработка", callback_data="money_ideas")],
        [InlineKeyboardButton(text="📝 Заявка на конкурс", callback_data="money_proposal")],
        [InlineKeyboardButton(text="📈 Анализ рынка", callback_data="money_market")],
        [InlineKeyboardButton(text="🏢 Анализ конкурентов", callback_data="money_competitors")],
        [InlineKeyboardButton(text="📋 Источники возможностей", callback_data="money_sources")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


# ─── Продажи и фриланс ──────────────────────────────────────────────────


def sales_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Найти заказы на фрилансе", callback_data="sales_freelance")],
        [InlineKeyboardButton(text="✍️ Отклик на заказ", callback_data="sales_response")],
        [InlineKeyboardButton(text="🏷 Описания для Kwork", callback_data="sales_kwork")],
        [InlineKeyboardButton(text="💵 Оценить проект", callback_data="sales_estimate")],
        [InlineKeyboardButton(text="📄 Коммерческое предложение", callback_data="sales_kp")],
        [InlineKeyboardButton(text="🎯 Целевые сегменты", callback_data="sales_segments")],
        [InlineKeyboardButton(text="📨 Холодное письмо", callback_data="sales_coldmsg")],
        [InlineKeyboardButton(text="📍 Где искать клиентов", callback_data="sales_leads")],
        [InlineKeyboardButton(text="📦 Наши услуги", callback_data="sales_services")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


# ─── Фабрика контента ───────────────────────────────────────────────────


def content_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Дашборд", callback_data="dashboard")],
        [InlineKeyboardButton(text="📋 Посты на проверку", callback_data="next_posts")],
        [InlineKeyboardButton(text="🎨 Создать пост", callback_data="generate")],
        [InlineKeyboardButton(text="⚙️ Настройки автоматизации", callback_data="settings")],
        [InlineKeyboardButton(text="💰 Расходы API", callback_data="costs")],
        [InlineKeyboardButton(text="🤖 Статус агента", callback_data="content_agent")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


# ─── Статус системы ─────────────────────────────────────────────────────


def status_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖥 Сервер", callback_data="status_server")],
        [InlineKeyboardButton(text="🐳 Docker контейнеры", callback_data="status_docker")],
        [InlineKeyboardButton(text="🗄 База данных", callback_data="status_db")],
        [InlineKeyboardButton(text="🤖 Агенты", callback_data="status_agents")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


# ─── Задача / Запрос ────────────────────────────────────────────────────


def task_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Задать вопрос CEO", callback_data="task_ask")],
        [InlineKeyboardButton(text="📋 Поставить задачу", callback_data="task_assign")],
        [InlineKeyboardButton(text="🔄 Стратегический план", callback_data="task_strategy")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


# ─── Общие ───────────────────────────────────────────────────────────────


def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


def back_to_money_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Инвестиции", callback_data="menu_money")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def back_to_sales_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Продажи", callback_data="menu_sales")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def back_to_content_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Контент", callback_data="menu_content")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


# Legacy — для обратной совместимости
def back_kb() -> InlineKeyboardMarkup:
    return back_to_main_kb()


def post_review_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{post_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{post_id}"),
        ],
        [
            InlineKeyboardButton(text="🔄 Переделать", callback_data=f"regen_{post_id}"),
            InlineKeyboardButton(text="📅 Запланировать", callback_data=f"schedule_{post_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Контент", callback_data="menu_content")],
    ])


def category_kb() -> InlineKeyboardMarkup:
    categories = [
        ("🏋️ Тренировка", "cat_workout"),
        ("🌿 Образ жизни", "cat_lifestyle"),
        ("💪 Мотивация", "cat_motivation"),
        ("👗 Наряды", "cat_outfit"),
        ("🥗 Питание", "cat_nutrition"),
        ("📹 За кулисами", "cat_behind_scenes"),
        ("🔄 Трансформация", "cat_transformation"),
        ("📚 Урок", "cat_tutorial"),
    ]
    rows = [[InlineKeyboardButton(text=t, callback_data=d)] for t, d in categories]
    rows.append([InlineKeyboardButton(text="◀️ Контент", callback_data="menu_content")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_kb(auto_gen: bool, auto_approve: bool, auto_publish: bool, auto_reply: bool) -> InlineKeyboardMarkup:
    def icon(val: bool) -> str:
        return "✅" if val else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{icon(auto_gen)} Авто-генерация", callback_data="toggle_auto_generate")],
        [InlineKeyboardButton(text=f"{icon(auto_approve)} Авто-одобрение", callback_data="toggle_auto_approve")],
        [InlineKeyboardButton(text=f"{icon(auto_publish)} Авто-публикация", callback_data="toggle_auto_publish")],
        [InlineKeyboardButton(text=f"{icon(auto_reply)} Авто-ответ на комментарии", callback_data="toggle_auto_reply")],
        [InlineKeyboardButton(text="◀️ Контент", callback_data="menu_content")],
    ])


def confirm_kb(action: str, entity_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{entity_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="main_menu"),
        ],
    ])
