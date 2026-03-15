"""System settings routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import SystemSettings
from ..schemas import SystemSettingsRead, SystemSettingsUpdate

router = APIRouter(prefix="/admin/api/settings", tags=["settings"])


@router.get("", response_model=SystemSettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    settings = db.query(SystemSettings).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not initialized")
    return settings


@router.put("", response_model=SystemSettingsRead)
def update_settings(
    body: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    settings = db.query(SystemSettings).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not initialized")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings
