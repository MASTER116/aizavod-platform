"""Instagram account management routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import SystemSettings

router = APIRouter(prefix="/admin/api/instagram", tags=["instagram"])


@router.post("/login")
async def instagram_login(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    """Login to Instagram and save session."""
    from services.instagram_client import get_instagram_client

    client = get_instagram_client()
    settings = db.query(SystemSettings).first()

    session_data = settings.instagram_session_data if settings else None
    client.login(session_data=session_data)

    # Save session
    if settings:
        settings.instagram_session_data = client.get_session_data()
        db.commit()

    return {"status": "ok", "message": "Instagram login successful"}


@router.get("/status")
async def instagram_status(
    _admin: str = Depends(verify_admin_token),
):
    """Check Instagram account status."""
    try:
        from services.instagram_client import get_instagram_client

        client = get_instagram_client()
        info = await client.get_account_info()
        return {"status": "connected", **info}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


@router.post("/test_post")
async def test_post(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    """Publish a test post to verify Instagram connection."""
    from services.instagram_client import get_instagram_client

    client = get_instagram_client()

    # Find the latest generated image
    from backend.models import Post, PostStatus

    post = (
        db.query(Post)
        .filter(Post.status.in_([PostStatus.GENERATED, PostStatus.APPROVED]))
        .filter(Post.image_path.isnot(None))
        .order_by(Post.created_at.desc())
        .first()
    )

    if not post or not post.image_path:
        raise HTTPException(status_code=404, detail="No generated post available for test")

    caption = post.caption_ru or post.caption_en or "Test post"
    media_id = await client.publish_photo(post.image_path, caption)

    post.instagram_media_id = media_id
    post.status = PostStatus.PUBLISHED
    from datetime import datetime
    post.published_at = datetime.utcnow()
    db.commit()

    return {"status": "ok", "media_id": media_id}
