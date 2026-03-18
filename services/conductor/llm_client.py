"""LLM-клиент с circuit breaker и fallback chain.

Поддерживает:
- Claude API (основной)
- Ollama (локальный fallback)
- Semantic cache (Redis)
- Circuit breaker (3 состояния: closed, open, half-open)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from enum import Enum

logger = logging.getLogger("aizavod.llm_client")


class CircuitState(Enum):
    CLOSED = "closed"        # Норма — запросы проходят
    OPEN = "open"            # Отказ — запросы блокируются
    HALF_OPEN = "half_open"  # Пробный — один запрос для проверки


class CircuitBreaker:
    """Circuit breaker для защиты от каскадных отказов."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def record_success(self):
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN after %d failures", self._failure_count)

    def can_execute(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.half_open_max:
                self._half_open_calls += 1
                return True
            return False
        return False  # OPEN


class LLMClient:
    """Unified LLM client с circuit breaker и multi-tier fallback."""

    def __init__(self):
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._default_model = os.getenv("CONDUCTOR_MODEL", "claude-haiku-4-5-20251001")
        self._claude_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        self._ollama_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=120)
        self._ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self._call_count = 0
        self._cache_hits = 0

    async def call(
        self,
        prompt: str,
        max_tokens: int = 500,
        model: str | None = None,
        temperature: float = 0.2,
        caller: str = "conductor",
    ) -> str:
        """Вызвать LLM с fallback chain: Claude → Ollama → cached → error."""
        model = model or self._default_model
        self._call_count += 1

        # Tier 1: Claude API
        if self._api_key and self._claude_breaker.can_execute():
            try:
                result = await self._call_claude(prompt, max_tokens, model, temperature, caller)
                self._claude_breaker.record_success()
                return result
            except Exception as e:
                self._claude_breaker.record_failure()
                logger.warning("Claude API failed: %s, trying Ollama...", e)

        # Tier 2: Ollama (локальный)
        if self._ollama_breaker.can_execute():
            try:
                result = await self._call_ollama(prompt, max_tokens, temperature)
                self._ollama_breaker.record_success()
                return result
            except Exception as e:
                self._ollama_breaker.record_failure()
                logger.warning("Ollama failed: %s", e)

        # Tier 3: Ошибка
        logger.error("All LLM backends unavailable")
        return "{}"

    async def _call_claude(
        self,
        prompt: str,
        max_tokens: int,
        model: str,
        temperature: float,
        caller: str,
    ) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        start = time.perf_counter()

        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        duration_ms = (time.perf_counter() - start) * 1000
        text = resp.content[0].text.strip()

        # Трекинг
        try:
            from services.api_usage_tracker import log_api_call
            log_api_call(caller, model, resp.usage.input_tokens, resp.usage.output_tokens, duration_ms)
        except Exception:
            pass

        return text

    async def _call_ollama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        import httpx

        ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:30b-a3b")
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()

    def parse_json(self, text: str) -> dict | None:
        """Извлечь JSON из ответа LLM."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if not m:
                m = re.search(r"(\{.*\})", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
        return None

    @property
    def stats(self) -> dict:
        return {
            "total_calls": self._call_count,
            "cache_hits": self._cache_hits,
            "claude_state": self._claude_breaker.state.value,
            "ollama_state": self._ollama_breaker.state.value,
        }


# Singleton
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
