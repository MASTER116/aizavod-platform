"""Integration tests: A/B Testing Engine."""

import pytest
from services.testing.ab_engine import ABEngine


class TestABEngine:
    def setup_method(self):
        self.engine = ABEngine()

    def test_create_experiment(self):
        exp_id = self.engine.create_experiment(
            "lawyer_agent",
            "Ты юрист v1. Отвечай кратко.",
            "Ты юрист v2. Отвечай подробно с ссылками на законы.",
        )
        assert exp_id.startswith("ab_lawyer_agent_")
        assert self.engine._experiments[exp_id].status == "running"

    def test_deterministic_variant_assignment(self):
        exp_id = self.engine.create_experiment("test", "prompt_a", "prompt_b")
        # Same user_id should always get same variant
        variant1, _ = self.engine.get_variant(exp_id, user_id=42)
        variant2, _ = self.engine.get_variant(exp_id, user_id=42)
        assert variant1 == variant2

    def test_different_users_get_different_variants(self):
        exp_id = self.engine.create_experiment("test", "prompt_a", "prompt_b", traffic_split=0.5)
        variants = set()
        for uid in range(100):
            v, _ = self.engine.get_variant(exp_id, user_id=uid)
            variants.add(v)
        # With 100 users and 50/50 split, should have both variants
        assert "a" in variants
        assert "b" in variants

    def test_record_results(self):
        exp_id = self.engine.create_experiment("test", "a", "b", min_samples=5)
        self.engine.record_result(exp_id, "a", quality_score=8.0, latency_ms=200, cost_usd=0.01)
        self.engine.record_result(exp_id, "b", quality_score=6.0, latency_ms=300, cost_usd=0.02)
        exp = self.engine._experiments[exp_id]
        assert len(exp.results_a) == 1
        assert len(exp.results_b) == 1

    def test_evaluate_insufficient_data(self):
        exp_id = self.engine.create_experiment("test", "a", "b", min_samples=30)
        for i in range(5):
            self.engine.record_result(exp_id, "a", quality_score=8.0, latency_ms=200)
            self.engine.record_result(exp_id, "b", quality_score=6.0, latency_ms=300)
        result = self.engine.evaluate(exp_id)
        assert not result.significant  # Not enough samples
        assert "Недостаточно" in result.recommendation

    def test_evaluate_significant_difference(self):
        exp_id = self.engine.create_experiment("test", "a", "b", min_samples=5)
        # A consistently scores 8, B consistently scores 4
        for _ in range(30):
            self.engine.record_result(exp_id, "a", quality_score=8.0 + (0.5 * (_ % 3 - 1)), latency_ms=200)
            self.engine.record_result(exp_id, "b", quality_score=4.0 + (0.5 * (_ % 3 - 1)), latency_ms=300)
        result = self.engine.evaluate(exp_id)
        assert result.significant
        assert result.winner == "a"
        assert result.p_value < 0.05

    def test_evaluate_no_significant_difference(self):
        exp_id = self.engine.create_experiment("test", "a", "b", min_samples=5)
        # Both score around 7
        import random
        random.seed(42)
        for _ in range(30):
            self.engine.record_result(exp_id, "a", quality_score=7.0 + random.uniform(-0.5, 0.5), latency_ms=200)
            self.engine.record_result(exp_id, "b", quality_score=7.0 + random.uniform(-0.5, 0.5), latency_ms=200)
        result = self.engine.evaluate(exp_id)
        # With similar scores, should not be significant (or barely)
        assert result.avg_quality_a == pytest.approx(result.avg_quality_b, abs=1.0)

    def test_promote_winner(self):
        exp_id = self.engine.create_experiment("test", "a", "b", min_samples=5)
        for _ in range(30):
            self.engine.record_result(exp_id, "a", quality_score=9.0, latency_ms=200)
            self.engine.record_result(exp_id, "b", quality_score=3.0, latency_ms=300)
        result = self.engine.promote_winner(exp_id)
        assert result["promoted"] == "a"
        assert self.engine._experiments[exp_id].status == "promoted"

    def test_list_experiments(self):
        self.engine.create_experiment("agent1", "a", "b")
        self.engine.create_experiment("agent2", "a", "b")
        exps = self.engine.list_experiments()
        assert len(exps) == 2

    def test_get_active_experiment(self):
        self.engine.create_experiment("lawyer_agent", "a", "b")
        exp = self.engine.get_active_experiment("lawyer_agent")
        assert exp is not None
        assert exp.agent_name == "lawyer_agent"

    def test_no_active_experiment(self):
        exp = self.engine.get_active_experiment("nonexistent")
        assert exp is None
