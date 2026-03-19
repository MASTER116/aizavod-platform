"""Unit tests: Credit-based billing metering limits per tier."""

import pytest
from services.billing.metering import (
    get_usage_meter, UsageMeter, TIER_CREDITS, TIER_LIMITS,
    AGENT_CREDITS, get_agent_credit_cost, get_orchestration_cost,
)


class TestMeteringLimits:
    def setup_method(self):
        self.meter = UsageMeter()

    def test_free_tier_credit_limit(self):
        user_id = 1
        daily_credits = TIER_CREDITS["free"]["daily_credits"]
        assert daily_credits == 30

        # Use simple agent (1 credit each) up to limit
        for _ in range(daily_credits):
            can, msg = self.meter.can_call(user_id, "free", agent_name="namer_agent")
            assert can
            self.meter.record(user_id, agent_name="namer_agent", tier="free")

        # Should block after limit
        can, msg = self.meter.can_call(user_id, "free", agent_name="namer_agent")
        assert not can
        assert "лимит" in msg.lower() or "Апгрейд" in msg

    def test_starter_tier_credits(self):
        assert TIER_CREDITS["starter"]["monthly_credits"] == 5000
        assert TIER_CREDITS["starter"]["daily_credits"] == 250

    def test_pro_tier_credits(self):
        assert TIER_CREDITS["pro"]["monthly_credits"] == 25000
        assert TIER_CREDITS["pro"]["daily_credits"] == 1250

    def test_enterprise_tier_credits(self):
        assert TIER_CREDITS["enterprise"]["monthly_credits"] == 100000

    def test_agent_credit_costs(self):
        """Verify credit costs match agent complexity."""
        assert get_agent_credit_cost("namer_agent") == 1      # Simple
        assert get_agent_credit_cost("idea_generator") == 1    # Simple
        assert get_agent_credit_cost("lawyer_agent") == 3      # Medium
        assert get_agent_credit_cost("certifier") == 8         # Heavy
        assert get_agent_credit_cost("ceo_agent") == 8         # Orchestration
        assert get_agent_credit_cost("qa_agent") == 0          # System (free)

    def test_extended_thinking_multiplier(self):
        base = get_agent_credit_cost("certifier")
        thinking = get_agent_credit_cost("certifier", use_thinking=True)
        assert thinking == base * 3

    def test_orchestration_cost(self):
        # CEO (8) + 3 directors × 3 = 17
        cost = get_orchestration_cost(3)
        assert cost == 8 + 3 * 3

    def test_heavy_agent_blocks_sooner(self):
        """Heavy agents (8 credits) exhaust free tier faster than simple ones."""
        user_id = 2
        # Free tier: 30 credits/day. Certifier = 8 credits.
        # 30 / 8 = 3 calls max
        for _ in range(3):
            can, _ = self.meter.can_call(user_id, "free", agent_name="certifier")
            assert can
            self.meter.record(user_id, agent_name="certifier", tier="free")

        # 4th call should fail (24 used + 8 needed = 32 > 30)
        can, msg = self.meter.can_call(user_id, "free", agent_name="certifier")
        assert not can

    def test_usage_tracking(self):
        self.meter.record(42, agent_name="pricing_agent", tokens=500, cost_usd=0.01, tier="starter")
        stats = self.meter.get_user_stats(42)
        assert stats["calls"] == 1
        assert stats["tokens"] == 500
        assert stats["tier"] == "starter"
        assert stats["credits_used_today"] == 3  # pricing = 3 credits

    def test_per_agent_tracking(self):
        self.meter.record(42, agent_name="namer_agent", tier="starter")
        self.meter.record(42, agent_name="namer_agent", tier="starter")
        self.meter.record(42, agent_name="certifier", tier="starter")
        stats = self.meter.get_user_stats(42)
        assert stats["by_agent"]["namer_agent"]["calls"] == 2
        assert stats["by_agent"]["namer_agent"]["credits"] == 2
        assert stats["by_agent"]["certifier"]["calls"] == 1
        assert stats["by_agent"]["certifier"]["credits"] == 8
        assert stats["credits_used_today"] == 10  # 2×1 + 1×8

    def test_workflow_tracking(self):
        self.meter.record(42, agent_name="ceo_agent", tier="pro")
        self.meter.record_workflow(42, num_directors=2)
        stats = self.meter.get_user_stats(42)
        assert stats["workflows"] == 1

    def test_outcome_tracking(self):
        self.meter.record(42, agent_name="certifier", tier="pro")
        self.meter.record_outcome(42)
        stats = self.meter.get_user_stats(42)
        assert stats["outcomes"] == 1

    def test_summary(self):
        self.meter.record(1, agent_name="namer_agent", tier="free")
        self.meter.record(2, agent_name="certifier", tier="starter")
        summary = self.meter.get_summary()
        assert summary["active_users"] == 2
        assert summary["total_calls_today"] == 2
        assert summary["total_credits_today"] == 9  # 1 + 8
        assert summary["pricing_model"] == "credit-based (hybrid 2026)"

    def test_pricing_info(self):
        info = self.meter.get_pricing_info()
        assert info["model"] == "credit-based"
        assert "starter" in info["tiers"]
        assert info["tiers"]["starter"]["price_rub"] == 4990
        assert info["agent_costs"]["certifier"] == 8
        assert info["agent_costs"]["namer_agent"] == 1

    def test_backwards_compat(self):
        """TIER_LIMITS still works for backwards compatibility."""
        assert "free" in TIER_LIMITS
        assert "daily_calls" in TIER_LIMITS["free"]
