"""Unit tests: Billing metering limits per tier."""

import pytest
from services.billing.metering import get_usage_meter, UsageMeter, TIER_LIMITS


class TestMeteringLimits:
    def setup_method(self):
        # Fresh meter for each test
        self.meter = UsageMeter()

    def test_free_tier_limit(self):
        user_id = 1
        limit = TIER_LIMITS["free"]["daily_calls"]
        assert limit == 50

        # Should allow calls up to limit
        for _ in range(limit):
            can, msg = self.meter.can_call(user_id, "free")
            assert can
            self.meter.record(user_id, tokens=100, tier="free")

        # Should block after limit
        can, msg = self.meter.can_call(user_id, "free")
        assert not can
        assert "лимит" in msg.lower() or "Апгрейд" in msg

    def test_starter_tier_limit(self):
        assert TIER_LIMITS["starter"]["daily_calls"] == 500

    def test_pro_tier_limit(self):
        assert TIER_LIMITS["pro"]["daily_calls"] == 5000

    def test_enterprise_tier_limit(self):
        assert TIER_LIMITS["enterprise"]["daily_calls"] == 50000

    def test_usage_tracking(self):
        self.meter.record(42, tokens=500, cost_usd=0.01, tier="starter")
        stats = self.meter.get_user_stats(42)
        assert stats["calls"] == 1
        assert stats["tokens"] == 500
        assert stats["tier"] == "starter"

    def test_workflow_tracking(self):
        self.meter.record(42, tier="pro")
        self.meter.record_workflow(42)
        stats = self.meter.get_user_stats(42)
        assert stats["workflows"] == 1

    def test_outcome_tracking(self):
        self.meter.record(42, tier="pro")
        self.meter.record_outcome(42)
        stats = self.meter.get_user_stats(42)
        assert stats["outcomes"] == 1

    def test_summary(self):
        self.meter.record(1, tier="free")
        self.meter.record(2, tier="starter")
        summary = self.meter.get_summary()
        assert summary["active_users"] == 2
        assert summary["total_calls_today"] == 2
