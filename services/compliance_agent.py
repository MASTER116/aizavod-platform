"""COMPLIANCE-AGENT — проверка на соответствие 152-ФЗ и другим регуляциям.

Функции:
- CHECK_PII: обнаружение персональных данных
- CHECK_STORAGE: где хранятся данные (РФ/зарубеж)
- MASK_PII: маскировка ПД перед передачей
- AUDIT_LOG: запись в аудит
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

logger = logging.getLogger("aizavod.compliance")

# PII patterns для детекции
PII_DETECTORS = {
    "phone_ru": r"(?:\+7|8)\s*[\(\-]?\d{3}[\)\-]?\s*\d{3}[\-]?\d{2}[\-]?\d{2}",
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "inn_individual": r"\bИНН\s*:?\s*(\d{12})\b",
    "inn_company": r"\bИНН\s*:?\s*(\d{10})\b",
    "passport": r"\b(\d{4})\s*(\d{6})\b",
    "snils": r"\b\d{3}-\d{3}-\d{3}\s*\d{2}\b",
    "card_number": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "birth_date": r"\b(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.(19|20)\d{2}\b",
    "full_name_ru": r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+вич|вна",
}

# Маски для замены PII
PII_MASKS = {
    "phone_ru": "+7 (***) ***-**-**",
    "email": "***@***.***",
    "inn_individual": "ИНН: ************",
    "inn_company": "ИНН: **********",
    "passport": "**** ******",
    "snils": "***-***-*** **",
    "card_number": "**** **** **** ****",
    "birth_date": "**.**.****",
    "full_name_ru": "*** *** ***",
}


class ComplianceAgent:
    """Агент проверки compliance с 152-ФЗ."""

    def __init__(self):
        self._audit_log: list[dict] = []

    def check_pii(self, text: str) -> dict:
        """Обнаружить PII в тексте."""
        found = {}
        for pii_type, pattern in PII_DETECTORS.items():
            matches = re.findall(pattern, text)
            if matches:
                found[pii_type] = {
                    "count": len(matches),
                    "severity": "critical" if pii_type in ("passport", "card_number", "snils") else "high",
                }

        compliant = len(found) == 0
        violations = []
        if not compliant:
            for pii_type, info in found.items():
                violations.append({
                    "law": "152-ФЗ",
                    "article": "ст. 3, п. 1",
                    "description": f"Обнаружены ПД типа '{pii_type}' ({info['count']} шт.)",
                    "severity": info["severity"],
                })

        return {
            "compliant": compliant,
            "pii_detected": found,
            "violations": violations,
            "total_pii_count": sum(v["count"] for v in found.values()),
        }

    def mask_pii(self, text: str) -> str:
        """Маскировать PII в тексте."""
        masked = text
        for pii_type, pattern in PII_DETECTORS.items():
            mask = PII_MASKS.get(pii_type, "***")
            masked = re.sub(pattern, mask, masked)
        return masked

    def check_data_residency(self, server_location: str) -> dict:
        """Проверить соответствие требованиям локализации данных."""
        ru_locations = ["russia", "россия", "рф", "ru", "moscow", "москва",
                        "spb", "selectel", "timeweb", "beget", "reg.ru"]
        is_ru = any(loc in server_location.lower() for loc in ru_locations)

        return {
            "compliant": is_ru,
            "server_location": server_location,
            "violation": None if is_ru else {
                "law": "152-ФЗ",
                "article": "ст. 18, ч. 5",
                "description": f"Персональные данные граждан РФ хранятся за пределами РФ ({server_location})",
                "severity": "critical",
                "penalty": "до 6 000 000 руб (первое), до 18 000 000 руб (повторное)",
                "recommendation": "Мигрировать ПД на серверы в РФ (Selectel, Timeweb Cloud)",
            },
        }

    def audit_log(self, action: str, agent: str, user_id: int | None = None, details: str = ""):
        """Записать действие в аудит-лог."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "agent": agent,
            "user_id": user_id,
            "details": details[:500],
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]
        logger.info("AUDIT: %s by %s — %s", action, agent, details[:100])
        return entry

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Получить последние записи аудит-лога."""
        return self._audit_log[-limit:]

    def full_compliance_check(self, text: str, agent: str, user_id: int | None = None) -> dict:
        """Полная проверка: PII + логирование."""
        pii_result = self.check_pii(text)
        storage_result = self.check_data_residency("Hetzner, Germany")

        all_violations = pii_result["violations"] + (
            [storage_result["violation"]] if storage_result.get("violation") else []
        )

        self.audit_log(
            action="compliance_check",
            agent=agent,
            user_id=user_id,
            details=f"PII: {pii_result['total_pii_count']}, Storage compliant: {storage_result['compliant']}",
        )

        return {
            "overall_compliant": pii_result["compliant"] and storage_result["compliant"],
            "pii": pii_result,
            "data_residency": storage_result,
            "violations": all_violations,
            "recommendations": [
                "Маскировать PII перед отправкой клиенту" if not pii_result["compliant"] else None,
                "Мигрировать ПД на RU-серверы" if not storage_result["compliant"] else None,
            ],
        }

    # === AI Content Disclaimer & Marking (закон о маркировке AI-контента) ===

    AI_DISCLAIMER_RU = "\n\n---\n_Сгенерировано AI-ассистентом Zavod-ii. Проверьте информацию перед использованием._"
    AI_DISCLAIMER_SHORT = " [AI]"

    def add_disclaimer(self, text: str, short: bool = False) -> str:
        """Добавить AI-disclaimer к ответу агента (закон о маркировке)."""
        if short:
            return text + self.AI_DISCLAIMER_SHORT
        return text + self.AI_DISCLAIMER_RU

    def requires_human_approval(self, action: str) -> bool:
        """Проверить, требует ли действие одобрения человека (agentic liability protection).

        Возвращает True для: подписание документов, отправка писем, финансовые операции,
        удаление данных, публикация контента.
        """
        high_risk_actions = [
            "sign_document", "send_email", "send_message",
            "financial_transaction", "payment", "invoice",
            "delete_data", "delete_account",
            "publish_content", "post_social",
            "create_contract", "submit_application",
            "make_call", "outbound_call",
        ]
        return action.lower() in high_risk_actions

    def approval_gate(self, action: str, agent: str, details: str, user_id: int | None = None) -> dict:
        """Human approval gate для высокорисковых действий."""
        needs_approval = self.requires_human_approval(action)
        self.audit_log(
            action=f"approval_gate:{action}",
            agent=agent,
            user_id=user_id,
            details=f"needs_approval={needs_approval}, {details[:200]}",
        )
        return {
            "action": action,
            "needs_approval": needs_approval,
            "message": f"Действие '{action}' требует вашего одобрения." if needs_approval else "Действие разрешено.",
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Singleton
_compliance_agent: ComplianceAgent | None = None


def get_compliance_agent() -> ComplianceAgent:
    global _compliance_agent
    if _compliance_agent is None:
        _compliance_agent = ComplianceAgent()
    return _compliance_agent
