"""Image post-processing: resize, filters, overlays for Instagram."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger("aizavod.post_processor")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"

# Instagram optimal dimensions
FEED_SIZE = (1080, 1350)     # 4:5
STORY_SIZE = (1080, 1920)    # 9:16
SQUARE_SIZE = (1080, 1080)   # 1:1
REEL_SIZE = (1080, 1920)     # 9:16


def _output_path(prefix: str = "processed") -> Path:
    out_dir = _MEDIA_DIR / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{prefix}_{uuid.uuid4().hex}.jpg"


def resize_for_feed(image_path: str, target_size: tuple[int, int] = FEED_SIZE) -> str:
    """Resize image to Instagram feed optimal dimensions (4:5).

    Uses center crop to fill the target ratio, then resize.
    """
    abs_path = _resolve_path(image_path)
    img = Image.open(abs_path).convert("RGB")

    # Calculate crop to match target aspect ratio
    target_ratio = target_size[0] / target_size[1]
    img_ratio = img.width / img.height

    if img_ratio > target_ratio:
        # Image is wider — crop sides
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        # Image is taller — crop top/bottom
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))

    img = img.resize(target_size, Image.LANCZOS)

    out = _output_path("feed")
    img.save(out, "JPEG", quality=95)
    logger.info("Resized for feed: %s -> %s", image_path, out.name)
    return f"/media/processed/{out.name}"


def resize_for_story(image_path: str) -> str:
    """Convert a feed image to story format (9:16) with blurred background."""
    abs_path = _resolve_path(image_path)
    img = Image.open(abs_path).convert("RGB")

    # Create blurred background
    bg = img.resize(STORY_SIZE, Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
    bg = ImageEnhance.Brightness(bg).enhance(0.5)

    # Resize original to fit within story width
    scale = STORY_SIZE[0] / img.width
    new_h = int(img.height * scale)
    img_resized = img.resize((STORY_SIZE[0], new_h), Image.LANCZOS)

    # Center paste
    y_offset = (STORY_SIZE[1] - new_h) // 2
    bg.paste(img_resized, (0, y_offset))

    out = _output_path("story")
    bg.save(out, "JPEG", quality=95)
    logger.info("Created story image: %s", out.name)
    return f"/media/processed/{out.name}"


def apply_filter(
    image_path: str,
    brightness: float = 1.05,
    contrast: float = 1.1,
    saturation: float = 1.15,
    warmth: float = 1.05,
) -> str:
    """Apply Instagram-style color adjustments."""
    abs_path = _resolve_path(image_path)
    img = Image.open(abs_path).convert("RGB")

    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(saturation)

    # Warmth: shift red channel slightly
    if warmth != 1.0:
        r, g, b = img.split()
        r = r.point(lambda x: min(255, int(x * warmth)))
        img = Image.merge("RGB", (r, g, b))

    out = _output_path("filtered")
    img.save(out, "JPEG", quality=95)
    logger.info("Applied filter to: %s", out.name)
    return f"/media/processed/{out.name}"


def _resolve_path(path: str) -> Path:
    """Resolve a media path (relative or absolute) to an absolute path."""
    if path.startswith("/media/"):
        return _MEDIA_DIR.parent / path.lstrip("/")
    p = Path(path)
    if p.is_absolute():
        return p
    return _MEDIA_DIR.parent / path
