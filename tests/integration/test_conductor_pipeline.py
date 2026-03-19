"""Integration tests: Full CONDUCTOR pipeline with mock LLM."""

import pytest
from services.conductor.registry import AGENTS


@pytest.mark.integration
class TestKeywordRoutingGolden:
    """Golden dataset: 20 queries → correct agent (keyword-based, no LLM)."""

    def _keyword_match(self, query: str) -> tuple[str, int]:
        query_lower = query.lower()
        scores = {}
        for agent in AGENTS:
            score = sum(1 for kw in agent.keywords if kw in query_lower)
            if score > 0:
                scores[agent.name] = score
        if scores:
            best = max(scores, key=scores.get)
            return best, scores[best]
        return "ceo_agent", 0

    def test_golden_routing(self, golden_routing_tests):
        """Test all golden routing cases."""
        passed = 0
        failed = []

        for case in golden_routing_tests:
            agent, score = self._keyword_match(case["input"])
            expected = case["expected_agent"]
            if agent == expected:
                passed += 1
            else:
                failed.append(f"'{case['input'][:50]}' → got {agent}, expected {expected}")

        total = len(golden_routing_tests)
        accuracy = passed / total if total > 0 else 0

        # Report
        if failed:
            print(f"\nRouting accuracy: {accuracy:.0%} ({passed}/{total})")
            for f in failed:
                print(f"  FAIL: {f}")

        # At least 80% accuracy on golden dataset
        assert accuracy >= 0.8, f"Routing accuracy {accuracy:.0%} < 80%. Failures: {failed}"


@pytest.mark.integration
class TestComplianceGolden:
    """Golden dataset: PII detection accuracy."""

    def test_golden_compliance(self, golden_compliance_tests):
        from services.compliance_agent import get_compliance_agent
        compliance = get_compliance_agent()

        passed = 0
        failed = []

        for case in golden_compliance_tests:
            result = compliance.check_pii(case["input"])
            detected = result["total_pii_count"] > 0

            if detected == case["should_detect"]:
                passed += 1
            else:
                failed.append(
                    f"'{case['input'][:50]}' → detected={detected}, expected={case['should_detect']}"
                )

        total = len(golden_compliance_tests)
        accuracy = passed / total if total > 0 else 0

        assert accuracy >= 0.9, f"PII detection accuracy {accuracy:.0%} < 90%. Failures: {failed}"


@pytest.mark.integration
class TestModeDetection:
    """Test router vs orchestrator mode detection."""

    def test_question_mode(self):
        from services.conductor.core import Conductor
        c = Conductor()
        assert c._detect_mode("Сколько стоит сертификация?") == "router"
        assert c._detect_mode("Что такое ТР ТС?") == "router"
        assert c._detect_mode("Как зарегистрировать ООО?") == "router"

    def test_task_mode(self):
        from services.conductor.core import Conductor
        c = Conductor()
        assert c._detect_mode("Создай коммерческое предложение") == "orchestrator"
        assert c._detect_mode("Разработай план маркетинга") == "orchestrator"
        assert c._detect_mode("Сделай анализ конкурентов") == "orchestrator"

    def test_ambiguous_defaults_to_router(self):
        from services.conductor.core import Conductor
        c = Conductor()
        assert c._detect_mode("Привет") == "router"
        assert c._detect_mode("AI агенты") == "router"
