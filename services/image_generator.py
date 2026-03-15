"""Image generation service using fal.ai API (FLUX Kontext Pro).

FLUX Kontext Pro features:
- Built-in character consistency via reference image (no LoRA needed)
- Same face/body preserved across generations
- $0.04/image on fal.ai
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path

import httpx
import fal_client

from backend.config import get_fal_ai_config
from backend.models import Character

logger = logging.getLogger("aizavod.image_generator")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"


class GenerationResult:
    def __init__(
        self,
        image_path: str,
        prediction_id: str,
        cost_usd: float,
        duration_seconds: float,
    ):
        self.image_path = image_path
        self.prediction_id = prediction_id
        self.cost_usd = cost_usd
        self.duration_seconds = duration_seconds


def _build_prompt(character: Character, user_prompt: str) -> str:
    """Build a FLUX Kontext Pro prompt from character attributes."""
    parts = [
        f"A photo of a {character.age_range} year old {character.ethnicity} woman",
        f"with {character.hair_color} {character.hair_style} hair",
        f"and {character.body_type} body type",
    ]
    if character.distinguishing_features:
        parts.append(character.distinguishing_features)
    parts.append(f". {user_prompt}")
    parts.append(
        ". Ultra realistic, high quality, Instagram style photography, "
        "professional DSLR photo, natural skin texture, natural bokeh"
    )
    return ", ".join(parts)


def _get_reference_image_url(character: Character) -> str | None:
    """Get the primary reference image URL for character consistency."""
    if character.reference_image_base64:
        return f"data:image/jpeg;base64,{character.reference_image_base64}"
    reference_urls = json.loads(character.reference_image_urls)
    return reference_urls[0] if reference_urls else None


async def generate_image(
    character: Character,
    prompt: str,
    aspect_ratio: str = "4:5",
    **kwargs,
) -> GenerationResult:
    """Generate an image using FLUX Kontext Pro on fal.ai.

    Character consistency is achieved through the reference image —
    same face and body are preserved, only outfit and location change.
    """
    cfg = get_fal_ai_config()
    if not cfg.api_key:
        raise RuntimeError("FAL_API_KEY not configured")

    os.environ["FAL_KEY"] = cfg.api_key

    full_prompt = _build_prompt(character, prompt)
    reference_url = _get_reference_image_url(character)
    start_time = time.time()

    input_params = {
        "prompt": full_prompt,
        "num_images": 1,
        "output_format": "jpeg",
        "guidance_scale": 3.5,
    }

    if reference_url:
        input_params["image_url"] = reference_url

    result = await fal_client.run_async(
        cfg.flux_model,
        arguments=input_params,
    )

    duration = time.time() - start_time

    # Download the generated image
    images = result.get("images", [])
    if not images:
        raise RuntimeError("No images returned from fal.ai")

    image_url = images[0].get("url", "")
    gen_dir = _MEDIA_DIR / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    file_path = gen_dir / filename

    async with httpx.AsyncClient() as http:
        resp = await http.get(image_url)
        resp.raise_for_status()
        file_path.write_bytes(resp.content)

    logger.info(
        "Generated image: %s (%.1fs, prompt=%s...)",
        filename,
        duration,
        full_prompt[:60],
    )

    return GenerationResult(
        image_path=f"/media/generated/{filename}",
        prediction_id=result.get("request_id", "unknown"),
        cost_usd=0.04,
        duration_seconds=duration,
    )
