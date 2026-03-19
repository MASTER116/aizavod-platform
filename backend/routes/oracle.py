"""ORACLE Agent — API routes для Zavod-ii backend."""
from __future__ import annotations

import io
import logging

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

logger = logging.getLogger("aizavod.routes.oracle")

router = APIRouter(prefix="/api/oracle", tags=["oracle"])


@router.get("/health")
def oracle_health():
    return {"status": "ok", "agent": "oracle", "version": "1.0.0"}


@router.post("/predict")
async def oracle_predict(
    file: UploadFile = File(...),
    target_col: str | None = Form(None),
    force_type: str | None = Form(None),
    forecast_periods: int = Form(30),
):
    """Загрузить CSV/Excel и получить ML-прогноз от ORACLE."""
    from services.oracle_agent import get_oracle_agent

    content = await file.read()
    filename = file.filename or "data.csv"

    try:
        if filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать файл: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Файл пустой")

    try:
        agent = get_oracle_agent()
        result = agent.predict_sync(df, target_col, force_type, forecast_periods)
    except Exception as e:
        logger.exception("Ошибка ORACLE predict")
        raise HTTPException(status_code=500, detail=f"Ошибка предсказания: {e}")

    return result


@router.post("/predict/json")
async def oracle_predict_json(
    data: list[dict],
    target_col: str | None = None,
    force_type: str | None = None,
    forecast_periods: int = 30,
):
    """Принять данные в JSON и получить ML-прогноз."""
    from services.oracle_agent import get_oracle_agent

    if not data:
        raise HTTPException(status_code=400, detail="Данные пусты")

    try:
        df = pd.DataFrame(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не удалось создать DataFrame: {e}")

    try:
        agent = get_oracle_agent()
        result = agent.predict_sync(df, target_col, force_type, forecast_periods)
    except Exception as e:
        logger.exception("Ошибка ORACLE predict/json")
        raise HTTPException(status_code=500, detail=f"Ошибка предсказания: {e}")

    return result
