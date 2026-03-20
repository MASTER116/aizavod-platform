"""CEO Agent — главный оркестратор Zavod-ii.

Принимает задачу от идейного вдохновителя (основателя),
анализирует и распределяет между директорами/агентами.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("aizavod.ceo_agent")

# Структура управления Zavod-ii
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

  🎓 Наука и гранты
     → ScholarAgent (грантовые заявки, научные статьи, ГОСТ/ВАК)

  📢 DevRel и продвижение
     → HeraldAgent (open-source, Habr, Telegram-канал, Product Hunt)

  ✏️ Нейминг и бренд
     → NamerAgent (генерация названий, проверка доменов/ТЗ/ЕГРЮЛ)

  🔒 IP и патенты
     → GuardianIPAgent (товарные знаки, патенты, IP-аудит)

  🎙 Голосовой отдел
     → VoiceAgent (скрипты звонков, TTS-оптимизация)

  💵 Казначейство
     → TreasurerAgent (монетизация, расходы, cash flow, ценообразование)

🛡 Кросс-модули:
  → DARWIN (самообучение, оптимизация агентов, контроль качества)
  → GUARDIAN (антифрод, антиабьюз, безопасность ввода/вывода)
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

        prompt = f"""Ты — CEO-агент (генеральный директор) Zavod-ii.
Тебе задаёт вопрос идейный вдохновитель (основатель Азат).

{ORG_STRUCTURE}

ТЕКУЩЕЕ СОСТОЯНИЕ AI ZAVOD:
- Платформа: FastAPI + PostgreSQL + Redis + Docker на Hetzner (Германия)
- 19 агентов: CEO, Certifier, OpportunityScanner, IdeaGenerator, MarketAnalyzer,
  FreelanceAgent, PricingAgent, OutreachAgent, ContentFactory, LawyerAgent,
  AccountantAgent, DarwinAgent, GuardianAgent, ScholarAgent, HeraldAgent,
  NamerAgent, GuardianIPAgent, VoiceAgent, TreasurerAgent
- CONDUCTOR — интеллектуальный маршрутизатор запросов
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
        """Break down a task and assign to directors/agents.

        Delegates to CONDUCTOR orchestrate() which has scope classifier,
        project context, and scope guard to prevent scope creep.
        """
        from services.conductor import get_conductor
        conductor = get_conductor()
        tree = await conductor.orchestrate(task, depth=3)

        if tree.get("status") == "error":
            return f"Ошибка декомпозиции: {tree.get('message', '?')}"

        # Format tree as readable text
        lines = []
        lines.append(f"📋 Задача: {task[:200]}")
        lines.append(f"🔍 Тип: {tree.get('task_type', '?')}")
        lines.append(f"📊 Анализ: {tree.get('analysis', '')[:300]}")

        reuse = tree.get("reuse", [])
        if reuse:
            lines.append(f"♻️ Переиспользуем: {', '.join(reuse[:5])}")

        lines.append("")

        for d in tree.get("directors", []):
            lines.append(f"👔 {d.get('title', d.get('role', '?'))}")
            if d.get("justification"):
                lines.append(f"   Зачем: {d['justification'][:100]}")
            lines.append(f"   Задача: {d.get('task', '')[:200]}")
            deliverables = d.get("deliverables", [])
            if deliverables:
                lines.append(f"   Результат: {', '.join(deliverables[:5])}")
            hours = d.get("estimated_hours", 0)
            if hours:
                lines.append(f"   Время: {hours}ч")

            for dept in d.get("departments", []):
                lines.append(f"   📁 {dept.get('department', '?')}: {dept.get('task', '')[:80]}")
                for spec in dept.get("specialists", []):
                    lines.append(f"      👤 {spec.get('specialist', '?')}: {spec.get('task', '')[:60]}")
            lines.append("")

        report = tree.get("report", {})
        if report:
            lines.append("─" * 30)
            lines.append(f"📊 Итог: {report.get('summary', '')[:200]}")
            for h in report.get("highlights", [])[:3]:
                lines.append(f"  ✅ {h[:80]}")
            for ns in report.get("next_steps", [])[:3]:
                lines.append(f"  ➡️ {ns[:80]}")

        tokens = tree.get("tokens", {})
        if tokens.get("total", 0) > 0:
            lines.append(f"\n🔢 Токены: {tokens['input']:,} in + {tokens['output']:,} out = {tokens['total']:,}")

        quality = tree.get("ceo_quality", {})
        if quality:
            lines.append(f"📈 Качество CEO: {quality.get('score', 0):.1f}/10")

        return "\n".join(lines)

    async def strategic_plan(self) -> str:
        """Generate current strategic plan."""
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        prompt = f"""Ты — CEO-агент Zavod-ii. Составь стратегический план на ближайшие 2 недели.

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
