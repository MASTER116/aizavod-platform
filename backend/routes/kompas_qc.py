"""
API-эндпоинты KOMPAS-QC.
"""

import os
import tempfile
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from services.kompas_qc import KompasQCEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/kompas-qc", tags=["KOMPAS-QC"])

engine = KompasQCEngine()

UPLOAD_DIR = Path(tempfile.gettempdir()) / "kompas_qc"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/health")
async def health():
    """Статус KOMPAS-QC."""
    return {
        "status": "ok",
        "version": engine.VERSION,
        "materials_in_db": len(engine.mapper.mappings),
    }


@router.post("/material")
async def convert_material(gb_grade: str):
    """Конвертировать марку материала GB → ГОСТ."""
    result = engine.convert_material(gb_grade)
    return result


@router.post("/text")
async def convert_text(text: str):
    """Извлечь и конвертировать GB-марки в тексте."""
    result = engine.convert_text(text)
    return result


@router.post("/analyze")
async def analyze_dxf(file: UploadFile = File(...)):
    """Анализ DXF-файла без конвертации."""
    if not file.filename.lower().endswith(".dxf"):
        raise HTTPException(400, "Поддерживается только формат .dxf")

    input_path = UPLOAD_DIR / file.filename
    try:
        content = await file.read()
        input_path.write_bytes(content)
        result = engine.analyze_file(str(input_path))
        return result
    finally:
        input_path.unlink(missing_ok=True)


@router.post("/convert")
async def convert_dxf(file: UploadFile = File(...)):
    """Конвертировать DXF GB → ГОСТ."""
    if not file.filename.lower().endswith(".dxf"):
        raise HTTPException(400, "Поддерживается только формат .dxf")

    input_path = UPLOAD_DIR / file.filename
    output_dir = UPLOAD_DIR / "output"
    output_dir.mkdir(exist_ok=True)

    try:
        content = await file.read()
        input_path.write_bytes(content)

        result = engine.convert_file(str(input_path), str(output_dir))

        if not result.get("success"):
            raise HTTPException(500, result.get("errors", ["Ошибка конвертации"]))

        return result
    finally:
        input_path.unlink(missing_ok=True)


@router.post("/convert/download")
async def convert_and_download(file: UploadFile = File(...)):
    """Конвертировать DXF и скачать результат."""
    if not file.filename.lower().endswith(".dxf"):
        raise HTTPException(400, "Поддерживается только формат .dxf")

    input_path = UPLOAD_DIR / file.filename
    output_dir = UPLOAD_DIR / "output"
    output_dir.mkdir(exist_ok=True)

    content = await file.read()
    input_path.write_bytes(content)

    result = engine.convert_file(str(input_path), str(output_dir))

    if not result.get("success"):
        input_path.unlink(missing_ok=True)
        raise HTTPException(500, result.get("errors", ["Ошибка конвертации"]))

    output_file = result.get("output_file")
    if output_file and Path(output_file).exists():
        return FileResponse(
            output_file,
            media_type="application/dxf",
            filename=Path(output_file).name,
        )

    raise HTTPException(500, "Выходной файл не создан")


@router.get("/materials/search")
async def search_materials(q: str):
    """Поиск по базе материалов."""
    from services.kompas_qc.material_db import search_gb
    results = search_gb(q)
    return [
        {
            "gb": m.gb_grade,
            "gost": m.gost_grade,
            "gb_standard": m.gb_standard,
            "gost_standard": m.gost_standard,
            "category": m.category,
            "description": m.description,
            "confidence": m.confidence,
        }
        for m in results
    ]


@router.get("/materials/all")
async def list_materials():
    """Полная база соответствий."""
    from services.kompas_qc.material_db import ALL_MAPPINGS
    return [
        {
            "gb": m.gb_grade,
            "gost": m.gost_grade,
            "gb_standard": m.gb_standard,
            "gost_standard": m.gost_standard,
            "category": m.category,
            "description": m.description,
            "confidence": m.confidence,
        }
        for m in ALL_MAPPINGS
    ]
