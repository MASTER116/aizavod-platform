"""Unit tests: Keyword-based routing (no LLM calls)."""

import pytest
from services.conductor.registry import AGENTS


class TestKeywordRouting:
    """Тестируем keyword matching без LLM."""

    def _match(self, query: str) -> tuple[str, int]:
        """Simulate keyword matching from Conductor._classify."""
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

    def test_lawyer_routing(self):
        agent, score = self._match("Нужна юридическая консультация по договору")
        assert agent == "lawyer_agent"
        assert score >= 1

    def test_accountant_routing(self):
        agent, score = self._match("Какую систему налогообложения выбрать?")
        assert agent == "accountant_agent"
        assert score >= 1

    def test_certifier_routing(self):
        agent, score = self._match("Сертификация Chery по ТР ТС")
        assert agent == "certifier"
        assert score >= 2

    def test_grants_routing(self):
        agent, score = self._match("Найди гранты РНФ")
        assert agent == "opportunity_scanner"
        assert score >= 1

    def test_freelance_routing(self):
        agent, score = self._match("Поиск заказов на Kwork")
        assert agent == "freelance_agent"
        assert score >= 1

    def test_namer_routing(self):
        agent, score = self._match("Придумай название для бренда")
        assert agent == "namer_agent"
        assert score >= 1

    def test_hackathon_routing(self):
        agent, score = self._match("Хакатон на DevPost")
        assert agent == "hackathon_manager"
        assert score >= 1

    def test_fallback_to_ceo(self):
        agent, score = self._match("Расскажи анекдот про кота")
        assert agent == "ceo_agent"
        assert score == 0

    def test_multi_keyword_higher_score(self):
        # "сертификация" + "ТР ТС" + "ЕАЭС" should give higher score
        _, score_specific = self._match("Сертификация по ТР ТС ЕАЭС для импорта")
        _, score_generic = self._match("Сертификация продукции")
        assert score_specific >= score_generic
