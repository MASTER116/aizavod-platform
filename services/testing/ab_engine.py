"""A/B Testing Engine для промптов агентов.

Best practices 2026 (Braintrust + Langfuse):
- Minimum 30 samples per variant для statistical significance
- t-test для continuous metrics (quality scores)
- Multi-run: min 3 runs per test case (single-run flips rankings в 83% случаев)
- Shadow deployment → canary release → full rollout
- Auto-promote winner при p_value < 0.05
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("aizavod.ab_engine")


@dataclass
class PromptVariant:
    """Вариант промпта для A/B теста."""
    agent_name: str
    version: str          # "v1.0", "v1.1"
    prompt_text: str
    is_control: bool      # True = A (control), False = B (challenger)


@dataclass
class ABMetric:
    """Метрика одного вызова варианта."""
    quality_score: float    # QA-AGENT score 0-10
    latency_ms: float
    cost_usd: float
    success: bool           # True if no error
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ABExperiment:
    """A/B эксперимент для одного агента."""
    experiment_id: str
    agent_name: str
    variant_a: PromptVariant   # Control
    variant_b: PromptVariant   # Challenger
    traffic_split: float = 0.5  # 0.5 = 50/50
    status: str = "draft"       # draft / running / completed / promoted
    min_samples: int = 30       # Minimum per variant for significance
    created_at: datetime = field(default_factory=datetime.utcnow)
    results_a: list[ABMetric] = field(default_factory=list)
    results_b: list[ABMetric] = field(default_factory=list)


@dataclass
class ABEvaluation:
    """Результат статистической оценки эксперимента."""
    experiment_id: str
    winner: str | None        # "a", "b", or None (no significant difference)
    p_value: float
    confidence: float         # 1 - p_value
    significant: bool         # p_value < 0.05
    samples_a: int
    samples_b: int
    avg_quality_a: float
    avg_quality_b: float
    avg_latency_a: float
    avg_latency_b: float
    avg_cost_a: float
    avg_cost_b: float
    recommendation: str       # Human-readable recommendation


class ABEngine:
    """A/B Testing Engine для промптов всех агентов."""

    def __init__(self):
        self._experiments: dict[str, ABExperiment] = {}

    def create_experiment(
        self,
        agent_name: str,
        variant_a_prompt: str,
        variant_b_prompt: str,
        traffic_split: float = 0.5,
        min_samples: int = 30,
    ) -> str:
        """Создать новый A/B эксперимент."""
        exp_id = f"ab_{agent_name}_{int(time.time())}"

        experiment = ABExperiment(
            experiment_id=exp_id,
            agent_name=agent_name,
            variant_a=PromptVariant(
                agent_name=agent_name,
                version="control",
                prompt_text=variant_a_prompt,
                is_control=True,
            ),
            variant_b=PromptVariant(
                agent_name=agent_name,
                version="challenger",
                prompt_text=variant_b_prompt,
                is_control=False,
            ),
            traffic_split=traffic_split,
            min_samples=min_samples,
            status="running",
        )

        self._experiments[exp_id] = experiment
        logger.info("AB experiment created: %s for agent %s", exp_id, agent_name)
        return exp_id

    def get_variant(self, experiment_id: str, user_id: int | None = None) -> tuple[str, PromptVariant]:
        """Выбрать вариант для запроса. Deterministic per user_id.

        Returns: ("a" or "b", PromptVariant)
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != "running":
            # Default to control
            if exp:
                return "a", exp.variant_a
            raise ValueError(f"Experiment {experiment_id} not found")

        # Deterministic assignment per user (consistent experience)
        if user_id is not None:
            hash_val = int(hashlib.md5(f"{experiment_id}:{user_id}".encode()).hexdigest(), 16)
            use_b = (hash_val % 100) < (exp.traffic_split * 100)
        else:
            use_b = random.random() < exp.traffic_split

        if use_b:
            return "b", exp.variant_b
        return "a", exp.variant_a

    def record_result(
        self,
        experiment_id: str,
        variant: str,
        quality_score: float,
        latency_ms: float,
        cost_usd: float = 0.0,
        success: bool = True,
    ) -> None:
        """Записать результат вызова варианта."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return

        metric = ABMetric(
            quality_score=quality_score,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
        )

        if variant == "a":
            exp.results_a.append(metric)
        else:
            exp.results_b.append(metric)

        # Auto-evaluate when enough samples
        total = len(exp.results_a) + len(exp.results_b)
        if total > 0 and total % 10 == 0:  # Check every 10 samples
            eval_result = self.evaluate(experiment_id)
            if eval_result.significant:
                logger.info(
                    "AB %s: significant result! Winner=%s (p=%.4f, quality: %.1f vs %.1f)",
                    experiment_id, eval_result.winner, eval_result.p_value,
                    eval_result.avg_quality_a, eval_result.avg_quality_b,
                )

    def evaluate(self, experiment_id: str) -> ABEvaluation:
        """Статистическая оценка эксперимента (Welch's t-test)."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found")

        scores_a = [m.quality_score for m in exp.results_a]
        scores_b = [m.quality_score for m in exp.results_b]
        n_a = len(scores_a)
        n_b = len(scores_b)

        # Means
        avg_q_a = sum(scores_a) / max(n_a, 1)
        avg_q_b = sum(scores_b) / max(n_b, 1)
        avg_lat_a = sum(m.latency_ms for m in exp.results_a) / max(n_a, 1)
        avg_lat_b = sum(m.latency_ms for m in exp.results_b) / max(n_b, 1)
        avg_cost_a = sum(m.cost_usd for m in exp.results_a) / max(n_a, 1)
        avg_cost_b = sum(m.cost_usd for m in exp.results_b) / max(n_b, 1)

        # Welch's t-test (doesn't assume equal variances)
        p_value = 1.0
        if n_a >= 2 and n_b >= 2:
            var_a = sum((x - avg_q_a) ** 2 for x in scores_a) / (n_a - 1)
            var_b = sum((x - avg_q_b) ** 2 for x in scores_b) / (n_b - 1)

            se = math.sqrt(var_a / n_a + var_b / n_b) if (var_a / n_a + var_b / n_b) > 0 else 1e-10
            t_stat = (avg_q_a - avg_q_b) / se

            # Approximate p-value using normal distribution (for large samples)
            # For small samples this is an approximation
            z = abs(t_stat)
            p_value = 2 * (1 - self._normal_cdf(z))

        significant = p_value < 0.05 and min(n_a, n_b) >= exp.min_samples

        # Determine winner
        winner = None
        if significant:
            winner = "a" if avg_q_a > avg_q_b else "b"

        # Recommendation
        if not significant and min(n_a, n_b) < exp.min_samples:
            recommendation = f"Недостаточно данных: {n_a}+{n_b} samples (нужно {exp.min_samples}+ на вариант)"
        elif not significant:
            recommendation = f"Нет значимой разницы (p={p_value:.3f}). Оставить control."
        elif winner == "a":
            recommendation = f"Control лучше (quality: {avg_q_a:.1f} vs {avg_q_b:.1f}, p={p_value:.4f}). Оставить текущий промпт."
        else:
            recommendation = f"Challenger лучше (quality: {avg_q_b:.1f} vs {avg_q_a:.1f}, p={p_value:.4f}). Промоутить вариант B."

        return ABEvaluation(
            experiment_id=experiment_id,
            winner=winner,
            p_value=p_value,
            confidence=1 - p_value,
            significant=significant,
            samples_a=n_a,
            samples_b=n_b,
            avg_quality_a=avg_q_a,
            avg_quality_b=avg_q_b,
            avg_latency_a=avg_lat_a,
            avg_latency_b=avg_lat_b,
            avg_cost_a=avg_cost_a,
            avg_cost_b=avg_cost_b,
            recommendation=recommendation,
        )

    def promote_winner(self, experiment_id: str) -> dict:
        """Промоутить winner как default prompt."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "Experiment not found"}

        evaluation = self.evaluate(experiment_id)
        if not evaluation.significant:
            return {"error": "No significant winner yet", "evaluation": evaluation.recommendation}

        exp.status = "promoted"
        logger.info("AB %s: promoted variant %s as winner", experiment_id, evaluation.winner)

        return {
            "promoted": evaluation.winner,
            "quality_improvement": evaluation.avg_quality_b - evaluation.avg_quality_a if evaluation.winner == "b" else 0,
            "recommendation": evaluation.recommendation,
        }

    def get_active_experiment(self, agent_name: str) -> ABExperiment | None:
        """Найти активный эксперимент для агента."""
        for exp in self._experiments.values():
            if exp.agent_name == agent_name and exp.status == "running":
                return exp
        return None

    def list_experiments(self) -> list[dict]:
        """Список всех экспериментов."""
        results = []
        for exp in self._experiments.values():
            eval_result = self.evaluate(exp.experiment_id) if (exp.results_a or exp.results_b) else None
            results.append({
                "id": exp.experiment_id,
                "agent": exp.agent_name,
                "status": exp.status,
                "samples": f"{len(exp.results_a)}+{len(exp.results_b)}",
                "winner": eval_result.winner if eval_result else None,
                "p_value": f"{eval_result.p_value:.4f}" if eval_result else None,
                "recommendation": eval_result.recommendation if eval_result else "No data",
            })
        return results

    @staticmethod
    def _normal_cdf(z: float) -> float:
        """Approximate standard normal CDF (Abramowitz & Stegun)."""
        if z < 0:
            return 1 - ABEngine._normal_cdf(-z)
        t = 1 / (1 + 0.2316419 * z)
        d = 0.3989422804014327  # 1/sqrt(2*pi)
        p = d * math.exp(-z * z / 2) * (
            t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
        )
        return 1 - p


# Singleton
_ab_engine: ABEngine | None = None


def get_ab_engine() -> ABEngine:
    global _ab_engine
    if _ab_engine is None:
        _ab_engine = ABEngine()
    return _ab_engine
