"""Admin-only access middleware."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update

from .config import get_admin_ids


class AdminOnlyMiddleware(BaseMiddleware):
    """Drop updates from non-admin users."""

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        admin_ids = get_admin_ids()
        if not admin_ids:
            return await handler(event, data)

        user = data.get("event_from_user")
        if user and user.id in admin_ids:
            return await handler(event, data)

        # Silently ignore non-admin users
        return None
