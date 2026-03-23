"""Inline-клавиатуры для Telegram-бота Zavod-ii."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ─── Главное меню ────────────────────────────────────────────────────────


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Менеджер отзывов", callback_data="menu_reviews")],
        [InlineKeyboardButton(text="🛒 Продажи и фриланс", callback_data="menu_sales")],
        [InlineKeyboardButton(text="📱 Фабрика контента", callback_data="menu_content")],
        [InlineKeyboardButton(text="🧠 Задача / Запрос", callback_data="menu_task")],
        [InlineKeyboardButton(text="📊 Статус системы", callback_data="menu_status")],
        [InlineKeyboardButton(text="🔧 Админ-панель", callback_data="menu_admin")],
    ])


# ─── Админ-панель ──────────────────────────────────────────────────────

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💚 Здоровье агентов", callback_data="admin_health")],
        [InlineKeyboardButton(text="💵 Расходы и токены", callback_data="admin_costs")],
        [InlineKeyboardButton(text="🧪 A/B эксперименты", callback_data="admin_ab")],
        [InlineKeyboardButton(text="📊 Metering (лимиты)", callback_data="admin_metering")],
        [InlineKeyboardButton(text="🛡 Compliance аудит", callback_data="admin_compliance")],
        [InlineKeyboardButton(text="☠️ Kill-Switch", callback_data="admin_killswitch")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


def killswitch_kb(agents: list[str]) -> InlineKeyboardMarkup:
    buttons = []
    for agent in agents[:10]:
        buttons.append([InlineKeyboardButton(text=f"☠️ Kill {agent}", callback_data=f"kill_{agent}")])
    buttons.append([InlineKeyboardButton(text="◀️ Админ-панель", callback_data="menu_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Привлечь инвестиции ─────────────────────────────────────────────────


def money_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Сканировать гранты и конкурсы", callback_data="money_scan")],
        [InlineKeyboardButton(text="🔬 Глубокий анализ конкурса", callback_data="money_deep_analyze")],
        [InlineKeyboardButton(text="💡 Идеи для заработка", callback_data="money_ideas")],
        [InlineKeyboardButton(text="📝 Заявка на конкурс", callback_data="money_proposal")],
        [InlineKeyboardButton(text="📈 Анализ рынка", callback_data="money_market")],
        [InlineKeyboardButton(text="🏢 Анализ конкурентов", callback_data="money_competitors")],
        [InlineKeyboardButton(text="📋 Источники возможностей", callback_data="money_sources")],
        [InlineKeyboardButton(text="💾 Мои идеи", callback_data="money_my_ideas")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


def grant_actions_kb() -> InlineKeyboardMarkup:
    """Действия после анализа конкурса."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Добавить ссылку для анализа", callback_data="grant_add_url")],
        [InlineKeyboardButton(text="💡 Идеи под этот конкурс", callback_data="grant_ideas")],
        [InlineKeyboardButton(text="📊 Excel-калькуляция", callback_data="grant_excel")],
        [InlineKeyboardButton(text="📄 Документы на подачу", callback_data="grant_docs")],
        [InlineKeyboardButton(text="💾 Сохранить идею", callback_data="grant_save_idea")],
        [InlineKeyboardButton(text="◀️ Инвестиции", callback_data="menu_money")],
    ])


def idea_actions_kb() -> InlineKeyboardMarkup:
    """Действия после генерации идей."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel-калькуляция", callback_data="grant_excel")],
        [InlineKeyboardButton(text="📄 Документы на подачу", callback_data="grant_docs")],
        [InlineKeyboardButton(text="💾 Сохранить идею", callback_data="grant_save_idea")],
        [InlineKeyboardButton(text="💡 Ещё идеи", callback_data="grant_ideas")],
        [InlineKeyboardButton(text="◀️ Инвестиции", callback_data="menu_money")],
    ])


def saved_ideas_kb() -> InlineKeyboardMarkup:
    """Клавиатура для списка сохранённых идей."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Сканировать гранты", callback_data="money_scan")],
        [InlineKeyboardButton(text="◀️ Инвестиции", callback_data="menu_money")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def scan_results_kb(results: list[dict]) -> InlineKeyboardMarkup:
    """Динамическая клавиатура: кнопка на каждый найденный грант."""
    rows = []
    for i, r in enumerate(results):
        rel = r.get("relevance", 0)
        icon = "🟢" if rel > 0.6 else "🟡" if rel > 0.3 else "⚪"
        title = r.get("title", "")
        rows.append([InlineKeyboardButton(
            text=f"{icon} {i+1}. {title}",
            callback_data=f"scan_grant_{i}",
        )])
    rows.append([InlineKeyboardButton(text="◀️ Инвестиции", callback_data="menu_money")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ideas_list_kb(ideas: list[dict]) -> InlineKeyboardMarkup:
    """Динамическая клавиатура: кнопка на каждую сгенерированную идею."""
    rows = []
    for i, idea in enumerate(ideas[:7]):
        title = idea.get("title", "")[:50]
        rows.append([InlineKeyboardButton(
            text=f"💡 {i+1}. {title}",
            callback_data=f"idea_{i}",
        )])
    rows.append([InlineKeyboardButton(text="💾 Сохранить все идеи", callback_data="grant_save_all")])
    rows.append([InlineKeyboardButton(text="📄 Документы на подачу", callback_data="grant_docs")])
    rows.append([InlineKeyboardButton(text="◀️ Инвестиции", callback_data="menu_money")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def idea_selected_kb(idea_idx: int) -> InlineKeyboardMarkup:
    """Клавиатура после выбора конкретной идеи и генерации Excel."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Документы на подачу", callback_data="grant_docs")],
        [InlineKeyboardButton(text="💾 Сохранить идею", callback_data="grant_save_idea")],
        [InlineKeyboardButton(text="💡 Назад к идеям", callback_data="back_to_ideas")],
        [InlineKeyboardButton(text="◀️ Инвестиции", callback_data="menu_money")],
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
        [InlineKeyboardButton(text="🧠 Задать вопрос Гендиректору", callback_data="task_ask")],
        [InlineKeyboardButton(text="📋 Поставить задачу", callback_data="task_assign")],
        [InlineKeyboardButton(text="🔄 Стратегический план", callback_data="task_strategy")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


# ─── Юрист / Бухгалтер ─────────────────────────────────────────────────


def legal_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚖️ Юридическая консультация", callback_data="legal_consult")],
        [InlineKeyboardButton(text="📄 Проверка договора", callback_data="legal_contract")],
        [InlineKeyboardButton(text="📝 Регистрация ИП", callback_data="legal_ip_reg")],
        [InlineKeyboardButton(text="👷 Трудовое право", callback_data="legal_labor")],
        [InlineKeyboardButton(text="🧮 Налоговая консультация", callback_data="acc_consult")],
        [InlineKeyboardButton(text="📊 Сравнить УСН/ОСН/Патент", callback_data="acc_tax_compare")],
        [InlineKeyboardButton(text="📅 Календарь отчетности", callback_data="acc_calendar")],
        [InlineKeyboardButton(text="💰 Расчет зарплаты", callback_data="acc_payroll")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


def back_to_legal_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Юрист / Бухгалтер", callback_data="menu_legal")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
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
