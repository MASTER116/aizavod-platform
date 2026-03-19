"""Agentic RAG — замена "тупого" RAG на планирующий retrieval.

Standard RAG is Dead (Q1 2026):
- Semantic mismatches: запрос не match'ится с индексацией документа
- Static retrieval: один запрос → один результат, нет re-planning
- No validation: retrieved chunks не проверяются на релевантность

Agentic RAG pattern:
  Plan → Retrieve → Validate → Re-plan if needed → Generate

Используется Letta-pattern memory для хранения и retrieval.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("aizavod.agentic_rag")


class AgenticRAG:
    """Plan-Retrieve-Validate-Replan-Generate RAG."""

    def __init__(self, max_retries: int = 2):
        self._max_retries = max_retries

    async def query(
        self,
        question: str,
        user_id: int | None = None,
        agent_name: str = "conductor",
    ) -> dict:
        """Полный Agentic RAG pipeline.

        Returns:
            {"answer": str, "sources": list, "retries": int, "plan": str}
        """
        retries = 0

        # Step 1: PLAN — определить что искать
        plan = await self._plan(question)

        while retries <= self._max_retries:
            # Step 2: RETRIEVE — получить данные из памяти
            chunks = await self._retrieve(plan, user_id)

            # Step 3: VALIDATE — проверить релевантность
            valid_chunks = await self._validate(question, chunks)

            if valid_chunks:
                # Step 4: GENERATE — сгенерировать ответ
                answer = await self._generate(question, valid_chunks)
                return {
                    "answer": answer,
                    "sources": [c.get("source", "memory") for c in valid_chunks],
                    "retries": retries,
                    "plan": plan,
                }

            # Step 5: RE-PLAN — переформулировать поиск
            retries += 1
            if retries <= self._max_retries:
                plan = await self._replan(question, plan, retries)
                logger.info("AgenticRAG: re-planning (attempt %d): %s", retries, plan[:100])

        # Fallback: ответить без контекста
        return {
            "answer": f"Не нашёл релевантного контекста после {retries} попыток. Отвечаю на основе общих знаний.",
            "sources": [],
            "retries": retries,
            "plan": plan,
        }

    async def _plan(self, question: str) -> str:
        """Спланировать стратегию поиска."""
        # Извлечь ключевые сущности и определить тип запроса
        q_lower = question.lower()

        # Простая эвристика для planning (без LLM для скорости)
        if any(kw in q_lower for kw in ["грант", "конкурс", "рнф", "фси"]):
            return "search:grants+competitions, filter:active, sort:deadline"
        elif any(kw in q_lower for kw in ["сертифик", "тр тс", "еаэс"]):
            return "search:certification+regulations, filter:current, source:knowledge_base"
        elif any(kw in q_lower for kw in ["налог", "усн", "бухгалтер"]):
            return "search:tax+accounting, filter:2026, source:law_updates"
        elif any(kw in q_lower for kw in ["договор", "юрист", "закон"]):
            return "search:legal+contracts, source:templates+law"
        elif any(kw in q_lower for kw in ["фриланс", "заказ", "kwork"]):
            return "search:freelance+orders, filter:active, sort:budget_desc"
        else:
            # Общий поиск по памяти
            keywords = [w for w in q_lower.split() if len(w) > 3][:5]
            return f"search:general, keywords:{','.join(keywords)}"

    async def _retrieve(self, plan: str, user_id: int | None = None) -> list[dict]:
        """Получить данные из памяти (Letta-pattern)."""
        chunks = []

        try:
            from services.conductor.memory import get_agent_memory
            memory = get_agent_memory()

            if user_id:
                # Recall memory: прошлые взаимодействия
                query_part = plan.split("keywords:")[-1] if "keywords:" in plan else plan
                recall = await memory.recall.search(user_id, query_part, limit=5)
                for r in recall:
                    chunks.append({
                        "text": f"Q: {r.get('query', '')}\nA: {r.get('response', '')}",
                        "source": "recall_memory",
                        "relevance": r.get("relevance", 0),
                    })

                # Archival memory: verified facts
                facts = await memory.archival.search(user_id, query_part, limit=5)
                for f in facts:
                    chunks.append({
                        "text": f"[{f.get('type', 'fact')}] {f.get('value', '')}",
                        "source": "archival_memory",
                        "relevance": 1.0,
                        "trust": f.get("trust_score", 0.5),
                    })
        except Exception as e:
            logger.debug("AgenticRAG retrieve from memory failed: %s", e)

        return chunks

    async def _validate(self, question: str, chunks: list[dict]) -> list[dict]:
        """Проверить релевантность retrieved chunks."""
        if not chunks:
            return []

        # Простая фильтрация по минимальной релевантности
        valid = [c for c in chunks if c.get("relevance", 0) > 0]

        # Фильтр по trust score для archival
        valid = [c for c in valid if c.get("trust", 1.0) >= 0.3]

        return valid[:5]  # Max 5 chunks

    async def _generate(self, question: str, chunks: list[dict]) -> str:
        """Сгенерировать ответ на основе validated chunks."""
        context = "\n\n".join(c.get("text", "") for c in chunks)

        try:
            from services.conductor.llm_client import get_llm_client
            llm = get_llm_client()
            prompt = f"""На основе следующего контекста ответь на вопрос.

КОНТЕКСТ:
{context[:3000]}

ВОПРОС:
{question}

Ответь кратко и точно. Если контекст не содержит нужной информации — скажи об этом."""

            return await llm.call(prompt, max_tokens=1000, caller="agentic_rag")
        except Exception as e:
            logger.error("AgenticRAG generate failed: %s", e)
            return f"Ошибка генерации ответа: {e}"

    async def _replan(self, question: str, prev_plan: str, attempt: int) -> str:
        """Переформулировать стратегию поиска после неудачи."""
        # Расширить поиск: добавить синонимы, убрать фильтры
        if "filter:" in prev_plan:
            return prev_plan.replace("filter:", "expanded_filter:")
        return f"search:broad, keywords:{question[:50]}, attempt:{attempt}"


# Singleton
_rag: AgenticRAG | None = None


def get_agentic_rag() -> AgenticRAG:
    global _rag
    if _rag is None:
        _rag = AgenticRAG()
    return _rag
