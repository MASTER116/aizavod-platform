"""Video generation service using fal.ai API (Kling 2.6 image-to-video).

Kling 2.6 features:
- 1080p output at 30fps
- Excellent human motion and facial consistency
- Image-to-video preserves face/body from input image
- 5-10 second duration
- $0.07/second on fal.ai
"""
from __future__ import annotations

import base64
import logging
import os
import time
import uuid
from pathlib import Path

import httpx
import fal_client

from backend.config import get_fal_ai_config

logger = logging.getLogger("aizavod.video_generator")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"


class VideoResult:
    def __init__(
        self,
        video_path: str,
        thumbnail_path: str | None,
        prediction_id: str,
        cost_usd: float,
        duration_seconds: float,
    ):
        self.video_path = video_path
        self.thumbnail_path = thumbnail_path
        self.prediction_id = prediction_id
        self.cost_usd = cost_usd
        self.duration_seconds = duration_seconds


def _image_to_data_uri(abs_path: Path) -> str:
    """Convert a local image file to a base64 data URI for fal.ai."""
    raw = abs_path.read_bytes()
    b64 = base64.b64encode(raw).decode()
    suffix = abs_path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


async def generate_reel(
    image_path: str,
    motion_prompt: str = "Slow cinematic movement, camera slowly panning, gentle hair movement",
    duration: int = 5,
    aspect_ratio: str = "9:16",
) -> VideoResult:
    """Convert a generated image into an animated video for Instagram Reels.

    Uses Kling 2.6 image-to-video model on fal.ai.
    Face and body from the input image are preserved in the video.

    Args:
        image_path: Path to the source image (relative or absolute)
        motion_prompt: Description of desired motion
        duration: Video duration in seconds (5 or 10)
        aspect_ratio: Video aspect ratio (9:16 for Reels/Stories)
    """
    cfg = get_fal_ai_config()
    if not cfg.api_key:
        raise RuntimeError("FAL_API_KEY not configured")

    os.environ["FAL_KEY"] = cfg.api_key
    start_time = time.time()

    # Resolve image path
    if image_path.startswith("/media/"):
        abs_path = _MEDIA_DIR.parent / image_path.lstrip("/")
    else:
        abs_path = Path(image_path)

    if not abs_path.exists():
        raise FileNotFoundError(f"Source image not found: {abs_path}")

    image_url = _image_to_data_uri(abs_path)

    input_params = {
        "prompt": motion_prompt,
        "image_url": image_url,
        "duration": str(duration),
        "aspect_ratio": aspect_ratio,
    }

    result = await fal_client.run_async(
        cfg.kling_model,
        arguments=input_params,
    )

    elapsed = time.time() - start_time

    # Download video
    video_data = result.get("video", {})
    video_url = video_data.get("url", "")
    if not video_url:
        raise RuntimeError("No video URL returned from fal.ai")

    gen_dir = _MEDIA_DIR / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    filename = f"reel_{uuid.uuid4().hex}.mp4"
    file_path = gen_dir / filename

    async with httpx.AsyncClient() as http:
        resp = await http.get(video_url, timeout=180)
        resp.raise_for_status()
        file_path.write_bytes(resp.content)

    # Cost: Kling 2.6 on fal.ai — $0.07/second at 1080p
    estimated_cost = 0.07 * duration

    logger.info(
        "Generated reel: %s (%.1fs gen, %ds video, cost=$%.2f, prompt=%s...)",
        filename, elapsed, duration, estimated_cost, motion_prompt[:50],
    )

    return VideoResult(
        video_path=f"/media/generated/{filename}",
        thumbnail_path=image_path,
        prediction_id=result.get("request_id", "unknown"),
        cost_usd=estimated_cost,
        duration_seconds=elapsed,
    )
