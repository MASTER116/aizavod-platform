"""AI-менеджер отзывов — парсинг и AI-ответы на отзывы Яндекс Карт / 2ГИС.

MVP для кэшфлоу-продукта: 990 руб./мес. за точку.
"""
from __future__ import annotations

import logging
import re
import json
from dataclasses import dataclass, field

from services.base_agent import BaseAgent

logger = logging.getLogger("aizavod.review_manager")


@dataclass
class Review:
    """Отзыв с площадки."""
    source: str  # "yandex" | "2gis"
    author: str
    rating: int  # 1-5
    text: str
    date: str
    review_id: str = ""
    response: str = ""  # Существующий ответ владельца
    ai_response: str = ""  # Сгенерированный AI-ответ


class ReviewManagerAgent(BaseAgent):
    """Агент для управления отзывами бизнеса."""

    agent_name = "review_manager"
    model_env_var = "REVIEW_MANAGER_MODEL"
    default_temperature = 0.3
    default_max_tokens = 1500

    system_prompt = (
        "Ты — профессиональный менеджер по работе с отзывами для малого бизнеса в России. "
        "Твоя задача — генерировать тёплые, профессиональные ответы на отзывы клиентов "
        "на Яндекс Картах и 2ГИС.\n\n"
        "ПРАВИЛА:\n"
        "- Ответ 2-4 предложения, без воды\n"
        "- Благодарить за отзыв (положительный) или извиниться (отрицательный)\n"
        "- Упоминать конкретные детали из отзыва\n"
        "- На негатив: извинение + конкретное решение + приглашение вернуться\n"
        "- На позитив: благодарность + подчеркнуть сильную сторону\n"
        "- Тон: дружелюбный, но профессиональный\n"
        "- НЕ использовать шаблонные фразы вроде 'Спасибо за обратную связь'\n"
        "- Обращаться по имени если указано\n"
        "- Для рейтинга 1-2: приоритет на решение проблемы\n"
        "- Для рейтинга 3: признать замечания + показать улучшения\n"
        "- Для рейтинга 4-5: благодарность + мотивация вернуться"
    )

    BREVITY_RULE = ""  # Отключаем стандартное правило краткости

    async def generate_response(self, review: Review) -> str:
        """Сгенерировать AI-ответ на один отзыв."""
        tone = "извинительный" if review.rating <= 2 else "благодарный" if review.rating >= 4 else "нейтрально-позитивный"
        prompt = (
            f"Площадка: {review.source}\n"
            f"Автор: {review.author}\n"
            f"Рейтинг: {'⭐' * review.rating} ({review.rating}/5)\n"
            f"Отзыв: {review.text}\n"
            f"Дата: {review.date}\n\n"
            f"Сгенерируй {tone} ответ от лица владельца бизнеса. "
            f"Только текст ответа, без пояснений."
        )
        return await self._call_llm(prompt, max_tokens=500)

    async def generate_batch_responses(self, reviews: list[Review]) -> list[Review]:
        """Сгенерировать ответы на пачку отзывов."""
        results = []
        for review in reviews:
            if not review.response:  # Только без ответа
                review.ai_response = await self.generate_response(review)
            results.append(review)
        return results

    async def analyze_sentiment(self, reviews: list[Review]) -> dict:
        """Анализ тональности и ключевых тем из отзывов."""
        if not reviews:
            return {"error": "Нет отзывов для анализа"}

        reviews_text = "\n---\n".join(
            f"⭐{r.rating} | {r.author}: {r.text[:300]}" for r in reviews[:20]
        )
        prompt = (
            f"Проанализируй {len(reviews)} отзывов бизнеса:\n\n"
            f"{reviews_text}\n\n"
            "Верни JSON:\n"
            '{"avg_rating": число, "positive_themes": ["тема1","тема2"], '
            '"negative_themes": ["тема1","тема2"], '
            '"urgent_count": число_негативных_без_ответа, '
            '"summary": "краткий вывод 1-2 предложения"}'
        )
        result = await self._call_llm(prompt, max_tokens=800)
        try:
            # Извлечь JSON из ответа
            json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        return {"summary": result, "avg_rating": 0}

    async def process_query(self, query: str) -> str:
        """Обработать произвольный запрос по отзывам."""
        prompt = (
            f"Запрос пользователя по управлению отзывами бизнеса:\n{query}\n\n"
            "Помоги с этим запросом. Если нужны конкретные отзывы — попроси "
            "пользователя отправить ссылку на бизнес или список отзывов."
        )
        return await self._call_llm(prompt, max_tokens=1000)


# Singleton
_agent: ReviewManagerAgent | None = None


def get_review_manager_agent() -> ReviewManagerAgent:
    global _agent
    if _agent is None:
        _agent = ReviewManagerAgent()
    return _agent
