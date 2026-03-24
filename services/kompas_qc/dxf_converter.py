"""
DXF-конвертер: парсинг GB-чертежей и генерация ГОСТ-оформления.
Использует библиотеку ezdxf.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import ezdxf
    from ezdxf.entities import Text, MText, Dimension
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False
    logger.warning("ezdxf не установлен. DXF-конвертация недоступна. pip install ezdxf")

from .material_mapper import MaterialMapper, MappingResult


@dataclass
class ConversionResult:
    input_file: str
    output_file: Optional[str] = None
    materials_converted: list[MappingResult] = field(default_factory=list)
    texts_converted: int = 0
    datums_converted: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = False


# Маппинг баз GD&T: Latin → Cyrillic
DATUM_MAP = {
    "A": "А", "B": "Б", "C": "В", "D": "Г", "E": "Д",
    "F": "Е", "G": "Ж", "H": "И", "J": "К", "K": "Л",
    "L": "М", "M": "Н", "N": "П", "P": "Р",
}

# Паттерн для обозначений баз в GD&T feature control frames
DATUM_PATTERN = re.compile(r'(?<=\|)([A-P])(?=\||\s|$)')

# Китайские подписи основной надписи → ГОСТ
TITLE_BLOCK_MAP = {
    "零件名称": "Наименование",
    "名称": "Наименование",
    "图号": "Обозначение",
    "图纸编号": "Обозначение",
    "材料": "Материал",
    "比例": "Масштаб",
    "重量": "Масса",
    "质量": "Масса",
    "设计": "Разраб.",
    "校核": "Пров.",
    "审核": "Т.контр.",
    "批准": "Утв.",
    "日期": "Дата",
    "数量": "Кол-во",
    "单位": "Ед.",
    "版本": "Лит.",
    "页": "Лист",
    "共页": "Листов",
}

# Шероховатость: GB/T 131 → ГОСТ 2.309
ROUGHNESS_REPLACEMENTS = {
    "Ra0.8": "Ra 0,8",
    "Ra1.6": "Ra 1,6",
    "Ra3.2": "Ra 3,2",
    "Ra6.3": "Ra 6,3",
    "Ra12.5": "Ra 12,5",
    "Ra25": "Ra 25",
}


class DXFConverter:
    """Конвертер DXF-чертежей из GB в ГОСТ."""

    def __init__(self):
        if not HAS_EZDXF:
            raise ImportError("ezdxf не установлен. Выполните: pip install ezdxf")
        self.mapper = MaterialMapper()

    def convert(self, input_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """Конвертировать DXF файл из GB в ГОСТ."""
        result = ConversionResult(input_file=input_path)

        if not output_path:
            p = Path(input_path)
            output_path = str(p.parent / f"{p.stem}_GOST{p.suffix}")
        result.output_file = output_path

        try:
            doc = ezdxf.readfile(input_path)
        except Exception as e:
            result.errors.append(f"Ошибка чтения DXF: {e}")
            return result

        # Обработка всех текстовых сущностей
        msp = doc.modelspace()

        for entity in msp:
            if entity.dxftype() == "TEXT":
                self._process_text(entity, result)
            elif entity.dxftype() == "MTEXT":
                self._process_mtext(entity, result)

        # Обработка блоков (включая основную надпись)
        for block in doc.blocks:
            for entity in block:
                if entity.dxftype() == "TEXT":
                    self._process_text(entity, result)
                elif entity.dxftype() == "MTEXT":
                    self._process_mtext(entity, result)

        # Сохранение
        try:
            doc.saveas(output_path)
            result.success = True
            result.materials_converted = self.mapper.extract_and_map(
                " ".join(self._all_texts)
            )
        except Exception as e:
            result.errors.append(f"Ошибка сохранения DXF: {e}")

        return result

    def _process_text(self, entity, result: ConversionResult):
        """Обработка TEXT-сущности."""
        text = entity.dxf.text
        if not text:
            return

        new_text = self._convert_text(text, result)
        if new_text != text:
            entity.dxf.text = new_text
            result.texts_converted += 1

    def _process_mtext(self, entity, result: ConversionResult):
        """Обработка MTEXT-сущности."""
        text = entity.text
        if not text:
            return

        new_text = self._convert_text(text, result)
        if new_text != text:
            entity.text = new_text
            result.texts_converted += 1

    def _convert_text(self, text: str, result: ConversionResult) -> str:
        """Конвертировать текст: материалы, подписи, базы, шероховатость."""
        original = text

        # 1. Замена китайских подписей основной надписи
        for cn, gost in TITLE_BLOCK_MAP.items():
            if cn in text:
                text = text.replace(cn, gost)

        # 2. Замена материалов GB → ГОСТ
        text, replacements = self.mapper.replace_in_text(text)
        for r in replacements:
            if r.needs_review:
                result.warnings.append(
                    f"Материал '{r.original}' → '{r.mapped}' (confidence: {r.confidence:.0%})"
                )

        # 3. Перелитеровка баз GD&T
        def replace_datum(match):
            letter = match.group(1)
            cyrillic = DATUM_MAP.get(letter, letter)
            if cyrillic != letter:
                result.datums_converted += 1
            return cyrillic

        text = DATUM_PATTERN.sub(replace_datum, text)

        # 4. Шероховатость: точка → запятая
        for gb_val, gost_val in ROUGHNESS_REPLACEMENTS.items():
            text = text.replace(gb_val, gost_val)

        # 5. Десятичный разделитель: точка → запятая в числах
        # (только в размерных текстах, не в обозначениях)
        # Пока отключено — требует контекстного анализа

        return text

    @property
    def _all_texts(self) -> list[str]:
        """Кеш всех текстов для пакетного анализа материалов."""
        return getattr(self, '_text_cache', [])

    def analyze(self, input_path: str) -> dict:
        """Анализ DXF без конвертации. Возвращает статистику."""
        try:
            doc = ezdxf.readfile(input_path)
        except Exception as e:
            return {"error": str(e)}

        texts = []
        msp = doc.modelspace()

        for entity in msp:
            if entity.dxftype() == "TEXT":
                texts.append(entity.dxf.text or "")
            elif entity.dxftype() == "MTEXT":
                texts.append(entity.text or "")

        for block in doc.blocks:
            for entity in block:
                if entity.dxftype() == "TEXT":
                    texts.append(entity.dxf.text or "")
                elif entity.dxftype() == "MTEXT":
                    texts.append(entity.text or "")

        all_text = " ".join(texts)
        materials = self.mapper.extract_and_map(all_text)

        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', all_text))

        return {
            "total_text_entities": len(texts),
            "chinese_characters": chinese_chars,
            "materials_found": len(materials),
            "materials": [
                {
                    "gb": m.original,
                    "gost": m.mapped,
                    "confidence": m.confidence,
                    "needs_review": m.needs_review,
                }
                for m in materials
            ],
            "mapper_stats": self.mapper.get_report(),
        }
