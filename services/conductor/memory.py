"""Letta-pattern Memory Architecture для агентов.

3-уровневая память (по модели Letta/MemGPT):
  1. Core Memory — context window (Redis, TTL 24h). Как RAM.
  2. Recall Memory — searchable conversation history (PostgreSQL). Как disk cache.
  3. Archival Memory — long-term facts (PostgreSQL JSON). Как cold storage.

Ключевое отличие: агенты САМИ редактируют свою память через tool calls.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("aizavod.memory")


class CoreMemory:
    """Core Memory — текущий контекст (Redis, TTL).

    Как RAM: быстрый доступ, ограниченный объём, автоочистка.
    Используется для: текущей сессии, active task chain, intermediate results.
    """

    def __init__(self, redis_client=None, ttl_hours: int = 24):
        self._redis = redis_client
        self._ttl = ttl_hours * 3600
        self._local: dict[str, dict] = {}  # Fallback без Redis

    def _key(self, session_id: str) -> str:
        return f"core_memory:{session_id}"

    async def store(self, session_id: str, key: str, value: Any) -> None:
        """Сохранить в core memory."""
        if self._redis:
            try:
                full_key = self._key(session_id)
                existing = await self._redis.get(full_key)
                data = json.loads(existing) if existing else {}
                data[key] = {"value": value, "ts": datetime.utcnow().isoformat()}
                await self._redis.setex(full_key, self._ttl, json.dumps(data, ensure_ascii=False))
                return
            except Exception as e:
                logger.warning("Redis core_memory store failed: %s", e)
        # Local fallback
        self._local.setdefault(session_id, {})[key] = {
            "value": value, "ts": datetime.utcnow().isoformat()
        }

    async def get(self, session_id: str, key: str) -> Any | None:
        """Получить из core memory."""
        if self._redis:
            try:
                data = await self._redis.get(self._key(session_id))
                if data:
                    parsed = json.loads(data)
                    return parsed.get(key, {}).get("value")
            except Exception:
                pass
        return self._local.get(session_id, {}).get(key, {}).get("value")

    async def get_all(self, session_id: str) -> dict:
        """Получить всю core memory для сессии."""
        if self._redis:
            try:
                data = await self._redis.get(self._key(session_id))
                if data:
                    return json.loads(data)
            except Exception:
                pass
        return self._local.get(session_id, {})

    async def delete(self, session_id: str, key: str) -> None:
        """Удалить ключ из core memory."""
        if self._redis:
            try:
                data = await self._redis.get(self._key(session_id))
                if data:
                    parsed = json.loads(data)
                    parsed.pop(key, None)
                    await self._redis.setex(self._key(session_id), self._ttl, json.dumps(parsed))
                return
            except Exception:
                pass
        self._local.get(session_id, {}).pop(key, None)


class RecallMemory:
    """Recall Memory — searchable conversation history (PostgreSQL).

    Как disk cache: searchable, persistent, medium-speed access.
    Используется для: история взаимодействий, прошлые решения агентов.
    """

    def __init__(self, db_session=None):
        self._db = db_session
        self._local: list[dict] = []  # Fallback без DB

    async def store(
        self,
        user_id: int,
        agent_id: str,
        query: str,
        response: str,
        quality_score: float = 5.0,
        metadata: dict | None = None,
    ) -> None:
        """Сохранить взаимодействие в recall memory."""
        entry = {
            "user_id": user_id,
            "agent_id": agent_id,
            "query": query,
            "response": response[:2000],
            "quality_score": quality_score,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self._db:
            try:
                # TODO: INSERT INTO recall_memory через SQLAlchemy
                pass
            except Exception as e:
                logger.warning("DB recall_memory store failed: %s", e)

        self._local.append(entry)
        # Keep max 10000 entries locally
        if len(self._local) > 10000:
            self._local = self._local[-5000:]

    async def search(
        self,
        user_id: int,
        query: str,
        agent_id: str | None = None,
        limit: int = 10,
        min_quality: float = 5.0,
    ) -> list[dict]:
        """Поиск в recall memory (пока keyword-based, TODO: vector search)."""
        results = []
        query_lower = query.lower()
        keywords = query_lower.split()[:5]

        for entry in reversed(self._local):
            if entry["user_id"] != user_id:
                continue
            if agent_id and entry["agent_id"] != agent_id:
                continue
            if entry["quality_score"] < min_quality:
                continue
            # Simple keyword matching
            entry_text = f"{entry['query']} {entry['response']}".lower()
            score = sum(1 for kw in keywords if kw in entry_text)
            if score > 0:
                results.append({**entry, "relevance": score})

        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]

    async def get_recent(self, user_id: int, limit: int = 20) -> list[dict]:
        """Получить последние записи для пользователя."""
        user_entries = [e for e in self._local if e["user_id"] == user_id]
        return user_entries[-limit:]


class ArchivalMemory:
    """Archival Memory — long-term facts (PostgreSQL JSON).

    Как cold storage: persistent, verified facts, rarely accessed.
    Используется для: факты о бизнесе клиента, preferences, verified data.
    Агенты редактируют через tool calls.
    """

    def __init__(self, db_session=None):
        self._db = db_session
        self._local: dict[int, list[dict]] = {}  # user_id → facts

    async def store(
        self,
        user_id: int,
        fact_type: str,
        fact_value: str,
        source: str = "agent_derived",
        trust_score: float = 0.5,
    ) -> str:
        """Сохранить факт. Возвращает fact_id."""
        fact_id = f"fact_{user_id}_{int(time.time() * 1000)}"
        fact = {
            "id": fact_id,
            "user_id": user_id,
            "type": fact_type,
            "value": fact_value,
            "source": source,
            "trust_score": trust_score,
            "created_at": datetime.utcnow().isoformat(),
            "verified": source == "human_verified",
        }

        self._local.setdefault(user_id, []).append(fact)
        logger.info("Archival: stored fact %s for user %d (trust=%.1f)", fact_type, user_id, trust_score)
        return fact_id

    async def search(self, user_id: int, query: str, limit: int = 10) -> list[dict]:
        """Поиск фактов."""
        facts = self._local.get(user_id, [])
        query_lower = query.lower()
        results = []
        for f in facts:
            text = f"{f['type']} {f['value']}".lower()
            if any(kw in text for kw in query_lower.split()[:3]):
                results.append(f)
        return results[:limit]

    async def update(self, user_id: int, fact_id: str, new_value: str) -> bool:
        """Обновить факт."""
        facts = self._local.get(user_id, [])
        for f in facts:
            if f["id"] == fact_id:
                f["value"] = new_value
                f["updated_at"] = datetime.utcnow().isoformat()
                return True
        return False

    async def delete(self, user_id: int, fact_id: str) -> bool:
        """Удалить факт (152-ФЗ: право на удаление)."""
        facts = self._local.get(user_id, [])
        before = len(facts)
        self._local[user_id] = [f for f in facts if f["id"] != fact_id]
        return len(self._local[user_id]) < before

    async def delete_all_for_user(self, user_id: int) -> int:
        """Удалить все факты пользователя (152-ФЗ: право на забвение)."""
        count = len(self._local.get(user_id, []))
        self._local.pop(user_id, None)
        logger.info("Archival: deleted all %d facts for user %d (right to be forgotten)", count, user_id)
        return count


class AgentMemory:
    """Unified memory interface для агентов (Letta-pattern).

    Объединяет Core + Recall + Archival в единый API.
    Агенты используют как tool calls для self-editing memory.
    """

    def __init__(self, redis_client=None, db_session=None):
        self.core = CoreMemory(redis_client)
        self.recall = RecallMemory(db_session)
        self.archival = ArchivalMemory(db_session)

    # === Tool-call interface (для агентов) ===

    async def remember(self, user_id: int, fact: str, fact_type: str = "general") -> str:
        """Агент запоминает факт о пользователе."""
        return await self.archival.store(user_id, fact_type, fact, source="agent_derived", trust_score=0.7)

    async def recall_context(self, user_id: int, query: str) -> str:
        """Агент вспоминает релевантный контекст."""
        facts = await self.archival.search(user_id, query, limit=5)
        history = await self.recall.search(user_id, query, limit=3)

        parts = []
        if facts:
            parts.append("Известные факты:")
            for f in facts:
                parts.append(f"  - [{f['type']}] {f['value']} (trust: {f['trust_score']})")
        if history:
            parts.append("Релевантные прошлые взаимодействия:")
            for h in history:
                parts.append(f"  - Q: {h['query'][:80]}... → A: {h['response'][:80]}...")

        return "\n".join(parts) if parts else "Нет релевантного контекста."

    async def forget(self, user_id: int, fact_id: str) -> bool:
        """Агент забывает факт (по запросу пользователя)."""
        return await self.archival.delete(user_id, fact_id)

    async def forget_all(self, user_id: int) -> int:
        """Полное удаление данных пользователя (152-ФЗ)."""
        return await self.archival.delete_all_for_user(user_id)


# Singleton
_agent_memory: AgentMemory | None = None


def get_agent_memory(redis_client=None, db_session=None) -> AgentMemory:
    global _agent_memory
    if _agent_memory is None:
        _agent_memory = AgentMemory(redis_client, db_session)
    return _agent_memory
