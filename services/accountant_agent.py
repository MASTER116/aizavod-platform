"""AccountantAgent — бухгалтерия, налоги, отчетность для ИП/ООО."""
from __future__ import annotations

import logging

from services.base_agent import BaseAgent

logger = logging.getLogger("aizavod.accountant_agent")


class AccountantAgent(BaseAgent):
    agent_name = "accountant"
    model_env_var = "ACCOUNTANT_MODEL"
    default_temperature = 0.2
    default_max_tokens = 2500

    system_prompt = (
        "Ты — опытный бухгалтер-консультант, специализирующийся на ИП и малом бизнесе (ООО) в России. "
        "Знаешь НК РФ, актуальные ставки налогов, сроки отчетности. "
        "Отвечай конкретно, с цифрами и сроками. "
        "Предупреждай, что ставки и лимиты нужно уточнять на дату обращения."
    )

    async def consult(self, question: str) -> str:
        """Общая консультация по налогам/бухгалтерии."""
        prompt = f"""Вопрос по бухгалтерии/налогам: {question}

Ответь:
1. Краткий ответ
2. Нормативная база (НК РФ, ФЗ)
3. Расчет (если применимо)
4. Сроки (оплаты, подачи отчетов)
5. Штрафы за нарушение"""
        return await self._call_llm(prompt)

    async def compare_tax_systems(self, revenue: str, expenses: str, activity: str) -> str:
        """Сравнение систем налогообложения."""
        prompt = f"""Сравни системы налогообложения для бизнеса.

Вид деятельности: {activity}
Ожидаемая выручка: {revenue}
Ожидаемые расходы: {expenses}

Сравни:
| Параметр | УСН 6% | УСН 15% | Патент | ОСН |
|----------|--------|---------|--------|-----|
| Налог за год | | | | |
| Взносы ИП | | | | |
| Отчетность | | | | |
| Сложность | | | | |

Итого нагрузка и рекомендация: какая система оптимальна и почему."""
        return await self._call_llm(prompt, max_tokens=3000)

    async def reporting_calendar(self, business_type: str = "ИП УСН 6%") -> str:
        """Календарь отчетности и платежей."""
        prompt = f"""Составь календарь отчетности и платежей на 2026 год.

Тип бизнеса: {business_type}

Формат:
| Срок | Что сдать/оплатить | Куда | Штраф за просрочку |
|------|-------------------|------|-------------------|

Включи: налоги, взносы, декларации, отчеты в ФНС, СФР."""
        return await self._call_llm(prompt, max_tokens=3000)

    async def payroll_calc(self, salary: str, region: str = "Москва") -> str:
        """Расчет зарплатных налогов и взносов."""
        prompt = f"""Рассчитай зарплатные налоги и взносы.

Оклад сотрудника: {salary}
Регион: {region}

Рассчитай:
1. НДФЛ (13%/15%)
2. Взносы работодателя (ПФР, ОМС, ФСС, травматизм)
3. Сотрудник получит на руки
4. Итого расход работодателя
5. Эффективная ставка налогообложения"""
        return await self._call_llm(prompt)


_agent: AccountantAgent | None = None


def get_accountant_agent() -> AccountantAgent:
    global _agent
    if _agent is None:
        _agent = AccountantAgent()
    return _agent
