"""Тесты для Task Scope Classifier — предотвращение scope creep."""

import pytest

from services.conductor.scope_classifier import (
    classify_task_scope,
    get_allowed_directors,
    filter_ceo_directors,
    MAX_DIRECTORS,
)


# ─── classify_task_scope ─────────────────────────────────────────────────────


class TestClassifyTaskScope:
    """Тесты классификации scope задачи."""

    def test_technical_bot_development(self):
        assert classify_task_scope("Разработай TG-бот для сертификации авто") == "technical"

    def test_technical_fix_bug(self):
        assert classify_task_scope("Исправь баг в API endpoint /health") == "technical"

    def test_technical_deploy(self):
        assert classify_task_scope("Деплой приложения в Docker на сервер") == "technical"

    def test_technical_refactor(self):
        assert classify_task_scope("Рефактор conductor.py — разбить на модули") == "technical"

    def test_technical_database(self):
        assert classify_task_scope("Настрой PostgreSQL репликацию") == "technical"

    def test_technical_write_tests(self):
        assert classify_task_scope("Напиши тесты для QA-агента") == "technical"

    def test_marketing_campaign(self):
        assert classify_task_scope("Запусти маркетинговую кампанию в Instagram") == "marketing"

    def test_marketing_content(self):
        assert classify_task_scope("Создай контент-план для TikTok") == "marketing"

    def test_legal_trademark(self):
        assert classify_task_scope("Зарегистрируй товарный знак Zavod-ii") == "legal"

    def test_legal_contract(self):
        assert classify_task_scope("Подготовь договор оферты") == "legal"

    def test_business_monetization(self):
        assert classify_task_scope("Разработай модель монетизации с тарифами") == "business"

    def test_full_scope_explicit(self):
        assert classify_task_scope("Создай полный план запуска продукта от идеи до запуска") == "full"

    def test_full_scope_business_plan(self):
        assert classify_task_scope("Составь полный бизнес-план с нуля") == "full"

    def test_default_to_technical(self):
        """Неопределённые задачи → technical (безопасный дефолт)."""
        assert classify_task_scope("Сделай что-нибудь полезное") == "technical"

    def test_product_mvp(self):
        assert classify_task_scope("Создай MVP прототип продукта") == "product"


# ─── get_allowed_directors ───────────────────────────────────────────────────


class TestGetAllowedDirectors:
    """Тесты допустимых директоров."""

    def test_technical_only_cto(self):
        allowed = get_allowed_directors("Разработай Telegram бот")
        assert allowed == ["cto"]

    def test_marketing_cmo_cdo(self):
        allowed = get_allowed_directors("Создай контент для Instagram")
        assert "cmo" in allowed

    def test_legal_only_clo(self):
        allowed = get_allowed_directors("Зарегистрируй товарный знак")
        assert allowed == ["clo"]

    def test_business_includes_cfo(self):
        allowed = get_allowed_directors("Разработай финмодель монетизации")
        assert "cfo" in allowed

    def test_no_hr_for_technical(self):
        allowed = get_allowed_directors("Напиши код парсера")
        assert "chro" not in allowed

    def test_no_marketing_for_technical(self):
        allowed = get_allowed_directors("Деплой на сервер")
        assert "cmo" not in allowed


# ─── filter_ceo_directors ────────────────────────────────────────────────────


class TestFilterCeoDirectors:
    """Тесты фильтрации CEO-декомпозиции."""

    def test_removes_irrelevant_directors(self):
        """CEO выбрал CMO и CHRO для технической задачи — убрать их."""
        ceo_selected = [
            {"role": "cto", "task": "Разработать бот"},
            {"role": "cmo", "task": "Маркетинг бота"},
            {"role": "chro", "task": "Нанять разработчиков"},
        ]
        result = filter_ceo_directors("Разработай TG-бот", ceo_selected)
        roles = [d["role"] for d in result]
        assert roles == ["cto"]
        assert "cmo" not in roles
        assert "chro" not in roles

    def test_max_directors_limit(self):
        """Не больше MAX_DIRECTORS."""
        ceo_selected = [
            {"role": "cto", "task": "Код"},
            {"role": "cfo", "task": "Финансы"},
            {"role": "cpo", "task": "Продукт"},
            {"role": "cmo", "task": "Маркетинг"},
            {"role": "clo", "task": "Юридическое"},
        ]
        result = filter_ceo_directors("Полный бизнес-план с нуля", ceo_selected)
        assert len(result) <= MAX_DIRECTORS

    def test_fallback_to_cto_when_all_filtered(self):
        """Если все отфильтрованы — оставить CTO."""
        ceo_selected = [
            {"role": "cmo", "task": "Маркетинг"},
            {"role": "chro", "task": "HR"},
        ]
        result = filter_ceo_directors("Исправь баг в API", ceo_selected)
        assert len(result) >= 1
        assert result[0]["role"] == "cto"

    def test_preserves_valid_directors(self):
        """Валидные директора не удаляются."""
        ceo_selected = [
            {"role": "cto", "task": "Разработка"},
        ]
        result = filter_ceo_directors("Напиши код бота", ceo_selected)
        assert len(result) == 1
        assert result[0]["role"] == "cto"

    def test_technical_task_no_sales(self):
        """Чисто техническая задача — нет продаж, финансов, HR."""
        ceo_selected = [
            {"role": "cto", "task": "Код"},
            {"role": "cfo", "task": "Бюджет"},
            {"role": "cmo", "task": "Продвижение"},
            {"role": "coo", "task": "Процессы"},
            {"role": "chro", "task": "Найм"},
            {"role": "clo", "task": "Лицензия"},
        ]
        result = filter_ceo_directors("Разработай микросервис авторизации", ceo_selected)
        roles = [d["role"] for d in result]
        assert "cto" in roles
        assert "cmo" not in roles
        assert "chro" not in roles
        assert "cfo" not in roles
