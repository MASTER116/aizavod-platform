"""
Маппер материалов GB → ГОСТ с AI-валидацией.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from .material_db import MaterialMapping, lookup_gb, search_gb, ALL_MAPPINGS

logger = logging.getLogger(__name__)


@dataclass
class MappingResult:
    original: str
    mapped: Optional[str] = None
    gb_standard: Optional[str] = None
    gost_standard: Optional[str] = None
    confidence: float = 0.0
    needs_review: bool = False
    note: str = ""


# Паттерны для распознавания GB-марок в тексте
GB_PATTERNS = [
    # Q-серия (Q235B, Q355C, Q195)
    re.compile(r'\b(Q\d{3}[A-E]?)\b', re.IGNORECASE),
    # Числовые марки (45, 20, 35)
    re.compile(r'\b(\d{2})\b(?=\s*(钢|steel|сталь|GB|GB/T))', re.IGNORECASE),
    # CrMo серия (40Cr, 30CrMnSi, 20CrMnTi)
    re.compile(r'\b(\d{2}Cr(?:Mo|Mn|Ni|V|Si|Ti|W)*(?:A|B)?)\b', re.IGNORECASE),
    # Нержавейка новая (06Cr19Ni10, 022Cr17Ni12Mo2)
    re.compile(r'\b(0?\d{2,3}Cr\d+Ni\d+(?:Mo\d+)?(?:Ti|N|Nb)?)\b', re.IGNORECASE),
    # Нержавейка старая (0Cr18Ni9, 1Cr18Ni9Ti)
    re.compile(r'\b([01]Cr\d+Ni\d+(?:Ti)?)\b', re.IGNORECASE),
    # Чугун серый (HT200, HT250)
    re.compile(r'\b(HT\d{3})\b', re.IGNORECASE),
    # Чугун высокопрочный (QT400-18, QT500-7)
    re.compile(r'\b(QT\d{3}-\d+)\b', re.IGNORECASE),
    # Алюминий (1060, 2024, 6061, 7075)
    re.compile(r'\b([1-8]\d{3})\b(?=\s*(?:铝|aluminum|алюмин|Al|GB))', re.IGNORECASE),
    # Латунь (H62, H68)
    re.compile(r'\b(H\d{2})\b', re.IGNORECASE),
    # Пружинная (65Mn, 60Si2Mn)
    re.compile(r'\b(\d{2}(?:Mn|Si\d*Mn))\b', re.IGNORECASE),
    # Бронза (QSn серия)
    re.compile(r'\b(QSn[\d.]+[-][\d.]+)\b', re.IGNORECASE),
]

# Китайские обозначения материалов → категория
CHINESE_MATERIAL_KEYWORDS = {
    "碳钢": "carbon_steel",
    "不锈钢": "stainless",
    "合金钢": "alloy_steel",
    "铸铁": "cast_iron",
    "灰铸铁": "grey_iron",
    "球墨铸铁": "ductile_iron",
    "铝合金": "aluminum",
    "铜合金": "copper",
    "黄铜": "brass",
    "青铜": "bronze",
    "弹簧钢": "spring",
}


class MaterialMapper:
    """Маппер GB-марок материалов в ГОСТ-эквиваленты."""

    def __init__(self):
        self.mappings = ALL_MAPPINGS
        self.stats = {"found": 0, "not_found": 0, "low_confidence": 0}

    def map_single(self, gb_grade: str) -> MappingResult:
        """Маппинг одной марки."""
        gb_grade = gb_grade.strip()

        # Точный поиск
        mapping = lookup_gb(gb_grade)
        if mapping:
            self.stats["found"] += 1
            result = MappingResult(
                original=gb_grade,
                mapped=f"{mapping.gost_grade} {mapping.gost_standard}",
                gb_standard=mapping.gb_standard,
                gost_standard=mapping.gost_standard,
                confidence=mapping.confidence,
                needs_review=mapping.confidence < 0.9,
                note=mapping.description,
            )
            if mapping.confidence < 0.9:
                self.stats["low_confidence"] += 1
            return result

        # Нечёткий поиск
        results = search_gb(gb_grade)
        if results:
            best = max(results, key=lambda m: m.confidence)
            self.stats["found"] += 1
            self.stats["low_confidence"] += 1
            return MappingResult(
                original=gb_grade,
                mapped=f"{best.gost_grade} {best.gost_standard}",
                gb_standard=best.gb_standard,
                gost_standard=best.gost_standard,
                confidence=best.confidence * 0.8,
                needs_review=True,
                note=f"Нечёткое соответствие: {best.gb_grade} → {best.gost_grade}",
            )

        # Не найдено
        self.stats["not_found"] += 1
        return MappingResult(
            original=gb_grade,
            needs_review=True,
            note="Марка не найдена в базе. Требуется ручная проверка.",
        )

    def extract_and_map(self, text: str) -> list[MappingResult]:
        """Извлечь GB-марки из текста и замапить на ГОСТ."""
        results = []
        found_grades = set()

        for pattern in GB_PATTERNS:
            for match in pattern.finditer(text):
                grade = match.group(1)
                if grade not in found_grades:
                    found_grades.add(grade)
                    results.append(self.map_single(grade))

        return results

    def replace_in_text(self, text: str) -> tuple[str, list[MappingResult]]:
        """Заменить GB-марки на ГОСТ в тексте. Возвращает (новый текст, список замен)."""
        replacements = []

        for pattern in GB_PATTERNS:
            for match in pattern.finditer(text):
                grade = match.group(1)
                result = self.map_single(grade)
                if result.mapped and result.confidence >= 0.8:
                    # Извлекаем только марку без стандарта для замены в тексте
                    mapping = lookup_gb(grade)
                    if mapping:
                        text = text.replace(grade, mapping.gost_grade)
                        replacements.append(result)

        return text, replacements

    def get_report(self) -> dict:
        """Статистика маппинга."""
        total = self.stats["found"] + self.stats["not_found"]
        return {
            "total_processed": total,
            "found": self.stats["found"],
            "not_found": self.stats["not_found"],
            "low_confidence": self.stats["low_confidence"],
            "accuracy": self.stats["found"] / max(total, 1) * 100,
        }
