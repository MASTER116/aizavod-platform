"""Monetization routes — campaigns, media kit, rate card."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import Campaign, Character
from ..schemas import CampaignCreate, CampaignRead, CampaignUpdate

router = APIRouter(prefix="/admin/api", tags=["monetization"])


# ─── Campaigns ──────────────────────────────────────────────────────────────


@router.get("/campaigns", response_model=List[CampaignRead])
def list_campaigns(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()


@router.post("/campaigns", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    campaign = Campaign(**body.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    return campaign


# ─── Media Kit & Rate Card ──────────────────────────────────────────────────


@router.get("/monetization/media_kit")
def get_media_kit(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from services.monetization import generate_media_kit_data

    character = db.query(Character).filter(Character.is_active.is_(True)).first()
    name = character.name if character else "AI Fitness Girl"

    return generate_media_kit_data(db, character_name=name)


@router.get("/monetization/rate_card")
def get_rate_card(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    from services.monetization import calculate_rate_card

    return calculate_rate_card(db)
