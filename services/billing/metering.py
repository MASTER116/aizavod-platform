"""Usage Metering — трекинг использования для биллинга.

Поддерживает 4 модели биллинга:
- Per-action: каждый вызов агента
- Per-workflow: полная оркестрация
- Per-outcome: только успешные результаты
- Subscription: месячный лимит

Реальность Q1 2026: $0.47/query × 1000/day = $470/day.
Без metering расходы выходят из-под контроля.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

logger = logging.getLogger("aizavod.billing")

# Лимиты по тарифам (calls per day)
TIER_LIMITS = {
    "free": {"daily_calls": 50, "daily_tokens": 100_000, "monthly_cost_usd": 0},
    "starter": {"daily_calls": 500, "daily_tokens": 1_000_000, "monthly_cost_usd": 50},
    "pro": {"daily_calls": 5000, "daily_tokens": 10_000_000, "monthly_cost_usd": 150},
    "enterprise": {"daily_calls": 50000, "daily_tokens": 100_000_000, "monthly_cost_usd": 500},
}


class UserUsage:
    """Трекинг использования для одного пользователя."""

    def __init__(self, user_id: int, tier: str = "free"):
        self.user_id = user_id
        self.tier = tier
        self._daily: dict[str, dict] = {}  # date → {calls, tokens, cost, outcomes}

    def _today_key(self) -> str:
        return date.today().isoformat()

    def _get_today(self) -> dict:
        key = self._today_key()
        if key not in self._daily:
            self._daily[key] = {"calls": 0, "tokens": 0, "cost_usd": 0.0, "outcomes": 0, "workflows": 0}
        return self._daily[key]

    def record_call(self, tokens: int = 0, cost_usd: float = 0.0) -> None:
        today = self._get_today()
        today["calls"] += 1
        today["tokens"] += tokens
        today["cost_usd"] += cost_usd

    def record_workflow(self) -> None:
        self._get_today()["workflows"] += 1

    def record_outcome(self) -> None:
        self._get_today()["outcomes"] += 1

    def can_make_call(self) -> tuple[bool, str]:
        """Проверить может ли пользователь сделать ещё один вызов."""
        limits = TIER_LIMITS.get(self.tier, TIER_LIMITS["free"])
        today = self._get_today()

        if today["calls"] >= limits["daily_calls"]:
            return False, f"Дневной лимит вызовов исчерпан ({limits['daily_calls']}). Апгрейд тарифа: /upgrade"

        if today["tokens"] >= limits["daily_tokens"]:
            return False, f"Дневной лимит токенов исчерпан ({limits['daily_tokens']:,}). Апгрейд тарифа: /upgrade"

        # Warning at 80%
        if today["calls"] >= limits["daily_calls"] * 0.8:
            remaining = limits["daily_calls"] - today["calls"]
            logger.info("User %d at 80%% daily limit (%d remaining)", self.user_id, remaining)

        return True, "ok"

    def get_today_stats(self) -> dict:
        limits = TIER_LIMITS.get(self.tier, TIER_LIMITS["free"])
        today = self._get_today()
        return {
            "user_id": self.user_id,
            "tier": self.tier,
            "date": self._today_key(),
            "calls": today["calls"],
            "calls_limit": limits["daily_calls"],
            "calls_remaining": max(0, limits["daily_calls"] - today["calls"]),
            "tokens": today["tokens"],
            "tokens_limit": limits["daily_tokens"],
            "cost_usd": f"${today['cost_usd']:.4f}",
            "workflows": today["workflows"],
            "outcomes": today["outcomes"],
            "usage_percent": f"{today['calls'] / max(limits['daily_calls'], 1) * 100:.0f}%",
        }


class UsageMeter:
    """Центральный metering для всех пользователей."""

    def __init__(self):
        self._users: dict[int, UserUsage] = {}

    def get_or_create(self, user_id: int, tier: str = "free") -> UserUsage:
        if user_id not in self._users:
            self._users[user_id] = UserUsage(user_id, tier)
        usage = self._users[user_id]
        if tier != "free":
            usage.tier = tier
        return usage

    def can_call(self, user_id: int, tier: str = "free") -> tuple[bool, str]:
        """Проверить лимит перед вызовом."""
        return self.get_or_create(user_id, tier).can_make_call()

    def record(self, user_id: int, tokens: int = 0, cost_usd: float = 0.0, tier: str = "free") -> None:
        """Записать использование."""
        self.get_or_create(user_id, tier).record_call(tokens, cost_usd)

    def record_workflow(self, user_id: int) -> None:
        if user_id in self._users:
            self._users[user_id].record_workflow()

    def record_outcome(self, user_id: int) -> None:
        if user_id in self._users:
            self._users[user_id].record_outcome()

    def get_user_stats(self, user_id: int) -> dict:
        if user_id in self._users:
            return self._users[user_id].get_today_stats()
        return {"user_id": user_id, "tier": "free", "calls": 0}

    def get_all_stats(self) -> list[dict]:
        return [u.get_today_stats() for u in self._users.values()]

    def get_summary(self) -> dict:
        today = date.today().isoformat()
        total_calls = sum(u._get_today()["calls"] for u in self._users.values())
        total_cost = sum(u._get_today()["cost_usd"] for u in self._users.values())
        return {
            "date": today,
            "active_users": len(self._users),
            "total_calls_today": total_calls,
            "total_cost_today_usd": f"${total_cost:.4f}",
            "tier_distribution": {
                tier: sum(1 for u in self._users.values() if u.tier == tier)
                for tier in TIER_LIMITS
            },
        }


# Singleton
_meter: UsageMeter | None = None


def get_usage_meter() -> UsageMeter:
    global _meter
    if _meter is None:
        _meter = UsageMeter()
    return _meter
