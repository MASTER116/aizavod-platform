"""Simple in-memory rate limiter with daily reset.

FREE tier: 3 questions per day per user.
"""
from __future__ import annotations

import os
from datetime import date


FREE_DAILY_LIMIT = int(os.getenv("CERTIFIER_FREE_LIMIT", "3"))

# {user_id: (date, count)}
_usage: dict[int, tuple[date, int]] = {}


def check_limit(user_id: int) -> tuple[bool, int]:
    """Return (allowed, remaining).

    Resets at midnight UTC.
    """
    today = date.today()
    day, count = _usage.get(user_id, (today, 0))

    if day != today:
        count = 0

    if count >= FREE_DAILY_LIMIT:
        return False, 0

    count += 1
    _usage[user_id] = (today, count)
    return True, FREE_DAILY_LIMIT - count
