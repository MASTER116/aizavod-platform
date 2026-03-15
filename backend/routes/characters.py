"""Character (persona) management routes."""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from ..admin_auth import verify_admin_token
from ..database import get_db
from ..models import Character
from ..schemas import CharacterCreate, CharacterRead, CharacterUpdate, GenerateImageRequest, GenerateImageResponse

router = APIRouter(prefix="/admin/api/characters", tags=["characters"])

_MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"


@router.get("", response_model=List[CharacterRead])
def list_characters(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    return db.query(Character).order_by(Character.id.desc()).all()


@router.post("", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
def create_character(
    body: CharacterCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    character = Character(**body.model_dump())
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@router.get("/{character_id}", response_model=CharacterRead)
def get_character(
    character_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.put("/{character_id}", response_model=CharacterRead)
def update_character(
    character_id: int,
    body: CharacterUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(character, field, value)
    db.commit()
    db.refresh(character)
    return character


@router.post("/{character_id}/upload_reference")
def upload_reference_image(
    character_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    ref_dir = _MEDIA_DIR / "reference" / str(character_id)
    ref_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = ref_dir / filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Update reference_image_urls list
    urls = json.loads(character.reference_image_urls)
    urls.append(f"/media/reference/{character_id}/{filename}")
    character.reference_image_urls = json.dumps(urls)
    db.commit()

    return {"uploaded": len(urls), "path": f"/media/reference/{character_id}/{filename}"}


@router.delete("/{character_id}/reference/{index}")
def delete_reference_image(
    character_id: int,
    index: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    urls = json.loads(character.reference_image_urls)
    if index < 0 or index >= len(urls):
        raise HTTPException(status_code=400, detail="Invalid index")

    removed_url = urls.pop(index)
    character.reference_image_urls = json.dumps(urls)
    db.commit()

    # Delete file from disk
    file_path = _MEDIA_DIR.parent / removed_url.lstrip("/")
    if file_path.exists():
        file_path.unlink()

    return {"ok": True, "remaining": len(urls)}


@router.post("/{character_id}/generate_image", response_model=GenerateImageResponse)
async def generate_character_image(
    character_id: int,
    body: GenerateImageRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_token),
):
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    from services.image_generator import generate_image

    result = await generate_image(
        character=character,
        prompt=body.prompt,
        aspect_ratio=body.aspect_ratio,
        use_lora=body.use_lora,
    )
    return result
