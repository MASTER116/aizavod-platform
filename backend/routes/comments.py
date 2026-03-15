"""Comment management routes."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import Comment, Post, Character
from ..schemas import CommentRead

router = APIRouter(prefix="/admin/api/comments", tags=["comments"])


@router.get("", response_model=List[CommentRead])
def list_comments(
    unreplied: Optional[bool] = Query(default=None),
    spam: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    q = db.query(Comment)
    if unreplied is True:
        q = q.filter(Comment.reply_sent.is_(False))
    if spam is True:
        q = q.filter(Comment.is_spam.is_(True))
    elif spam is False:
        q = q.filter(Comment.is_spam.is_(False))
    return q.order_by(Comment.created_at.desc()).limit(limit).all()


@router.post("/{comment_id}/reply", response_model=CommentRead)
async def reply_to_comment(
    comment_id: int,
    reply_text: str = Query(...),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    post = db.query(Post).filter(Post.id == comment.post_id).first()
    if not post or not post.instagram_media_id:
        raise HTTPException(status_code=400, detail="Post not published on Instagram")

    from services.instagram_client import get_instagram_client
    from datetime import datetime

    client = get_instagram_client()
    await client.reply_to_comment(
        post.instagram_media_id,
        comment.platform_comment_id,
        reply_text,
    )

    comment.reply_text = reply_text
    comment.reply_sent = True
    comment.reply_sent_at = datetime.utcnow()
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/{comment_id}/mark_spam", response_model=CommentRead)
def mark_spam(
    comment_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_spam = True
    db.commit()
    db.refresh(comment)
    return comment
