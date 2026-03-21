"""Credit-Based Usage Metering — кредитная система биллинга.

Модель 2026 (hybrid): подписка с кредитами, разная стоимость агентов.
- Простой агент (namer, idea) = 1 кредит
- Средний (pricing, outreach, lawyer) = 3 кредита
- Тяжёлый (certifier RAG) = 8 кредитов
- Очень тяжёлый (certifier Sonnet) = 15 кредитов
- Оркестрация CEO = 8-25 кредитов

Маржа: 45-82% при любом поведении пользователя (vs -364% при flat calls).
Безубыточность: 3 клиента STARTER.

Источники:
- Chargebee 2026 Playbook: outcome + action + hybrid models
- Intercom Fin: $0.99/resolution (outcome-based)
- Cursor/Replit: lessons on flat-to-credit transition
- a16z: LLM costs drop 10x/year → пересматривать quarterly
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

logger = logging.getLogger("aizavod.billing")


# ─── Credit costs per agent type ──────────────────────────────────────────────

# Привязаны к реальной себестоимости (Claude Haiku 4.5, март 2026)
# 1 кредит ≈ $0.005 себестоимости, продаём за ~$0.008
AGENT_CREDITS: dict[str, int] = {
    # Простые (1 кредит, ~$0.002 cost)
    "namer_agent": 1,
    "idea_generator": 1,

    # Лёгкие (2 кредита, ~$0.003 cost)
    "herald_agent": 2,
    "voice_agent": 2,
    "scholar_agent": 2,

    # Средние (3 кредита, ~$0.005 cost)
    "lawyer_agent": 3,
    "accountant_agent": 3,
    "pricing_agent": 3,
    "outreach_agent": 3,
    "content_factory": 3,
    "market_analyzer": 3,
    "freelance_agent": 3,
    "guardian_agent": 3,
    "guardian_ip_agent": 3,
    "treasurer_agent": 3,
    "oracle_agent": 3,

    # Тяжёлые (8 кредитов, ~$0.015 cost — RAG + длинный контекст)
    "certifier": 8,
    "opportunity_scanner": 5,
    "darwin_agent": 5,

    # Оркестрация CEO (8-25 кредитов в зависимости от depth)
    "ceo_agent": 8,

    # Системные (0 — не считаются)
    "qa_agent": 0,
    "compliance_agent": 0,
    "system": 0,
}

# Доп. стоимость за extended thinking
EXTENDED_THINKING_MULTIPLIER = 3  # 3x кредитов

# Доп. стоимость за оркестрацию (per director involved)
ORCHESTRATION_PER_DIRECTOR = 3  # +3 кредита за каждого директора


# ─── Tier definitions (кредитная модель) ──────────────────────────────────────

TIER_CREDITS = {
    "free": {
        "monthly_credits": 900,          # 30/day × 30 days
        "daily_credits": 30,
        "price_rub": 0,
        "price_usd": 0,
        "max_agents": 5,                 # Только базовые агенты
        "features": ["basic_agents"],
        "description": "Бесплатный: 30 кредитов/день, базовые агенты",
    },
    "starter": {
        "monthly_credits": 5000,
        "daily_credits": 250,            # ~167/day average, burst до 250
        "price_rub": 4990,
        "price_usd": 55,
        "max_agents": 15,
        "features": ["basic_agents", "medium_agents", "pdf_export"],
        "description": "Starter: 5000 кредитов/мес, 15 агентов",
    },
    "pro": {
        "monthly_credits": 25000,
        "daily_credits": 1250,
        "price_rub": 14990,
        "price_usd": 165,
        "max_agents": 21,
        "features": ["all_agents", "orchestration", "darwin", "pdf_export", "priority_support"],
        "description": "Pro: 25000 кредитов/мес, все агенты + оркестрация",
    },
    "enterprise": {
        "monthly_credits": 100000,
        "daily_credits": 5000,
        "price_rub": 49990,
        "price_usd": 550,
        "max_agents": 999,
        "features": ["all_agents", "orchestration", "darwin", "custom_agents", "sla", "outcome_pricing"],
        "description": "Enterprise: 100K кредитов/мес + outcome-based pricing",
    },
}

# Backwards compatibility alias
TIER_LIMITS = {
    tier: {
        "daily_calls": data["daily_credits"],
        "daily_tokens": data["daily_credits"] * 2000,
        "monthly_cost_usd": data["price_usd"],
    }
    for tier, data in TIER_CREDITS.items()
}


def get_agent_credit_cost(agent_name: str, use_thinking: bool = False) -> int:
    """Получить стоимость вызова агента в кредитах."""
    base = AGENT_CREDITS.get(agent_name, 3)  # Default: 3 (средний)
    if use_thinking:
        base *= EXTENDED_THINKING_MULTIPLIER
    return base


def get_orchestration_cost(num_directors: int) -> int:
    """Стоимость оркестрации в кредитах (CEO + директора)."""
    return AGENT_CREDITS.get("ceo_agent", 8) + num_directors * ORCHESTRATION_PER_DIRECTOR


# ─── User Usage (credit-based) ────────────────────────────────────────────────

class UserUsage:
    """Трекинг использования для одного пользователя (кредитная модель)."""

    def __init__(self, user_id: int, tier: str = "free"):
        self.user_id = user_id
        self.tier = tier
        self._daily: dict[str, dict] = {}
        self._monthly: dict[str, dict] = {}

    def _today_key(self) -> str:
        return date.today().isoformat()

    def _month_key(self) -> str:
        return date.today().strftime("%Y-%m")

    def _get_today(self) -> dict:
        key = self._today_key()
        if key not in self._daily:
            self._daily[key] = {
                "credits_used": 0, "calls": 0, "tokens": 0,
                "cost_usd": 0.0, "outcomes": 0, "workflows": 0,
                "by_agent": {},
            }
        return self._daily[key]

    def _get_month(self) -> dict:
        key = self._month_key()
        if key not in self._monthly:
            self._monthly[key] = {"credits_used": 0, "calls": 0, "cost_usd": 0.0}
        return self._monthly[key]

    def record_call(
        self,
        agent_name: str = "",
        credits: int = 0,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Записать использование с кредитами."""
        if credits == 0 and agent_name:
            credits = get_agent_credit_cost(agent_name)

        today = self._get_today()
        today["credits_used"] += credits
        today["calls"] += 1
        today["tokens"] += tokens
        today["cost_usd"] += cost_usd

        # Per-agent tracking
        if agent_name:
            agent_stats = today["by_agent"].get(agent_name, {"calls": 0, "credits": 0})
            agent_stats["calls"] += 1
            agent_stats["credits"] += credits
            today["by_agent"][agent_name] = agent_stats

        # Monthly rollup
        month = self._get_month()
        month["credits_used"] += credits
        month["calls"] += 1
        month["cost_usd"] += cost_usd

    def record_workflow(self, num_directors: int = 1) -> None:
        """Записать оркестрацию."""
        credits = get_orchestration_cost(num_directors)
        self._get_today()["workflows"] += 1
        self._get_today()["credits_used"] += credits
        self._get_month()["credits_used"] += credits

    def record_outcome(self) -> None:
        self._get_today()["outcomes"] += 1

    def can_make_call(self, agent_name: str = "") -> tuple[bool, str]:
        """Проверить хватает ли кредитов для вызова."""
        tier_data = TIER_CREDITS.get(self.tier, TIER_CREDITS["free"])
        today = self._get_today()
        month = self._get_month()

        # Credit cost for this call
        credits_needed = get_agent_credit_cost(agent_name) if agent_name else 3

        # Daily limit
        if today["credits_used"] + credits_needed > tier_data["daily_credits"]:
            remaining = max(0, tier_data["daily_credits"] - today["credits_used"])
            return False, (
                f"Дневной лимит кредитов исчерпан "
                f"({today['credits_used']}/{tier_data['daily_credits']}). "
                f"Осталось: {remaining}. "
                f"Этот агент стоит {credits_needed} кр. "
                f"Апгрейд: /upgrade"
            )

        # Monthly limit
        if month["credits_used"] + credits_needed > tier_data["monthly_credits"]:
            remaining = max(0, tier_data["monthly_credits"] - month["credits_used"])
            return False, (
                f"Месячный лимит кредитов исчерпан "
                f"({month['credits_used']}/{tier_data['monthly_credits']}). "
                f"Осталось: {remaining}. "
                f"Апгрейд: /upgrade"
            )

        # Warning at 80%
        daily_pct = today["credits_used"] / max(tier_data["daily_credits"], 1)
        if daily_pct >= 0.8:
            remaining = tier_data["daily_credits"] - today["credits_used"]
            logger.info(
                "User %d at %.0f%% daily credit limit (%d remaining)",
                self.user_id, daily_pct * 100, remaining,
            )

        return True, "ok"

    def get_today_stats(self) -> dict:
        tier_data = TIER_CREDITS.get(self.tier, TIER_CREDITS["free"])
        today = self._get_today()
        month = self._get_month()
        daily_limit = tier_data["daily_credits"]
        monthly_limit = tier_data["monthly_credits"]

        return {
            "user_id": self.user_id,
            "tier": self.tier,
            "date": self._today_key(),
            # Credits (основная метрика)
            "credits_used_today": today["credits_used"],
            "credits_limit_daily": daily_limit,
            "credits_remaining_today": max(0, daily_limit - today["credits_used"]),
            "credits_used_month": month["credits_used"],
            "credits_limit_monthly": monthly_limit,
            "credits_remaining_month": max(0, monthly_limit - month["credits_used"]),
            # Legacy (backwards compat)
            "calls": today["calls"],
            "calls_limit": daily_limit,
            "calls_remaining": max(0, daily_limit - today["credits_used"]),
            # Details
            "tokens": today["tokens"],
            "cost_usd": f"${today['cost_usd']:.4f}",
            "workflows": today["workflows"],
            "outcomes": today["outcomes"],
            "usage_percent_daily": f"{today['credits_used'] / max(daily_limit, 1) * 100:.0f}%",
            "usage_percent_monthly": f"{month['credits_used'] / max(monthly_limit, 1) * 100:.0f}%",
            "by_agent": today["by_agent"],
            "tier_price_rub": tier_data["price_rub"],
        }


# ─── Usage Meter (central) ────────────────────────────────────────────────────

class UsageMeter:
    """Центральный credit metering для всех пользователей."""

    def __init__(self):
        self._users: dict[int, UserUsage] = {}

    def get_or_create(self, user_id: int, tier: str = "free") -> UserUsage:
        if user_id not in self._users:
            self._users[user_id] = UserUsage(user_id, tier)
        usage = self._users[user_id]
        if tier != "free":
            usage.tier = tier
        return usage

    def can_call(self, user_id: int, tier: str = "free", agent_name: str = "") -> tuple[bool, str]:
        """Проверить кредитный лимит перед вызовом."""
        return self.get_or_create(user_id, tier).can_make_call(agent_name)

    def record(
        self,
        user_id: int,
        agent_name: str = "",
        tokens: int = 0,
        cost_usd: float = 0.0,
        tier: str = "free",
    ) -> None:
        """Записать использование с автоматическим подсчётом кредитов."""
        self.get_or_create(user_id, tier).record_call(agent_name, 0, tokens, cost_usd)

    def record_workflow(self, user_id: int, num_directors: int = 1) -> None:
        if user_id in self._users:
            self._users[user_id].record_workflow(num_directors)

    def record_outcome(self, user_id: int) -> None:
        if user_id in self._users:
            self._users[user_id].record_outcome()

    def get_user_stats(self, user_id: int) -> dict:
        if user_id in self._users:
            return self._users[user_id].get_today_stats()
        return {"user_id": user_id, "tier": "free", "credits_used_today": 0, "calls": 0}

    def get_all_stats(self) -> list[dict]:
        return [u.get_today_stats() for u in self._users.values()]

    def get_summary(self) -> dict:
        today = date.today().isoformat()
        total_credits = sum(u._get_today()["credits_used"] for u in self._users.values())
        total_calls = sum(u._get_today()["calls"] for u in self._users.values())
        total_cost = sum(u._get_today()["cost_usd"] for u in self._users.values())

        # Estimated margin
        total_revenue_est = sum(
            TIER_CREDITS.get(u.tier, TIER_CREDITS["free"])["price_usd"] / 30
            for u in self._users.values()
        )

        return {
            "date": today,
            "active_users": len(self._users),
            "total_credits_today": total_credits,
            "total_calls_today": total_calls,
            "total_cost_today_usd": f"${total_cost:.4f}",
            "estimated_daily_revenue_usd": f"${total_revenue_est:.2f}",
            "estimated_margin": f"{(1 - total_cost / max(total_revenue_est, 0.01)) * 100:.0f}%" if total_revenue_est > 0 else "N/A",
            "tier_distribution": {
                tier: sum(1 for u in self._users.values() if u.tier == tier)
                for tier in TIER_CREDITS
            },
            "pricing_model": "credit-based (hybrid 2026)",
        }

    def get_pricing_info(self) -> dict:
        """Информация о тарифах для UI."""
        return {
            "tiers": {
                name: {
                    "price_rub": data["price_rub"],
                    "price_usd": data["price_usd"],
                    "monthly_credits": data["monthly_credits"],
                    "daily_credits": data["daily_credits"],
                    "max_agents": data["max_agents"],
                    "description": data["description"],
                }
                for name, data in TIER_CREDITS.items()
            },
            "agent_costs": AGENT_CREDITS,
            "model": "credit-based",
            "note": "1 кредит ≈ 1 простой запрос. Тяжёлые агенты стоят 3-25 кредитов.",
        }


# Singleton
_meter: UsageMeter | None = None


def get_usage_meter() -> UsageMeter:
    global _meter
    if _meter is None:
        _meter = UsageMeter()
    return _meter
