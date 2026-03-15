"""DM management routes — conversations, messages, summary."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import DMConversation, DMMessage
from ..schemas import DMConversationRead, DMMessageRead, DMSummaryResponse

router = APIRouter(prefix="/admin/api/dms", tags=["dms"])


@router.get("/conversations", response_model=List[DMConversationRead])
def list_conversations(
    category: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    q = db.query(DMConversation).order_by(DMConversation.updated_at.desc())
    if category:
        q = q.filter(DMConversation.category == category)
    return q.limit(limit).all()


@router.get("/conversations/{conv_id}/messages", response_model=List[DMMessageRead])
def get_messages(
    conv_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    return (
        db.query(DMMessage)
        .filter(DMMessage.conversation_id == conv_id)
        .order_by(DMMessage.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/summary", response_model=DMSummaryResponse)
async def dm_summary(
    _admin: str = Depends(verify_admin_token),
):
    from services.character_manager import get_active_character
    from services.dm_manager import generate_dm_summary

    db_session = next(get_db())
    try:
        character = get_active_character(db_session)
        if not character:
            return DMSummaryResponse(total_conversations=0, total_unread=0, by_category={})
        return await generate_dm_summary(character)
    finally:
        db_session.close()


@router.post("/conversations/{conv_id}/mark-read")
def mark_read(
    conv_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    conv = db.query(DMConversation).get(conv_id)
    if not conv:
        return {"error": "Conversation not found"}
    conv.unread_count = 0
    db.commit()
    return {"ok": True}
