"""Webhook endpoints for n8n orchestration and external integrations."""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Post, PostStatus, Character, Campaign, GenerationLog

logger = logging.getLogger("aizavod.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ─── Request schemas ──────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    character_id: Optional[int] = None
    count: int = 1
    platform: str = "instagram"


class PublishRequest(BaseModel):
    post_id: int


class ComplianceRequest(BaseModel):
    post_id: int


# ─── Webhook: Generate content ───────────────────────────────────────────


@router.post("/generate")
async def webhook_generate(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_api_key),
):
    """n8n webhook: trigger content generation for a character."""
    if body.character_id:
        character = db.query(Character).filter(Character.id == body.character_id).first()
    else:
        character = db.query(Character).filter(Character.is_active.is_(True)).first()

    if not character:
        raise HTTPException(status_code=404, detail="No active character found")

    from services.content_strategy import generate_weekly_calendar

    calendar = await generate_weekly_calendar(character=character, days=body.count)

    created_ids = []
    from ..models import ContentCategory, ContentType, Platform

    try:
        platform = Platform(body.platform)
    except ValueError:
        platform = Platform.INSTAGRAM

    for day in calendar:
        for post_data in day.get("posts", []):
            cat = post_data.get("category", "workout")
            ctype = post_data.get("content_type", "photo")

            try:
                category = ContentCategory(cat)
            except ValueError:
                category = ContentCategory.WORKOUT
            try:
                content_type = ContentType(ctype)
            except ValueError:
                content_type = ContentType.PHOTO

            post = Post(
                character_id=character.id,
                content_type=content_type,
                category=category,
                platform=platform,
                status=PostStatus.DRAFT,
                image_prompt_used=post_data.get("scene", ""),
                caption_ru=post_data.get("description_ru", ""),
                caption_en=post_data.get("description_en", ""),
            )
            db.add(post)
            db.flush()
            created_ids.append(post.id)

    db.commit()
    logger.info("Webhook: generated %d posts for character %d", len(created_ids), character.id)
    return {"status": "ok", "generated_count": len(created_ids), "post_ids": created_ids}


# ─── Webhook: Publish post ───────────────────────────────────────────────


@router.post("/publish")
async def webhook_publish(
    body: PublishRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_api_key),
):
    """n8n webhook: publish a specific post immediately."""
    post = db.query(Post).filter(Post.id == body.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.status not in (PostStatus.APPROVED, PostStatus.SCHEDULED, PostStatus.GENERATED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish post in {post.status.value} state",
        )

    from services.publisher import get_publisher_registry
    from ..models import Platform

    registry = get_publisher_registry()
    if not registry.has(post.platform):
        raise HTTPException(status_code=400, detail=f"No publisher for {post.platform.value}")

    publisher = registry.get(post.platform)

    caption_parts = []
    if post.caption_ru:
        caption_parts.append(post.caption_ru)
    if post.caption_en:
        caption_parts.append("")
        caption_parts.append(post.caption_en)
    if post.hashtags:
        caption_parts.append("")
        caption_parts.append(post.hashtags)
    caption = "\n".join(caption_parts)

    try:
        if post.video_path and post.content_type.value == "reel":
            media_id = await publisher.publish_video(post.video_path, caption, post.thumbnail_path)
        elif post.image_path:
            media_id = await publisher.publish_photo(post.image_path, caption)
        else:
            raise HTTPException(status_code=400, detail="Post has no media")

        if post.platform == Platform.INSTAGRAM:
            post.instagram_media_id = media_id
        elif post.platform == Platform.TELEGRAM:
            post.telegram_message_id = media_id
        elif post.platform == Platform.VK:
            post.vk_post_id = media_id

        from datetime import datetime
        post.published_at = datetime.utcnow()
        post.status = PostStatus.PUBLISHED

        db.add(GenerationLog(
            action="webhook_publish",
            entity_type="post",
            entity_id=post.id,
            status="success",
            details=f"platform={post.platform.value}",
        ))
        db.commit()

        return {"status": "ok", "post_id": post.id, "platform": post.platform.value, "media_id": media_id}

    except Exception as e:
        post.status = PostStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Webhook: Compliance check ───────────────────────────────────────────


@router.post("/compliance")
async def webhook_compliance(
    body: ComplianceRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_api_key),
):
    """n8n webhook: run compliance check on a post."""
    post = db.query(Post).filter(Post.id == body.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    campaign = None
    # TODO: link campaigns to posts properly in future

    from services.legal_compliance import run_compliance_check
    from ..models import ComplianceLog

    result = await run_compliance_check(post, campaign=campaign)

    if result.auto_fixed and result.fixed_caption_ru:
        post.caption_ru = result.fixed_caption_ru
    if result.auto_fixed and result.fixed_caption_en:
        post.caption_en = result.fixed_caption_en
    if not result.passed:
        post.status = PostStatus.REVIEW

    log = ComplianceLog(
        post_id=post.id,
        check_level=result.check_level,
        passed=result.passed,
        violations=json.dumps(result.violations, ensure_ascii=False),
        auto_fixed=result.auto_fixed,
        iterations=result.iterations,
    )
    db.add(log)
    db.commit()

    return {
        "status": "ok",
        "passed": result.passed,
        "check_level": result.check_level,
        "violations": result.violations,
        "auto_fixed": result.auto_fixed,
    }
