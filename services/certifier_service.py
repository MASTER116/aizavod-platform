"""CERTIFIER — AI-agent for EAEU vehicle certification consulting.

Uses BM25 search over local knowledge base + Groq LLM for answers.
Falls back to rule-based responses when Groq is unavailable.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

logger = logging.getLogger("aizavod.certifier")

# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 600  # tokens (approx chars for Russian text)
_CHUNK_OVERLAP = 100


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokeniser for Russian text."""
    return re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", text.lower())


def _split_into_chunks(text: str, source: str) -> list[dict[str, str]]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks: list[dict[str, str]] = []
    start = 0
    while start < len(words):
        end = start + _CHUNK_SIZE
        chunk_text = " ".join(words[start:end])
        chunks.append({"text": chunk_text, "source": source})
        start += _CHUNK_SIZE - _CHUNK_OVERLAP
    return chunks


# ---------------------------------------------------------------------------
# Rule-based fallback answers
# ---------------------------------------------------------------------------

_FALLBACK_RULES: list[tuple[list[str], str]] = [
    (
        ["оттс", "одобрение типа"],
        "ОТТС (Одобрение типа транспортного средства) — документ, подтверждающий "
        "соответствие серийного ТС требованиям ТР ТС 018/2011. Выдаётся аккредитованным "
        "органом по сертификации после проведения испытаний и аудита производства.",
    ),
    (
        ["сбктс", "единичн", "свидетельство о безопасности"],
        "СБКТС (Свидетельство о безопасности конструкции ТС) выдаётся на единичное ТС "
        "(конкретный VIN). Используется при ввозе единичного ТС, параллельном импорте, "
        "переоборудовании. Оформляется аккредитованной испытательной лабораторией.",
    ),
    (
        ["категори", "l1", "l2", "m1", "m2", "n1", "n2", "o1", "o2"],
        "Категории ТС по ТР ТС 018/2011: L — мототехника, M — пассажирские (M1 легковые, "
        "M2/M3 автобусы), N — грузовые (N1 до 3.5т, N2 до 12т, N3 свыше 12т), "
        "O — прицепы (O1-O4 по массе).",
    ),
    (
        ["эра", "глонасс"],
        "ЭРА-ГЛОНАСС обязательна для новых типов ТС категорий M1 и N1 с 1 января 2017 г. "
        "При ввозе б/у ТС также требуется установка ЭРА-ГЛОНАСС.",
    ),
    (
        ["стоимость", "цена", "сколько стоит"],
        "Стоимость ОТТС для легкового автомобиля (M1): от 2 до 15 млн руб. "
        "СБКТС для единичного ТС: от 15 000 до 150 000 руб. "
        "Сертификация компонента: от 100 000 до 1 000 000 руб.",
    ),
    (
        ["электромобил", "электро", "аккумулятор"],
        "Электромобили сертифицируются по ТР ТС 018/2011. Дополнительно проверяются: "
        "электробезопасность (Правила ООН № 100), безопасность АКБ (ГТП ООН № 20), "
        "система AVAS (звуковое оповещение пешеходов).",
    ),
    (
        ["eac", "маркировк"],
        "Знак EAC (Eurasian Conformity) наносится на ТС и компоненты, прошедшие оценку "
        "соответствия по техническим регламентам ЕАЭС. Без знака EAC продукция не может "
        "быть выпущена в обращение.",
    ),
    (
        ["переоборудован", "газ", "лифт"],
        "Переоборудование ТС регулируется Приложением 15 к ТР ТС 018/2011. Необходимо: "
        "заключение лаборатории, работы в сертифицированной мастерской, проверка, СБКТС, "
        "внесение изменений в ПТС через ГИБДД.",
    ),
]


def _fallback_answer(question: str) -> str:
    """Return a rule-based answer if Groq API is unavailable."""
    q_lower = question.lower()
    for keywords, answer in _FALLBACK_RULES:
        if any(kw in q_lower for kw in keywords):
            return answer
    return (
        "К сожалению, я не смог найти точный ответ на ваш вопрос. "
        "Рекомендую обратиться к полному тексту ТР ТС 018/2011 или "
        "в аккредитованный орган по сертификации (например, НАМИ)."
    )


# ---------------------------------------------------------------------------
# CertifierService
# ---------------------------------------------------------------------------


class CertifierService:
    """Knowledge-augmented certification consulting service."""

    def __init__(self, knowledge_dir: str | None = None) -> None:
        self._knowledge_dir = knowledge_dir or os.getenv(
            "CERTIFIER_KNOWLEDGE_DIR", "data/certifier"
        )
        self._chunks: list[dict[str, str]] = []
        self._bm25: BM25Okapi | None = None
        self._regulations: list[dict[str, str]] = []
        self._loaded = False

    # -- public interface ----------------------------------------------------

    def load_knowledge(self) -> None:
        """Load all *.txt files from knowledge directory and build BM25 index."""
        kb_path = Path(self._knowledge_dir)
        if not kb_path.exists():
            logger.warning("Knowledge dir %s does not exist", kb_path)
            return

        self._chunks = []
        self._regulations = []

        for txt_file in sorted(kb_path.glob("*.txt")):
            text = txt_file.read_text(encoding="utf-8")
            if not text.strip():
                continue

            source_name = txt_file.stem
            self._chunks.extend(_split_into_chunks(text, source_name))

            # Extract regulation title from first non-empty line
            first_line = ""
            for line in text.splitlines():
                line = line.strip()
                if line:
                    first_line = line
                    break
            self._regulations.append(
                {"file": txt_file.name, "title": first_line, "source": source_name}
            )

        if self._chunks:
            tokenized = [_tokenize(c["text"]) for c in self._chunks]
            self._bm25 = BM25Okapi(tokenized)
            logger.info(
                "Certifier KB loaded: %d chunks from %d files",
                len(self._chunks),
                len(self._regulations),
            )
        else:
            logger.warning("No knowledge chunks loaded")

        self._loaded = True

    def get_regulations(self) -> list[dict[str, str]]:
        """Return list of loaded regulations."""
        if not self._loaded:
            self.load_knowledge()
        return self._regulations

    async def query(self, question: str) -> dict[str, Any]:
        """Answer a certification question using BM25 + Groq LLM."""
        if not self._loaded:
            self.load_knowledge()

        # BM25 search
        top_chunks = self._search(question, top_k=5)
        context = "\n\n---\n\n".join(c["text"] for c in top_chunks)
        sources = list({c["source"] for c in top_chunks})

        # Try Groq LLM
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        if groq_api_key:
            try:
                answer = await self._ask_groq(question, context, groq_api_key)
                return {
                    "answer": answer,
                    "sources": sources,
                    "confidence": "high" if top_chunks else "low",
                    "model": os.getenv(
                        "CERTIFIER_MODEL", "llama-3.3-70b-versatile"
                    ),
                }
            except Exception as exc:
                logger.error("Groq API error: %s", exc)

        # Fallback
        answer = _fallback_answer(question)
        return {
            "answer": answer,
            "sources": sources,
            "confidence": "medium",
            "model": "rule-based-fallback",
        }

    # -- internals -----------------------------------------------------------

    def _search(self, query: str, top_k: int = 5) -> list[dict[str, str]]:
        """BM25 search over loaded chunks."""
        if not self._bm25 or not self._chunks:
            return []
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:top_k]
        return [self._chunks[idx] for idx, score in ranked if score > 0]

    @staticmethod
    async def _ask_groq(question: str, context: str, api_key: str) -> str:
        """Call Groq API with context-augmented prompt."""
        from groq import AsyncGroq

        model = os.getenv("CERTIFIER_MODEL", "llama-3.3-70b-versatile")

        system_prompt = (
            "Ты — эксперт-консультант по сертификации транспортных средств "
            "в рамках технических регламентов Таможенного союза (ЕАЭС). "
            "Отвечай на русском языке, точно и по существу. "
            "Используй только информацию из предоставленного контекста. "
            "Если информации недостаточно — честно скажи об этом.\n\n"
            "КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:\n"
            f"{context}"
        )

        client = AsyncGroq(api_key=api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: CertifierService | None = None


def get_certifier_service() -> CertifierService:
    """Get or create the singleton CertifierService instance."""
    global _service
    if _service is None:
        _service = CertifierService()
    return _service
