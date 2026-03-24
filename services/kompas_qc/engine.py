"""
KOMPAS-QC Engine — основной движок конвертации.
Объединяет DXF-парсер, маппинг материалов, генерацию отчётов.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .material_mapper import MaterialMapper
from .dxf_converter import DXFConverter, ConversionResult

logger = logging.getLogger(__name__)


class KompasQCEngine:
    """Основной движок KOMPAS-QC."""

    VERSION = "0.1.0"

    def __init__(self):
        self.mapper = MaterialMapper()
        self._converter = None

    @property
    def converter(self):
        if self._converter is None:
            self._converter = DXFConverter()
        return self._converter

    def convert_file(self, input_path: str, output_dir: Optional[str] = None) -> dict:
        """
        Конвертировать файл GB → ГОСТ.

        Args:
            input_path: путь к исходному DXF-файлу
            output_dir: директория для результатов (по умолчанию — рядом с исходным)

        Returns:
            dict с результатами конвертации
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return {"error": f"Файл не найден: {input_path}", "success": False}

        if input_path.suffix.lower() not in (".dxf",):
            return {
                "error": f"Формат {input_path.suffix} пока не поддерживается. Поддерживается: .dxf",
                "success": False,
            }

        # Определяем выходные пути
        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = input_path.parent

        output_dxf = str(out_dir / f"{input_path.stem}_GOST.dxf")
        output_report = str(out_dir / f"{input_path.stem}_report.json")

        # Конвертация
        result = self.converter.convert(str(input_path), output_dxf)

        # Генерация отчёта
        report = self._generate_report(result)

        # Сохранение отчёта
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    def analyze_file(self, input_path: str) -> dict:
        """Анализ файла без конвертации."""
        input_path = Path(input_path)

        if not input_path.exists():
            return {"error": f"Файл не найден: {input_path}"}

        return self.converter.analyze(str(input_path))

    def convert_material(self, gb_grade: str) -> dict:
        """Конвертировать одну марку материала."""
        result = self.mapper.map_single(gb_grade)
        return {
            "gb": result.original,
            "gost": result.mapped,
            "confidence": result.confidence,
            "needs_review": result.needs_review,
            "note": result.note,
        }

    def convert_text(self, text: str) -> dict:
        """Конвертировать произвольный текст (извлечь и заменить GB-марки)."""
        new_text, replacements = self.mapper.replace_in_text(text)
        return {
            "original": text,
            "converted": new_text,
            "replacements": [
                {
                    "gb": r.original,
                    "gost": r.mapped,
                    "confidence": r.confidence,
                    "needs_review": r.needs_review,
                }
                for r in replacements
            ],
        }

    def _generate_report(self, result: ConversionResult) -> dict:
        """Генерация JSON-отчёта о конвертации."""
        return {
            "kompas_qc_version": self.VERSION,
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "input_file": result.input_file,
            "output_file": result.output_file,
            "summary": {
                "texts_converted": result.texts_converted,
                "datums_converted": result.datums_converted,
                "materials_found": len(result.materials_converted),
                "materials_needing_review": sum(
                    1 for m in result.materials_converted if m.needs_review
                ),
            },
            "materials": [
                {
                    "gb": m.original,
                    "gost": m.mapped,
                    "gb_standard": m.gb_standard,
                    "gost_standard": m.gost_standard,
                    "confidence": m.confidence,
                    "needs_review": m.needs_review,
                    "note": m.note,
                }
                for m in result.materials_converted
            ],
            "warnings": result.warnings,
            "errors": result.errors,
            "mapper_stats": self.mapper.get_report(),
        }
