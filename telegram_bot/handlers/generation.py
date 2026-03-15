"""Manual content generation handler."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import httpx
from telegram_bot.config import get_backend_url, get_backend_api_key
from telegram_bot.keyboards import category_kb, back_kb
from telegram_bot.states import ManualPostStates

router = Router()


async def _api(method: str, path: str, json_data: dict = None, params: dict = None) -> dict | list:
    url = f"{get_backend_url()}{path}"
    headers = {}
    api_key = get_backend_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, json=json_data, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()


@router.callback_query(F.data == "generate")
async def cb_generate(callback: CallbackQuery):
    """Show category selection for manual generation."""
    await callback.message.edit_text(
        "🎨 **Generate New Post**\n\nSelect content category:",
        reply_markup=category_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def cb_category_selected(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace("cat_", "")
    await state.update_data(category=category)
    await state.set_state(ManualPostStates.entering_prompt)

    await callback.message.edit_text(
        f"📂 Category: **{category}**\n\n"
        "Enter a description for the image (or send 'auto' for AI-generated prompt):",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(ManualPostStates.entering_prompt)
async def on_prompt_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    category = data["category"]
    prompt = message.text.strip()

    await message.answer("⏳ Generating post... This may take 30-60 seconds.")

    try:
        # Get active character
        characters = await _api("GET", "/admin/api/characters")
        if not characters:
            await message.answer("❌ No character configured. Create one first.", reply_markup=back_kb())
            await state.clear()
            return

        character_id = characters[0]["id"]

        # Create post
        post = await _api("POST", "/admin/api/posts", json_data={
            "character_id": character_id,
            "category": category,
            "content_type": "photo",
        })

        if prompt.lower() != "auto":
            await _api("PUT", f"/admin/api/posts/{post['id']}", json_data={
                "caption_ru": prompt,
            })

        # Generate image + caption
        result = await _api("POST", f"/admin/api/posts/{post['id']}/generate")

        # Show result
        from telegram_bot.keyboards import post_review_kb
        text = f"""✨ **Post Generated!**

📂 Category: {result['category']}
💰 Cost: ${result.get('generation_cost_usd', 0):.3f}

🇷🇺 {result.get('caption_ru', '')}

🇬🇧 {result.get('caption_en', '')}"""

        if result.get("image_path"):
            from pathlib import Path
            from aiogram.types import FSInputFile
            _PROJECT_ROOT = Path(__file__).resolve().parents[2]
            image_abs = _PROJECT_ROOT / result["image_path"].lstrip("/")
            if image_abs.exists():
                photo = FSInputFile(str(image_abs))
                await message.answer_photo(
                    photo=photo,
                    caption=text[:1024],
                    reply_markup=post_review_kb(result["id"]),
                    parse_mode="Markdown",
                )
                await state.clear()
                return

        await message.answer(text, reply_markup=post_review_kb(result["id"]), parse_mode="Markdown")

    except Exception as e:
        await message.answer(f"❌ Generation failed: {e}", reply_markup=back_kb())

    await state.clear()
