"""Генерация PDF-документов для грантовых заявок."""
from __future__ import annotations

import logging
import os
from datetime import datetime

logger = logging.getLogger("aizavod.pdf_generator")


def generate_submission_pdf(text: str, title: str = "Документы на подачу", output_dir: str = "/tmp") -> str:
    """Сгенерировать PDF из текста. Возвращает путь к файлу."""
    try:
        from fpdf import FPDF
    except ImportError:
        logger.error("fpdf2 не установлен")
        return ""

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Используем встроенный шрифт Helvetica (поддержка кириллицы через UTF-8)
        font_dir = "/usr/share/fonts/truetype/dejavu"
        font_path = os.path.join(font_dir, "DejaVuSans.ttf")
        bold_path = os.path.join(font_dir, "DejaVuSans-Bold.ttf")

        if os.path.exists(font_path):
            pdf.add_font("DejaVu", "", font_path, uni=True)
            pdf.add_font("DejaVu", "B", bold_path, uni=True)
            font_name = "DejaVu"
        else:
            # Fallback — Helvetica (без кириллицы, но хоть что-то)
            font_name = "Helvetica"

        # Заголовок
        pdf.set_font(font_name, "B", 16)
        pdf.cell(0, 12, title[:80], ln=True, align="C")
        pdf.ln(5)

        # Дата
        pdf.set_font(font_name, "", 9)
        pdf.cell(0, 6, f"Сгенерировано: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}", ln=True, align="R")
        pdf.ln(5)

        # Тело документа
        pdf.set_font(font_name, "", 11)

        for line in text.split("\n"):
            stripped = line.strip()

            if not stripped:
                pdf.ln(3)
                continue

            # Заголовки ## и #
            if stripped.startswith("## "):
                pdf.ln(4)
                pdf.set_font(font_name, "B", 13)
                pdf.multi_cell(0, 7, stripped[3:])
                pdf.set_font(font_name, "", 11)
                pdf.ln(2)
            elif stripped.startswith("# "):
                pdf.ln(5)
                pdf.set_font(font_name, "B", 15)
                pdf.multi_cell(0, 8, stripped[2:])
                pdf.set_font(font_name, "", 11)
                pdf.ln(3)
            elif stripped.startswith("- ") or stripped.startswith("• "):
                pdf.multi_cell(0, 6, f"  {stripped}")
            elif stripped.startswith("**") and stripped.endswith("**"):
                pdf.set_font(font_name, "B", 11)
                pdf.multi_cell(0, 6, stripped.strip("*"))
                pdf.set_font(font_name, "", 11)
            else:
                # Убираем markdown bold из середины текста
                clean = stripped.replace("**", "").replace("__", "")
                pdf.multi_cell(0, 6, clean)

        # Сохранение
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in " _-").strip().replace(" ", "_")
        filename = f"docs_{safe_title}_{timestamp}.pdf"
        filepath = os.path.join(output_dir, filename)

        os.makedirs(output_dir, exist_ok=True)
        pdf.output(filepath)
        logger.info("PDF сохранён: %s", filepath)
        return filepath

    except Exception as exc:
        logger.error("Ошибка генерации PDF: %s", exc)
        return ""
