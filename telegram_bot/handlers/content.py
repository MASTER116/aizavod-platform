"""Просмотр и одобрение контента."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto, FSInputFile
from pathlib import Path

import httpx
from telegram_bot.config import get_backend_url, get_backend_api_key
from telegram_bot.keyboards import post_review_kb, back_kb

router = Router()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def _api(method: str, path: str, json_data: dict = None) -> dict | list:
    url = f"{get_backend_url()}{path}"
    headers = {}
    api_key = get_backend_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, json=json_data, timeout=30)
        resp.raise_for_status()
        return resp.json()


@router.callback_query(F.data == "next_posts")
async def cb_next_posts(callback: CallbackQuery):
    try:
        posts = await _api("GET", "/admin/api/posts?status=generated&limit=5")
        if not posts:
            posts = await _api("GET", "/admin/api/posts?status=scheduled&limit=5")

        if not posts:
            await callback.message.edit_text(
                "📋 Нет постов на проверку.",
                reply_markup=back_kb(),
            )
            await callback.answer()
            return

        post = posts[0]
        await _show_post(callback, post)

    except Exception as e:
        await callback.message.edit_text(
            f"Ошибка: {e}",
            reply_markup=back_kb(),
        )
    await callback.answer()


async def _show_post(callback: CallbackQuery, post: dict):
    status_emoji = {
        "draft": "📝", "generating": "⏳", "generated": "✨",
        "approved": "✅", "scheduled": "📅", "published": "📱",
        "failed": "❌",
    }
    status_label = {
        "draft": "черновик", "generating": "генерация", "generated": "создан",
        "approved": "одобрен", "scheduled": "запланирован", "published": "опубликован",
        "failed": "ошибка",
    }

    emoji = status_emoji.get(post["status"], "❓")
    label = status_label.get(post["status"], post["status"])
    text = f"""{emoji} **Пост #{post['id']}** [{label}]

📂 Категория: {post['category']}
🖼 Тип: {post['content_type']}

🇷🇺 {post.get('caption_ru', 'Нет подписи') or 'Нет подписи'}

🇬🇧 {post.get('caption_en', 'Нет подписи') or 'Нет подписи'}

💰 Стоимость: ${post.get('generation_cost_usd', 0):.3f}"""

    if post.get("image_path"):
        image_abs = _PROJECT_ROOT / post["image_path"].lstrip("/")
        if image_abs.exists():
            photo = FSInputFile(str(image_abs))
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=post_review_kb(post["id"]),
                parse_mode="Markdown",
            )
            return

    await callback.message.edit_text(
        text,
        reply_markup=post_review_kb(post["id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])
    try:
        post = await _api("POST", f"/admin/api/posts/{post_id}/approve")
        await callback.message.edit_caption(
            caption=f"✅ Пост #{post_id} одобрен!",
            reply_markup=back_kb(),
        )
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])
    try:
        await _api("POST", f"/admin/api/posts/{post_id}/reject")
        await callback.message.edit_caption(
            caption=f"❌ Пост #{post_id} отклонён. Перемещён в черновик.",
            reply_markup=back_kb(),
        )
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("regen_"))
async def cb_regenerate(callback: CallbackQuery):
    post_id = int(callback.data.split("_")[1])
    await callback.answer("🔄 Переделываю... Может занять некоторое время.", show_alert=True)
    try:
        post = await _api("POST", f"/admin/api/posts/{post_id}/generate")
        await _show_post(callback, post)
    except Exception as e:
        await callback.message.edit_text(
            f"Ошибка переделки: {e}",
            reply_markup=back_kb(),
        )
