"""ORACLE Agent — предиктивный AI-агент для Zavod-ii.

Обёртка OraclePredictor под паттерн BaseAgent.
Для файловых запросов: загрузи CSV/Excel через /api/oracle/predict.
Для текстовых запросов: объясняет возможности ORACLE через LLM.
"""
from __future__ import annotations

import logging

from services.base_agent import BaseAgent

logger = logging.getLogger("aizavod.oracle_agent")

ORACLE_SYSTEM_PROMPT = """Ты — ORACLE, предиктивный AI-агент платформы Zavod-ii.

Ты умеешь:
1. Классификация (отток клиентов, скоринг лидов, фрод) → GradientBoosting, LogisticRegression
2. Регрессия (прогноз выручки, спроса, цен) → GradientBoosting, Ridge
3. Временной ряд (прогноз продаж, загрузки, трафика) → Trend + FFT
4. Детекция аномалий (фрод, выбросы, сбои) → IsolationForest + Z-score
5. Survival analysis (отказы оборудования, TTF) → Weibull

Пользователь спрашивает о прогнозах и ML. Объясни, что ORACLE может сделать.
Если нужен анализ файла — направь на /api/oracle/predict (POST, загрузить CSV/Excel).
"""


class OracleAgent(BaseAgent):
    agent_name = "oracle"
    default_model = "claude-haiku-4-5-20251001"
    system_prompt = ORACLE_SYSTEM_PROMPT
    default_max_tokens = 1000

    def __init__(self) -> None:
        super().__init__()
        self._predictor = None

    def _get_predictor(self):
        if self._predictor is None:
            from services.oracle_predictor.predictor import OraclePredictor
            self._predictor = OraclePredictor()
        return self._predictor

    async def process(self, query: str) -> str:
        """Обработка текстового запроса через LLM."""
        prompt = f"""Пользователь спрашивает:
{query}

Объясни, как ORACLE может помочь. Если нужен анализ данных — скажи загрузить CSV/Excel через API:
POST /api/oracle/predict с параметрами file, target_col, force_type, forecast_periods.

Типы задач: classification, regression, timeseries, anomaly_detection, survival.
Автоопределение типа по данным или принудительный выбор через force_type."""

        return await self._call_llm(prompt)

    def predict_sync(self, df, target_col=None, force_type=None, forecast_periods=30):
        """Синхронный вызов OraclePredictor для API-роутов."""
        predictor = self._get_predictor()
        return predictor.predict(df, target_col, force_type, forecast_periods)


_oracle: OracleAgent | None = None


def get_oracle_agent() -> OracleAgent:
    global _oracle
    if _oracle is None:
        _oracle = OracleAgent()
    return _oracle
