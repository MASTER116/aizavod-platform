"""Character management service."""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models import Character

logger = logging.getLogger("aizavod.character_manager")


def get_active_character(db: Session) -> Optional[Character]:
    """Return the first active character (primary persona)."""
    return db.query(Character).filter(Character.is_active.is_(True)).first()


def get_character_prompt_context(character: Character) -> dict:
    """Build a context dict for prompt templates from character data."""
    return {
        "name": character.name,
        "age_range": character.age_range,
        "ethnicity": character.ethnicity,
        "hair_color": character.hair_color,
        "hair_style": character.hair_style,
        "body_type": character.body_type,
        "height": character.height_description,
        "features": character.distinguishing_features or "",
        "personality": json.loads(character.personality_traits),
        "tone": character.tone_of_voice,
        "topics": json.loads(character.favorite_topics),
        "emoji_style": character.emoji_style,
        "bio_ru": character.bio_ru,
        "bio_en": character.bio_en,
    }


def get_reference_images(character: Character) -> list[str]:
    """Return list of reference image URLs for the character."""
    return json.loads(character.reference_image_urls)
