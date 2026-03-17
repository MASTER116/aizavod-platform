"""Трекер использования Anthropic API.

Логирует каждый вызов: агент, модель, токены, стоимость, время.
Используется в BaseAgent._call_llm() и Conductor._classify()/_call_claude().
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger("aizavod.api_tracker")

# Цены Anthropic API (USD за 1M токенов) — актуальные на март 2026
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6-20260520": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6-20260618": {"input": 15.00, "output": 75.00},
}

# Дефолт для неизвестных моделей
DEFAULT_PRICING = {"input": 3.00, "output": 15.00}


def calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Рассчитать стоимость запроса в USD."""
    prices = PRICING.get(model, DEFAULT_PRICING)
    cost = (input_tokens / 1_000_000) * prices["input"] + (output_tokens / 1_000_000) * prices["output"]
    return round(cost, 6)


def log_api_call(
    agent_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: float,
    status: str = "ok",
    error: str | None = None,
) -> None:
    """Сохранить запись о вызове API в БД (fire-and-forget)."""
    try:
        from backend.database import SessionLocal
        from backend.models import ApiUsageLog

        cost = calc_cost(model, input_tokens, output_tokens)

        db = SessionLocal()
        try:
            db.add(ApiUsageLog(
                agent_name=agent_name,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                duration_ms=duration_ms,
                status=status,
                error=error,
            ))
            db.commit()
        finally:
            db.close()

        logger.debug(
            "API: %s | %s | in=%d out=%d | $%.4f | %dms",
            agent_name, model, input_tokens, output_tokens, cost, duration_ms,
        )
    except Exception as e:
        # Не ломаем основную логику если трекинг упал
        logger.warning("Не удалось залогировать API вызов: %s", e)
