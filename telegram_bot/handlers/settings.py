"""Settings management handler."""
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
    """Show current settings with toggle buttons."""
    try:
        settings = await _api("GET", "/admin/api/settings")
        text = f"""⚙️ **Settings**

📊 Posts/day: {settings['posts_per_day']}
📸 Stories/day: {settings['stories_per_day']}
🎬 Reels/week: {settings['reels_per_week']}
🌐 Language: {settings['caption_language']}
🖼 Quality: {settings['image_quality']}

Toggle automation below:"""

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
        await callback.message.edit_text(f"❌ Error: {e}", reply_markup=back_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_"))
async def cb_toggle_setting(callback: CallbackQuery):
    """Toggle an automation setting."""
    setting_name = callback.data.replace("toggle_", "")

    try:
        current = await _api("GET", "/admin/api/settings")
        new_value = not current.get(setting_name, False)

        await _api("PUT", "/admin/api/settings", json_data={setting_name: new_value})

        # Refresh settings view
        await cb_settings(callback)
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data == "costs")
async def cb_costs(callback: CallbackQuery):
    """Show API cost summary."""
    try:
        # For now, calculate from posts
        posts = await _api("GET", "/admin/api/posts?limit=200")
        if isinstance(posts, list):
            total_cost = sum(p.get("generation_cost_usd", 0) for p in posts)
            total_posts = len(posts)
        else:
            total_cost = 0
            total_posts = 0

        text = f"""💰 **Cost Report**

📊 Total posts: {total_posts}
💵 Total spent: ${total_cost:.2f}
📈 Avg per post: ${(total_cost / total_posts) if total_posts else 0:.3f}"""

        await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    except Exception as e:
        await callback.message.edit_text(f"❌ Error: {e}", reply_markup=back_kb())
    await callback.answer()
