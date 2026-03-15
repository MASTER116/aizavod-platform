"""Telegram bot entry point — aiogram 3 with FSM and admin-only access."""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from .config import get_bot_token
from .middlewares import AdminOnlyMiddleware
from .handlers import start, dashboard, content, generation, settings, agent_admin, opportunities, money, ceo, system_status, conductor

logger = logging.getLogger("aizavod.bot")


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    """Create and configure bot + dispatcher with all handlers."""
    token = get_bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    # Admin-only middleware
    dp.message.middleware(AdminOnlyMiddleware())
    dp.callback_query.middleware(AdminOnlyMiddleware())

    # Register all handlers
    dp.include_router(start.router)
    dp.include_router(dashboard.router)
    dp.include_router(content.router)
    dp.include_router(generation.router)
    dp.include_router(settings.router)
    dp.include_router(agent_admin.router)
    dp.include_router(opportunities.router)
    dp.include_router(money.router)
    dp.include_router(ceo.router)
    dp.include_router(system_status.router)

    # CONDUCTOR — catch-all для свободного текста (ПОСЛЕДНИМ!)
    dp.include_router(conductor.router)

    return bot, dp


async def run_bot() -> None:
    """Start bot polling. Designed to be run as an asyncio task."""
    bot, dp = create_bot_and_dispatcher()
    logger.info("Starting Telegram bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())
