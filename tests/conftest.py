"""Shared fixtures для всех тестов Zavod-ii."""

import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_llm_responses():
    """Predefined LLM responses for deterministic testing."""
    return {
        "conductor_classify": '{"agent": "lawyer_agent", "confidence": 0.9, "reasoning": "legal question", "reformulated_query": "test", "multi_agent": false, "secondary_agents": []}',
        "conductor_ceo": '{"analysis": "test task", "directors": [{"role": "cto", "task": "implement feature", "priority": "high", "estimated_hours": 4, "deliverables": ["code"], "depends_on": []}]}',
        "conductor_dir": '{"tasks": [{"department": "backend", "task": "write API", "estimated_hours": 2, "deliverables": ["endpoint"], "depends_on": []}]}',
        "conductor_dept": '{"tasks": [{"specialist": "fastapi_dev", "task": "create route", "estimated_hours": 1, "deliverables": ["route.py"], "depends_on": []}]}',
        "conductor_collect": '{"summary": "Done", "status": "completed", "highlights": ["feature done"], "issues": [], "next_steps": []}',
        "conductor_thinking": '{"analysis": "deep analysis", "directors": []}',
        "agentic_rag": "Ответ на основе контекста из памяти.",
    }


@pytest.fixture
def mock_llm(monkeypatch, mock_llm_responses):
    """Mock LLM client — no API calls, deterministic responses."""
    async def fake_call(self, prompt, max_tokens=500, model=None, temperature=0.2,
                        caller="conductor", system_prompt=None, use_cache=True, use_thinking=False):
        for key, resp in mock_llm_responses.items():
            if key in caller:
                return resp
        return '{"response": "mock response"}'

    async def fake_thinking(self, prompt, system_prompt=None, max_tokens=2000, model=None, caller="thinking"):
        return mock_llm_responses.get("conductor_thinking", '{}')

    monkeypatch.setattr(
        "services.conductor.llm_client.LLMClient.call", fake_call
    )
    monkeypatch.setattr(
        "services.conductor.llm_client.LLMClient.call_with_thinking", fake_thinking
    )


@pytest.fixture
def golden_routing_tests():
    """Load golden routing test cases."""
    import yaml
    path = os.path.join(os.path.dirname(__file__), "golden", "routing_tests.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["tests"]


@pytest.fixture
def golden_compliance_tests():
    """Load golden compliance test cases."""
    import yaml
    path = os.path.join(os.path.dirname(__file__), "golden", "compliance_tests.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["tests"]
