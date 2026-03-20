"""Project Context Provider — контекст проекта для CEO-декомпозиции.

CEO получает полную картину: что уже построено, какие ресурсы,
какие ограничения. Это предотвращает:
- Создание уже существующих сервисов
- Нереалистичные планы (10 человек, когда есть 1)
- Абстрактные задачи без привязки к реальности
"""

from __future__ import annotations


# ─── Контекст платформы ──────────────────────────────────────────────────────

PLATFORM_CONTEXT = {
    "stack": "FastAPI + SQLAlchemy 2.x + Pydantic v2, PostgreSQL 16, Redis 7, Docker Compose",
    "llm": "Claude Haiku 4.5 (prompt caching, extended thinking) + Ollama/Qwen3 fallback",
    "bot_framework": "aiogram 3 + FSM (@zavod_ii_bot)",
    "server": "VPS (Docker Compose, 9 контейнеров, nginx reverse proxy)",
    "ci_cd": "GitHub Actions → SSH deploy → docker compose build/up",
    "tasks": "Celery + APScheduler (фоновые задачи, автономность)",
}

# ─── Существующие агенты (не создавать заново!) ──────────────────────────────

EXISTING_AGENTS = [
    "certifier — сертификация ТС ЕАЭС (RAG + Claude API), 291 ОКВЭД",
    "opportunity_scanner — гранты, хакатоны, конкурсы (ФАСИ, РНФ, Сколково, DevPost)",
    "idea_generator — генерация идей заработка и монетизации",
    "market_analyzer — анализ рынка, конкурентов, заявок",
    "freelance_agent — поиск заказов на Kwork/Upwork, отклики",
    "pricing_agent — оценка проектов, генерация КП",
    "outreach_agent — холодные продажи, генерация писем",
    "content_factory — контент для Instagram, TikTok, VK",
    "lawyer_agent — договоры, регистрация ИП/ООО, право",
    "accountant_agent — налоги, отчётность, УСН/ОСН",
    "darwin_agent — self-learning, оценка качества, weekly reports",
    "guardian_agent — антифрод, injection detection, безопасность",
    "guardian_ip_agent — товарные знаки, патенты, IP-аудит",
    "scholar_agent — грантовые заявки, научные статьи, ГОСТ/ВАК",
    "herald_agent — open-source, Хабр, Product Hunt",
    "namer_agent — нейминг, домены, товарные знаки",
    "voice_agent — скрипты звонков, TTS-оптимизация",
    "treasurer_agent — монетизация, расходы, cash flow",
    "oracle_agent — ML-прогнозы, классификация, аномалии",
]

# ─── Существующие инфраструктурные сервисы ───────────────────────────────────

EXISTING_SERVICES = [
    "CONDUCTOR v2 — мета-оркестратор, 17-шаговый pipeline, scope classifier",
    "QA-AGENT — critic pattern, PII detection, injection markers",
    "COMPLIANCE-AGENT — 152-ФЗ, PII masking, AI disclaimers, approval gates",
    "Health Monitor — DEADMAN kill-switch, 6 статусов агентов",
    "Billing/Metering — кредитная система (FREE:50, STARTER:500, PRO:2000/день)",
    "Session Trace — correlation ID, replay, blame assignment",
    "Safeguards — 10 классов (deadlock, latency, role boundary, lifecycle, firewall, etc.)",
    "LLM Client — Claude API + circuit breaker (3 failures → Ollama) + prompt caching 90%",
    "A/B Engine — Welch's t-test, multi-armed bandit",
    "Observability — Langfuse-compatible traces, cost tracking",
    "Scope Classifier — предотвращение scope creep, MAX_DIRECTORS=3",
    "PDF/Excel генераторы — fpdf2, openpyxl, DejaVu шрифты",
]

# ─── Ограничения проекта ─────────────────────────────────────────────────────

CONSTRAINTS = {
    "team": "1 человек (основатель), работает вечерами после основной работы",
    "budget": "0 руб на разработку (open-source, бесплатный продукт)",
    "timeline": "Каждая задача должна быть выполнима за 1 вечер (2-4 часа)",
    "no_ooo": "ООО планируется август 2026, пока физлицо",
    "philosophy": "Open-source, исходники на GitHub, никаких продаж до MVP",
    "server": "1 VPS, 60GB диск, все сервисы в Docker Compose",
}


def get_project_context_text() -> str:
    """Сформировать текстовый контекст проекта для промпта CEO."""
    lines = []

    lines.append("ПЛАТФОРМА:")
    for key, val in PLATFORM_CONTEXT.items():
        lines.append(f"  - {key}: {val}")

    lines.append("\nСУЩЕСТВУЮЩИЕ АГЕНТЫ (21+, переиспользуй!):")
    for agent in EXISTING_AGENTS:
        lines.append(f"  - {agent}")

    lines.append("\nИНФРАСТРУКТУРНЫЕ СЕРВИСЫ (уже работают):")
    for svc in EXISTING_SERVICES:
        lines.append(f"  - {svc}")

    lines.append("\nОГРАНИЧЕНИЯ:")
    for key, val in CONSTRAINTS.items():
        lines.append(f"  - {val}")

    return "\n".join(lines)
