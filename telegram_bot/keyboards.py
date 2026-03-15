"""Inline keyboard builders for the Telegram bot."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Dashboard", callback_data="dashboard"),
            InlineKeyboardButton(text="📋 Next Posts", callback_data="next_posts"),
        ],
        [
            InlineKeyboardButton(text="🎨 Generate", callback_data="generate"),
            InlineKeyboardButton(text="📸 Stories", callback_data="stories"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton(text="💰 Costs", callback_data="costs"),
        ],
        [
            InlineKeyboardButton(text="🔔 Alerts", callback_data="alerts"),
        ],
    ])


def post_review_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{post_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{post_id}"),
        ],
        [
            InlineKeyboardButton(text="🔄 Regenerate", callback_data=f"regen_{post_id}"),
            InlineKeyboardButton(text="📅 Schedule", callback_data=f"schedule_{post_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️ Back", callback_data="next_posts"),
        ],
    ])


def category_kb() -> InlineKeyboardMarkup:
    categories = [
        ("🏋️ Workout", "cat_workout"),
        ("🌿 Lifestyle", "cat_lifestyle"),
        ("💪 Motivation", "cat_motivation"),
        ("👗 Outfit", "cat_outfit"),
        ("🥗 Nutrition", "cat_nutrition"),
        ("📹 Behind Scenes", "cat_behind_scenes"),
        ("🔄 Transformation", "cat_transformation"),
        ("📚 Tutorial", "cat_tutorial"),
    ]
    rows = [[InlineKeyboardButton(text=t, callback_data=d)] for t, d in categories]
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_kb(auto_gen: bool, auto_approve: bool, auto_publish: bool, auto_reply: bool) -> InlineKeyboardMarkup:
    def toggle_icon(val: bool) -> str:
        return "✅" if val else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{toggle_icon(auto_gen)} Auto Generate",
            callback_data="toggle_auto_generate",
        )],
        [InlineKeyboardButton(
            text=f"{toggle_icon(auto_approve)} Auto Approve",
            callback_data="toggle_auto_approve",
        )],
        [InlineKeyboardButton(
            text=f"{toggle_icon(auto_publish)} Auto Publish",
            callback_data="toggle_auto_publish",
        )],
        [InlineKeyboardButton(
            text=f"{toggle_icon(auto_reply)} Auto Reply Comments",
            callback_data="toggle_auto_reply",
        )],
        [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")],
    ])


def confirm_kb(action: str, entity_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes", callback_data=f"confirm_{action}_{entity_id}"),
            InlineKeyboardButton(text="❌ No", callback_data="main_menu"),
        ],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="main_menu")],
    ])
