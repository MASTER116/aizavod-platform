"""Управление настройками."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery

import httpx
from telegram_bot.config import get_backend_url, get_backend_api_key
from telegram_bot.keyboards import settings_kb, back_kb

router = Router()


async def _api(method: str, path: str, json_data: dict = None) -> dict:
    url = f"{get_backend_url()}{path}"
    headers = {}
    api_key = get_backend_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, json=json_data, timeout=10)
        resp.raise_for_status()
        return resp.json()


@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery):
    try:
        settings = await _api("GET", "/admin/api/settings")
        text = f"""⚙️ **Настройки**

📊 Постов/день: {settings['posts_per_day']}
📸 Сторис/день: {settings['stories_per_day']}
🎬 Рилс/неделю: {settings['reels_per_week']}
🌐 Язык: {settings['caption_language']}
🖼 Качество: {settings['image_quality']}

Переключи автоматизацию ниже:"""

        await callback.message.edit_text(
            text,
            reply_markup=settings_kb(
                settings["auto_generate"],
                settings["auto_approve"],
                settings["auto_publish"],
                settings["auto_reply_comments"],
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=back_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_"))
async def cb_toggle_setting(callback: CallbackQuery):
    setting_name = callback.data.replace("toggle_", "")

    try:
        current = await _api("GET", "/admin/api/settings")
        new_value = not current.get(setting_name, False)

        await _api("PUT", "/admin/api/settings", json_data={setting_name: new_value})

        await cb_settings(callback)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "costs")
async def cb_costs(callback: CallbackQuery):
    try:
        posts = await _api("GET", "/admin/api/posts?limit=200")
        if isinstance(posts, list):
            total_cost = sum(p.get("generation_cost_usd", 0) for p in posts)
            total_posts = len(posts)
        else:
            total_cost = 0
            total_posts = 0

        text = f"""💰 **Отчёт о расходах**

📊 Всего постов: {total_posts}
💵 Потрачено: ${total_cost:.2f}
📈 Среднее за пост: ${(total_cost / total_posts) if total_posts else 0:.3f}"""

        await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=back_kb())
    await callback.answer()
