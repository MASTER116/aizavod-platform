"""Post management routes: CRUD, generation, approval, scheduling."""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import Post, Character, ContentTemplate, PostStatus, GenerationLog, ComplianceLog, Campaign
from ..schemas import PostCreate, PostRead, PostUpdate, ComplianceLogRead

router = APIRouter(prefix="/admin/api/posts", tags=["posts"])


@router.get("", response_model=List[PostRead])
def list_posts(
    status_filter: Optional[PostStatus] = Query(default=None, alias="status"),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    q = db.query(Post)
    if status_filter:
        q = q.filter(Post.status == status_filter)
    if category:
        q = q.filter(Post.category == category)
    return q.order_by(Post.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(
    body: PostCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    character = db.query(Character).filter(Character.id == body.character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    post = Post(**body.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/{post_id}", response_model=PostRead)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.put("/{post_id}", response_model=PostRead)
def update_post(
    post_id: int,
    body: PostUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return {"deleted": post_id}


@router.post("/{post_id}/generate", response_model=PostRead)
async def generate_post_image(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    """Generate image and caption for a post."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    character = db.query(Character).filter(Character.id == post.character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    post.status = PostStatus.GENERATING
    db.commit()

    start = time.time()

    try:
        # Build prompt from template or use default
        prompt = "fitness photo, Instagram style"
        if post.template_id:
            template = db.query(ContentTemplate).filter(ContentTemplate.id == post.template_id).first()
            if template and template.image_prompt_template:
                prompt = template.image_prompt_template

        # Generate image
        from services.image_generator import generate_image

        result = await generate_image(
            character=character,
            prompt=prompt,
            aspect_ratio="4:5",
        )
        post.image_path = result.image_path
        post.image_prompt_used = prompt
        post.replicate_prediction_id = result.prediction_id
        post.generation_cost_usd = result.cost_usd
        post.generation_time_seconds = result.duration_seconds

        # Generate caption
        from services.caption_generator import generate_caption

        captions = await generate_caption(
            character=character,
            category=post.category,
            description=prompt,
        )
        post.caption_ru = captions.get("caption_ru", "")
        post.caption_en = captions.get("caption_en", "")

        # Generate hashtags
        from services.hashtag_optimizer import get_hashtags

        post.hashtags = get_hashtags(post.category)

        post.status = PostStatus.GENERATED
        duration = time.time() - start

        # Log generation
        db.add(GenerationLog(
            action="generate_post",
            entity_type="post",
            entity_id=post.id,
            status="success",
            cost_usd=result.cost_usd,
            duration_seconds=duration,
        ))

    except Exception as e:
        post.status = PostStatus.FAILED
        db.add(GenerationLog(
            action="generate_post",
            entity_type="post",
            entity_id=post.id,
            status="failure",
            details=str(e),
            duration_seconds=time.time() - start,
        ))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/approve", response_model=PostRead)
def approve_post(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status not in (PostStatus.GENERATED, PostStatus.REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot approve post in {post.status} state")
    post.status = PostStatus.APPROVED
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/reject", response_model=PostRead)
def reject_post(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = PostStatus.DRAFT
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/schedule", response_model=PostRead)
def schedule_post(
    post_id: int,
    scheduled_at: datetime = Query(...),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status not in (PostStatus.APPROVED, PostStatus.GENERATED):
        raise HTTPException(status_code=400, detail=f"Cannot schedule post in {post.status} state")
    post.scheduled_at = scheduled_at
    post.status = PostStatus.SCHEDULED
    db.commit()
    db.refresh(post)
    return post


@router.post("/generate_batch")
async def generate_batch(
    character_id: Optional[int] = Query(default=None),
    count: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    """Generate a batch of posts from the content calendar."""
    if character_id:
        character = db.query(Character).filter(Character.id == character_id).first()
    else:
        character = db.query(Character).filter(Character.is_active.is_(True)).first()

    if not character:
        raise HTTPException(status_code=404, detail="No active character found")

    # Generate calendar first
    from services.content_strategy import generate_weekly_calendar

    calendar = await generate_weekly_calendar(character=character, days=count)

    created = 0
    for day in calendar:
        for post_data in day.get("posts", []):
            from backend.models import ContentCategory, ContentType

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
                status=PostStatus.DRAFT,
                image_prompt_used=post_data.get("scene", ""),
                caption_ru=post_data.get("description_ru", ""),
                caption_en=post_data.get("description_en", ""),
            )
            db.add(post)
            created += 1

    db.commit()
    return {"generated": created}


@router.post("/{post_id}/compliance_check", response_model=ComplianceLogRead)
async def compliance_check(
    post_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    """Run compliance check on a post."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Find associated campaign (if any)
    campaign = db.query(Campaign).filter(Campaign.id == post_id).first()

    from services.legal_compliance import run_compliance_check

    result = await run_compliance_check(post, campaign=campaign)

    # Apply auto-fixed captions
    if result.auto_fixed and result.fixed_caption_ru:
        post.caption_ru = result.fixed_caption_ru
    if result.auto_fixed and result.fixed_caption_en:
        post.caption_en = result.fixed_caption_en

    # If compliance failed → set to REVIEW
    if not result.passed:
        post.status = PostStatus.REVIEW

    # Log the check
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
    db.refresh(log)
    return log
