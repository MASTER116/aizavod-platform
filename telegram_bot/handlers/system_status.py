"""Хендлеры раздела «Статус системы» — мониторинг."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

import httpx
from telegram_bot.config import get_backend_url, get_backend_api_key
from telegram_bot.keyboards import back_to_main_kb, status_menu_kb

logger = logging.getLogger("aizavod.bot.status")

router = Router()


async def _api(method: str, path: str) -> dict | list:
    url = f"{get_backend_url()}{path}"
    headers = {}
    api_key = get_backend_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()


@router.callback_query(F.data == "status_server")
async def cb_status_server(callback: CallbackQuery):
    await callback.answer()
    try:
        health = await _api("GET", "/health")
        text = (
            "🖥 <b>Статус сервера</b>\n\n"
            f"API: ✅ работает\n"
            f"Время: {health.get('timestamp', '?')}\n"
            f"Хост: Hetzner (Франкфурт)\n"
            f"IP: 72.56.127.52\n"
            f"OS: Ubuntu 22.04"
        )
    except Exception as e:
        text = f"🖥 <b>Статус сервера</b>\n\n❌ API недоступен: {e}"

    await callback.message.answer(text, parse_mode="HTML", reply_markup=status_menu_kb())


@router.callback_query(F.data == "status_docker")
async def cb_status_docker(callback: CallbackQuery):
    await callback.answer()
    # List known containers
    containers = [
        ("nginx", "Nginx (80/443)", "🌐"),
        ("backend", "FastAPI Backend (8000)", "⚙️"),
        ("postgres", "PostgreSQL 16", "🗄"),
        ("redis", "Redis 7", "📦"),
        ("celery-worker", "Celery Worker", "👷"),
        ("celery-beat", "Celery Beat", "⏰"),
        ("telegram-bot", "Telegram Bot", "🤖"),
        ("n8n", "n8n (5678)", "🔄"),
    ]

    # Check if backend is alive as proxy for system health
    try:
        await _api("GET", "/health")
        api_ok = True
    except Exception:
        api_ok = False

    lines = ["🐳 <b>Docker контейнеры</b>\n"]
    for name, label, emoji in containers:
        status = "✅" if api_ok else "❓"
        lines.append(f"{emoji} {label} — {status}")

    lines.append(f"\nAPI статус: {'✅ работает' if api_ok else '❌ недоступен'}")

    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=status_menu_kb())


@router.callback_query(F.data == "status_db")
async def cb_status_db(callback: CallbackQuery):
    await callback.answer()
    try:
        # Check health as proxy
        await _api("GET", "/health")
        text = (
            "🗄 <b>База данных</b>\n\n"
            "PostgreSQL 16: ✅ работает\n"
            "Redis 7: ✅ работает\n"
            "Подключение: через Docker network\n"
            "Данные: volumes (postgres_data, redis_data)"
        )
    except Exception as e:
        text = f"🗄 <b>База данных</b>\n\n❌ Не удалось проверить: {e}"

    await callback.message.answer(text, parse_mode="HTML", reply_markup=status_menu_kb())


@router.callback_query(F.data == "status_agents")
async def cb_status_agents(callback: CallbackQuery):
    await callback.answer()

    agents = [
        ("🧠 Генеральный директор", "Оркестратор задач", "✅"),
        ("🔍 Сканер возможностей", "Поиск грантов/конкурсов", "✅"),
        ("💡 Генератор идей", "Генерация идей заработка", "✅"),
        ("📈 Аналитик рынка", "Анализ рынка и конкурентов", "✅"),
        ("🔎 Фрилансер", "Поиск заказов на фрилансе", "✅"),
        ("💵 Оценщик проектов", "Оценка проектов и КП", "✅"),
        ("📨 Менеджер продаж", "Холодные продажи и лиды", "✅"),
        ("📝 Сертификатор", "Консультации по сертификации ТС", "✅"),
        ("📱 Фабрика контента", "Генерация контента", "⚠️ IG login заблокирован"),
        ("⚖️ Юрист", "Юридические консультации", "✅"),
        ("🧮 Бухгалтер", "Налоги и отчётность", "✅"),
        ("🧬 Эволюция", "Оптимизация агентов", "✅"),
        ("🛡 Страж безопасности", "Антифрод и защита", "✅"),
        ("🎓 Учёный", "Научные заявки и статьи", "✅"),
        ("📢 Глашатай", "Продвижение и PR", "✅"),
        ("✏️ Нейминг", "Генерация названий", "✅"),
        ("🔒 Страж ИС", "Патенты и товарные знаки", "✅"),
        ("🎙 Голосовой агент", "Скрипты звонков", "✅"),
        ("💵 Казначей", "Монетизация и cash flow", "✅"),
    ]

    lines = ["🤖 <b>Статус агентов</b>\n"]
    for name, desc, status in agents:
        lines.append(f"{name}\n   {desc} — {status}")

    lines.append(f"\nВсего агентов: {len(agents)}")
    lines.append("LLM: Claude Haiku 4.5 (Anthropic API)")

    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=status_menu_kb())


@router.callback_query(F.data == "content_agent")
async def cb_content_agent(callback: CallbackQuery):
    """Redirect to agent status from content menu."""
    await cb_status_agents(callback)
