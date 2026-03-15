"""CERTIFIER Telegram Bot — AI-консультант по сертификации ТС в ЕАЭС.

Публичный бот. FREE: 3 вопроса/день. STARTER: безлимит.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .handlers import router

logger = logging.getLogger("aizavod.certifier_bot")


def create_bot() -> tuple[Bot, Dispatcher]:
    token = os.getenv("CERTIFIER_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("CERTIFIER_BOT_TOKEN not set")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp


async def run_bot() -> None:
    bot, dp = create_bot()
    logger.info("CERTIFIER bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(run_bot())
