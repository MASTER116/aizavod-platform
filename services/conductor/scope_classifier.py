"""Task Scope Classifier — пре-классификация задачи ДО CEO-декомпозиции.

Определяет тип задачи (technical/business/marketing/legal/full)
и возвращает список допустимых директоров.

Решает проблему scope creep: CEO видит только релевантных директоров,
а не все 8.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("aizavod.scope_classifier")

# Маппинг scope → допустимые директора
SCOPE_DIRECTORS: dict[str, list[str]] = {
    "technical": ["cto"],
    "product": ["cto", "cpo"],
    "business": ["cto", "cfo", "cpo"],
    "marketing": ["cmo", "cdo"],
    "legal": ["clo"],
    "operations": ["coo", "cto"],
    "full": ["cto", "cfo", "cmo", "cpo", "clo"],
}

# Ключевые слова для быстрой классификации (0 токенов LLM)
SCOPE_KEYWORDS: dict[str, list[str]] = {
    "technical": [
        "разработай", "напиши код", "создай бот", "деплой", "настрой сервер",
        "исправь баг", "рефактор", "api", "docker", "база данных", "бэкенд",
        "фронтенд", "telegram бот", "тг бот", "тг-бот", "микросервис",
        "интеграци", "миграци", "тест", "ci/cd", "git", "python", "fastapi",
        "redis", "postgres", "nginx", "celery", "aiogram", "webhook",
        "endpoint", "обнови зависимост", "почини", "переделай",
        "автоматизируй", "оптимизируй", "добавь функци", "добавь фич",
        "напиши скрипт", "парсер", "краулер", "скрейпер",
    ],
    "product": [
        "фича", "mvp", "прототип", "roadmap", "спецификация",
        "user story", "требования к продукт", "продуктов",
    ],
    "business": [
        "бизнес-план", "финмодель", "финмодел", "монетизаци", "тариф", "подписк",
        "unit-экономик", "окупаемость", "инвестиц", "кредит",
        "грант", "конкурс", "хакатон", "модель монетизац",
        "бизнес модел", "финансовая модел",
    ],
    "marketing": [
        "маркетинг", "контент", "instagram", "tiktok", "youtube",
        "seo", "продвижени", "реклам", "пост", "статья на хабр",
        "pr", "devrel", "лендинг", "посадочная",
    ],
    "legal": [
        "юридическ", "договор", "патент", "товарный знак", "лицензи",
        "регистрация ооо", "регистрация ип", "152-фз", "compliance",
        "nda", "оферт", "политика конфиденциальности",
    ],
    "operations": [
        "процесс", "автоматизация бизнес", "партнёр", "интеграция с",
        "поддержка клиент", "онбординг",
    ],
}

# Явные маркеры "full scope" — только когда пользователь просит полный план
FULL_SCOPE_MARKERS = [
    "полный план", "бизнес-план с нуля", "запусти продукт на рынок",
    "от идеи до запуска", "всё что нужно для", "комплексн",
    "полная стратегия", "стратегический план",
]

MAX_DIRECTORS = 3


def classify_task_scope(task: str) -> str:
    """Классифицировать задачу по scope.

    Returns: "technical", "product", "business", "marketing", "legal", "operations", "full"
    """
    task_lower = task.lower()

    # Проверка на full scope (только при явных маркерах)
    for marker in FULL_SCOPE_MARKERS:
        if marker in task_lower:
            logger.info("SCOPE: full (маркер: '%s')", marker)
            return "full"

    # Подсчёт очков по каждому scope
    scores: dict[str, int] = {}
    for scope, keywords in SCOPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in task_lower)
        if score > 0:
            scores[scope] = score

    if scores:
        best_scope = max(scores, key=scores.get)
        logger.info("SCOPE: %s (score=%d, all=%s)", best_scope, scores[best_scope], scores)
        return best_scope

    # По умолчанию — technical (безопасный выбор, не раздувает scope)
    logger.info("SCOPE: technical (default — нет совпадений)")
    return "technical"


def get_allowed_directors(task: str) -> list[str]:
    """Вернуть список допустимых директоров для задачи."""
    scope = classify_task_scope(task)
    allowed = SCOPE_DIRECTORS.get(scope, ["cto"])
    logger.info("ALLOWED DIRECTORS for scope '%s': %s", scope, allowed)
    return allowed


def filter_ceo_directors(task: str, ceo_selected: list[dict]) -> list[dict]:
    """Отфильтровать директоров, выбранных CEO, по scope задачи.

    Убирает директоров, не входящих в допустимый scope.
    Ограничивает максимум MAX_DIRECTORS.
    """
    allowed = get_allowed_directors(task)
    filtered = []
    removed = []

    for dt in ceo_selected:
        role = dt.get("role", "")
        if role in allowed:
            filtered.append(dt)
        else:
            removed.append(role)

    if removed:
        logger.warning(
            "SCOPE GUARD: убраны директора %s (не в scope для задачи)", removed
        )

    # Жёсткий лимит
    if len(filtered) > MAX_DIRECTORS:
        excess = [d.get("role") for d in filtered[MAX_DIRECTORS:]]
        logger.warning("SCOPE GUARD: обрезано до %d директоров (убраны: %s)", MAX_DIRECTORS, excess)
        filtered = filtered[:MAX_DIRECTORS]

    # Если всё отфильтровано — оставить хотя бы CTO
    if not filtered:
        logger.warning("SCOPE GUARD: все директора отфильтрованы, fallback на CTO")
        cto_tasks = [dt for dt in ceo_selected if dt.get("role") == "cto"]
        if cto_tasks:
            filtered = cto_tasks[:1]
        else:
            filtered = [{"role": "cto", "task": ceo_selected[0].get("task", ""), "priority": "high"}]

    return filtered
