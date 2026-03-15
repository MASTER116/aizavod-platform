"""Singleton bot instance for use from services (notifications, alerts)."""
from __future__ import annotations

from typing import Optional

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from .config import get_bot_token

_bot: Optional[Bot] = None


def get_bot() -> Bot:
    """Get or create the singleton Bot instance."""
    global _bot
    if _bot is None:
        token = get_bot_token()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")
        _bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    return _bot
