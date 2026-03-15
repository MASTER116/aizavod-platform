"""LawyerAgent — юридические консультации для бизнеса в России."""
from __future__ import annotations

import logging

from services.base_agent import BaseAgent

logger = logging.getLogger("aizavod.lawyer_agent")


class LawyerAgent(BaseAgent):
    agent_name = "lawyer"
    model_env_var = "LAWYER_MODEL"
    default_temperature = 0.3
    default_max_tokens = 2500

    system_prompt = (
        "Ты — опытный юрист-консультант по российскому праву, "
        "специализирующийся на предпринимательском праве. "
        "Консультируешь ИП и ООО. Отвечай структурированно, "
        "ссылайся на конкретные статьи законов и нормативные акты. "
        "Предупреждай, что консультация информационная и не заменяет "
        "профессиональную юридическую помощь."
    )

    async def consult(self, question: str) -> str:
        """Общая юридическая консультация."""
        prompt = f"""Вопрос клиента: {question}

Ответь как юрист-консультант:
1. Краткий ответ (2-3 предложения)
2. Правовая основа (законы, статьи, НПА)
3. Порядок действий (пошагово)
4. Риски и на что обратить внимание
5. Когда обязательно нужен юрист (оффлайн)"""
        return await self._call_llm(prompt)

    async def check_contract(self, description: str) -> str:
        """Анализ рисков договора."""
        prompt = f"""Проанализируй описание договора и выяви риски.

ОПИСАНИЕ ДОГОВОРА:
{description}

Структура ответа:
## Тип договора
## Ключевые условия (которые должны быть)
## Потенциальные риски
## Рекомендации по защите интересов
## Обязательные пункты для включения"""
        return await self._call_llm(prompt, max_tokens=3000)

    async def ip_registration(self, activity: str) -> str:
        """Пошаговая регистрация ИП."""
        prompt = f"""Клиент хочет зарегистрировать ИП.

Вид деятельности: {activity}

Дай пошаговую инструкцию:
1. Выбор ОКВЭД (предложи конкретные коды для этой деятельности)
2. Выбор системы налогообложения (УСН 6%, УСН 15%, патент — что лучше)
3. Документы для регистрации
4. Порядок подачи (Госуслуги, ФНС, МФЦ)
5. Что сделать ПОСЛЕ регистрации (банк, печать, отчетность)
6. Стоимость и сроки"""
        return await self._call_llm(prompt, max_tokens=3000)

    async def labor_law(self, question: str) -> str:
        """Трудовое право (ТК РФ)."""
        prompt = f"""Вопрос по трудовому праву: {question}

Ответь с учетом ТК РФ:
1. Правовая позиция
2. Права и обязанности сторон
3. Сроки и процедуры
4. Штрафы за нарушения
5. Рекомендации"""
        return await self._call_llm(prompt)


_agent: LawyerAgent | None = None


def get_lawyer_agent() -> LawyerAgent:
    global _agent
    if _agent is None:
        _agent = LawyerAgent()
    return _agent
