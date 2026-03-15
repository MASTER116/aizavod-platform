"""Дашборд — обзор метрик."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery

import httpx
from telegram_bot.config import get_backend_url, get_backend_api_key
from telegram_bot.keyboards import back_kb

router = Router()


async def _api(method: str, path: str) -> dict:
    url = f"{get_backend_url()}{path}"
    headers = {}
    api_key = get_backend_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()


@router.callback_query(F.data == "dashboard")
async def cb_dashboard(callback: CallbackQuery):
    try:
        posts = await _api("GET", "/admin/api/posts?status=published&limit=1")
        scheduled = await _api("GET", "/admin/api/posts?status=scheduled&limit=200")
        pending = await _api("GET", "/admin/api/posts?status=generated&limit=200")

        published_count = len(posts) if isinstance(posts, list) else 0
        scheduled_count = len(scheduled) if isinstance(scheduled, list) else 0
        pending_count = len(pending) if isinstance(pending, list) else 0

        text = f"""📊 **Дашборд**

📈 Опубликовано: {published_count} постов
📅 Запланировано: {scheduled_count} постов
⏳ На проверку: {pending_count} постов

_/start — главное меню_"""

    except Exception as e:
        text = f"Ошибка загрузки дашборда: {e}"

    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    await callback.answer()
