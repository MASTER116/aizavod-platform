"""CEO Agent — главный оркестратор AI Zavod.

Принимает задачу от идейного вдохновителя (основателя),
анализирует и распределяет между директорами/агентами.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("aizavod.ceo_agent")

# Структура управления AI Zavod
ORG_STRUCTURE = """
ОРГАНИЗАЦИОННАЯ СТРУКТУРА AI ZAVOD:

👑 Идейный вдохновитель (Азат) — ставит задачи и направление

🧠 CEO-агент (ты) — анализирует задачу, составляет план, распределяет

📊 Директора:
  💰 Финансовый директор — гранты, конкурсы, инвестиции, бюджет
     → OpportunityScanner (поиск грантов/хакатонов)
     → IdeaGenerator (идеи монетизации)
     → MarketAnalyzer (анализ рынка)
     → ProposalGenerator (заявки на конкурсы)

  🛒 Директор по продажам — фриланс, клиенты, продажи
     → FreelanceAgent (поиск заказов, отклики)
     → PricingAgent (оценка проектов, КП)
     → OutreachAgent (холодные продажи, лиды)

  📱 Директор по контенту — Instagram Factory, генерация
     → ImageGenerator (fal.ai Flux Pro)
     → CaptionGenerator (Claude API)
     → InstagramClient (публикация)
     → Scheduler (расписание)

  🔧 Технический директор — инфраструктура, код, деплой
     → Docker Compose (8 контейнеров)
     → PostgreSQL / Redis
     → Nginx / SSL
     → Мониторинг

  📋 Директор по продукту — CERTIFIER, новые модули
     → CertifierService (RAG + Claude API)
     → Планирование новых агентов

  ⚖️ Юридический отдел — договоры, регистрация, трудовое право
     → LawyerAgent (юридические консультации, договоры, ИП/ООО)
     → AccountantAgent (налоги, бухгалтерия, отчетность, зарплата)
"""


class CEOAgent:
    """Main orchestrator — takes tasks from founder and delegates."""

    def __init__(self) -> None:
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("CEO_MODEL", "claude-haiku-4-5-20251001")

    async def process_question(self, question: str) -> str:
        """Answer a strategic question as CEO."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Ты — CEO-агент (генеральный директор) AI Zavod.
Тебе задаёт вопрос идейный вдохновитель (основатель Азат).

{ORG_STRUCTURE}

ТЕКУЩЕЕ СОСТОЯНИЕ AI ZAVOD:
- Платформа: FastAPI + PostgreSQL + Redis + Docker на Hetzner (Германия)
- Готовые модули: CERTIFIER (сертификация ТС), Instagram Factory (контент)
- 7 рабочих агентов: OpportunityScanner, IdeaGenerator, MarketAnalyzer,
  FreelanceAgent, PricingAgent, OutreachAgent, CertifierService
- Telegram-бот управления (aiogram 3)
- Нет ООО (план на август 2026)
- Бюджет: ~0 (НЗ 4.5 млн не трогаем)
- 1 человек (Азат работает вечерами после МАЗ)
- Anthropic API ключ оплачен

ВОПРОС ОСНОВАТЕЛЯ:
{question}

Ответь как CEO:
1. Краткий ответ (2-3 предложения)
2. Какому директору/агенту передать задачу
3. Конкретные шаги (3-5 пунктов)
4. Приоритет (критический / высокий / средний / низкий)
5. Оценка времени"""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.content[0].text

    async def assign_task(self, task: str) -> str:
        """Break down a task and assign to directors/agents."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Ты — CEO-агент AI Zavod. Основатель поставил задачу.

{ORG_STRUCTURE}

ЗАДАЧА ОТ ОСНОВАТЕЛЯ:
{task}

Составь план выполнения задачи:

## Анализ задачи
(что нужно сделать, какая цель)

## Декомпозиция по директорам

### 💰 Финансовый директор
- Задачи для него (если есть)
- Какие агенты задействовать

### 🛒 Директор по продажам
- Задачи для него (если есть)
- Какие агенты задействовать

### 📱 Директор по контенту
- Задачи для него (если есть)
- Какие агенты задействовать

### 🔧 Технический директор
- Задачи для него (если есть)
- Какие агенты задействовать

### 📋 Директор по продукту
- Задачи для него (если есть)

## Порядок выполнения
(пронумерованный список шагов с зависимостями)

## Критический путь
(что блокирует остальное)

## Оценка
- Время: сколько вечеров/выходных
- Риски: что может пойти не так
- Результат: что получим в итоге

Пиши конкретно, с привязкой к реальным агентам и модулям."""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.content[0].text

    async def strategic_plan(self) -> str:
        """Generate current strategic plan."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Ты — CEO-агент AI Zavod. Составь стратегический план на ближайшие 2 недели.

{ORG_STRUCTURE}

ТЕКУЩАЯ СИТУАЦИЯ (15.03.2026):
- Задеплоена платформа на Hetzner (Docker, 8 контейнеров)
- Работают 7 агентов (сканер, идеи, рынок, фриланс, цены, продажи, сертификация)
- CERTIFIER MVP работает (Claude Haiku 4.5, база знаний 7 документов)
- Instagram Factory создана но Instagram логин заблокирован (ChallengeRequired)
- Нет клиентов, нет выручки, нет ООО
- Дедлайн unicornroad.ru — 30 марта 2026
- Дедлайн РНФ — 16 июня 2026

ЦЕЛИ:
1. Первые деньги (хоть 1000 руб.)
2. Первый клиент (хоть 1 человек)
3. Подать на грант до 30 марта

Составь план по дням на 2 недели:
| День | Задача | Директор | Ожидаемый результат |
|------|--------|----------|---------------------|

В конце: ТОП-3 приоритета на эту неделю."""

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.content[0].text


_ceo: CEOAgent | None = None


def get_ceo_agent() -> CEOAgent:
    global _ceo
    if _ceo is None:
        _ceo = CEOAgent()
    return _ceo
