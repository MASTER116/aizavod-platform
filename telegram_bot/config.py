"""Telegram bot configuration."""
from __future__ import annotations

import os


def get_bot_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def get_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_TELEGRAM_IDS", "")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def get_backend_url() -> str:
    return os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")


def get_backend_api_key() -> str:
    return os.getenv("BACKEND_API_KEY", "")
