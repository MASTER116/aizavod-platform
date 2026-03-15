"""Content calendar and template management routes."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import ContentTemplate, Character, SystemSettings
from ..schemas import ContentTemplateCreate, ContentTemplateRead, ContentTemplateUpdate

router = APIRouter(prefix="/admin/api", tags=["content"])


# ─── Templates ──────────────────────────────────────────────────────────────


@router.get("/templates", response_model=List[ContentTemplateRead])
def list_templates(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    return db.query(ContentTemplate).filter(ContentTemplate.is_active.is_(True)).all()


@router.post("/templates", response_model=ContentTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    body: ContentTemplateCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    template = ContentTemplate(**body.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/templates/{template_id}", response_model=ContentTemplateRead)
def update_template(
    template_id: int,
    body: ContentTemplateUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    template = db.query(ContentTemplate).filter(ContentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    template = db.query(ContentTemplate).filter(ContentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.is_active = False
    db.commit()
    return {"deleted": template_id}


# ─── Calendar Generation ───────────────────────────────────────────────────


@router.post("/calendar/generate")
async def generate_calendar(
    days: int = Query(default=7, ge=1, le=30),
    character_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    """Generate a content calendar for N days using AI."""
    if character_id:
        character = db.query(Character).filter(Character.id == character_id).first()
    else:
        character = db.query(Character).filter(Character.is_active.is_(True)).first()

    if not character:
        raise HTTPException(status_code=404, detail="No active character found")

    settings = db.query(SystemSettings).first()

    from services.content_strategy import generate_weekly_calendar

    calendar = await generate_weekly_calendar(
        character=character,
        days=days,
        posts_per_day=settings.posts_per_day if settings else 2,
        stories_per_day=settings.stories_per_day if settings else 5,
        reels_per_week=settings.reels_per_week if settings else 3,
    )

    return {"days": len(calendar), "calendar": calendar}
