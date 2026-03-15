"""Background music generation service using Suno API.

Suno v4.5:
- Professional quality complete tracks
- 90+ second songs in under 60 seconds
- Free tier: 50 credits/day (~10 songs)
- Pro ($10/mo): 500 songs with commercial rights
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

import httpx

from backend.config import get_suno_config

logger = logging.getLogger("aizavod.music_generator")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"

SUNO_BASE_URL = "https://studio-api.suno.ai"


class MusicResult:
    def __init__(
        self,
        audio_path: str,
        title: str,
        duration_seconds: float,
        cost_usd: float,
        song_id: str,
    ):
        self.audio_path = audio_path
        self.title = title
        self.duration_seconds = duration_seconds
        self.cost_usd = cost_usd
        self.song_id = song_id


# Pre-defined style templates for fitness/lifestyle Reels
MUSIC_STYLES = {
    "workout": {
        "prompt": "Energetic electronic workout music, motivational, 120-140 BPM, powerful drops",
        "tags": "electronic, edm, workout, energetic",
    },
    "motivation": {
        "prompt": "Inspiring cinematic background music, uplifting piano and strings, motivational",
        "tags": "cinematic, inspiring, piano, motivational",
    },
    "lifestyle": {
        "prompt": "Chill lo-fi hip hop beat, relaxed lifestyle vibes, soft bass, warm pads",
        "tags": "lofi, chill, lifestyle, relaxed",
    },
    "yoga": {
        "prompt": "Peaceful ambient meditation music, gentle nature sounds, calming atmosphere",
        "tags": "ambient, meditation, calm, peaceful",
    },
    "nutrition": {
        "prompt": "Light acoustic pop background music, happy cooking vibes, upbeat guitar",
        "tags": "acoustic, pop, happy, cooking",
    },
    "transformation": {
        "prompt": "Epic motivational cinematic music, building intensity, dramatic reveal moment",
        "tags": "cinematic, epic, dramatic, transformation",
    },
    "outfit": {
        "prompt": "Trendy pop fashion runway music, stylish beat, confident vibe",
        "tags": "pop, fashion, trendy, confident",
    },
}


async def generate_music(
    style: str = "lifestyle",
    custom_prompt: str | None = None,
    duration_seconds: int = 30,
    instrumental: bool = True,
) -> MusicResult:
    """Generate background music track for Reels.

    Args:
        style: One of MUSIC_STYLES keys or "custom"
        custom_prompt: Custom description (overrides style prompt)
        duration_seconds: Target duration (15, 30, 60, 90)
        instrumental: If True, generates instrumental only (no vocals)

    Returns:
        MusicResult with path to generated audio file
    """
    cfg = get_suno_config()
    if not cfg.api_key:
        raise RuntimeError("SUNO_API_KEY not configured — get one at suno.com")

    style_config = MUSIC_STYLES.get(style, MUSIC_STYLES["lifestyle"])
    prompt = custom_prompt or style_config["prompt"]
    tags = style_config.get("tags", "")

    if instrumental:
        prompt = f"[Instrumental] {prompt}"

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    # Generate music
    payload = {
        "prompt": prompt,
        "tags": tags,
        "make_instrumental": instrumental,
    }

    start_time = time.time()

    async with httpx.AsyncClient() as client:
        # Start generation
        resp = await client.post(
            f"{SUNO_BASE_URL}/api/generate/v2/",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        gen_data = resp.json()

        clips = gen_data.get("clips", [])
        if not clips:
            raise RuntimeError("Suno returned no clips")

        clip = clips[0]
        song_id = clip.get("id", "")

        # Poll for completion (Suno generates async)
        audio_url = None
        for _ in range(60):  # Max 5 minutes polling
            status_resp = await client.get(
                f"{SUNO_BASE_URL}/api/feed/{song_id}",
                headers=headers,
                timeout=15,
            )
            status_resp.raise_for_status()
            status_data = status_resp.json()

            feed_item = status_data[0] if isinstance(status_data, list) else status_data
            status = feed_item.get("status", "")

            if status == "complete":
                audio_url = feed_item.get("audio_url", "")
                break
            elif status == "error":
                raise RuntimeError(f"Suno generation failed: {feed_item}")

            import asyncio
            await asyncio.sleep(5)

        if not audio_url:
            raise RuntimeError("Suno generation timed out")

        # Download audio
        gen_dir = _MEDIA_DIR / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        filename = f"music_{uuid.uuid4().hex}.mp3"
        file_path = gen_dir / filename

        audio_resp = await client.get(audio_url, timeout=60)
        audio_resp.raise_for_status()
        file_path.write_bytes(audio_resp.content)

    elapsed = time.time() - start_time

    # Free tier = $0, Pro = ~$0.02/song
    estimated_cost = 0.0 if cfg.is_free_tier else 0.02

    title = clip.get("title", f"{style}_track")

    logger.info(
        "Generated music: %s (%.1fs gen, style=%s, cost=$%.2f)",
        filename, elapsed, style, estimated_cost,
    )

    return MusicResult(
        audio_path=f"/media/generated/{filename}",
        title=title,
        duration_seconds=duration_seconds,
        cost_usd=estimated_cost,
        song_id=song_id,
    )


async def generate_music_for_trend(
    trend_style: str,
    duration_seconds: int = 70,
    ref_title: str | None = None,
    ref_author: str | None = None,
) -> MusicResult:
    """Generate an original instrumental track inspired by a trending sound.

    Used when a trending TikTok sound has copyright risk — we create a Suno
    remake that captures the vibe without copying the original.

    Args:
        trend_style: Style description from trend_analyzer (e.g. "dark trap, energetic drops").
        duration_seconds: Target duration (70s for 65s video with fade).
        ref_title: Title of the original trending sound (for style reference only).
        ref_author: Author of the original trending sound.
    """
    reference = ""
    if ref_title:
        reference = f" Inspired by the style/vibe of '{ref_title}'"
        if ref_author:
            reference += f" by {ref_author}"
        reference += " — but completely original composition, no sampling."

    custom_prompt = (
        f"[Instrumental] {trend_style}.{reference} "
        f"Energetic, suitable for short-form vertical video content. "
        f"Clear beat, professional mix."
    )

    return await generate_music(
        style="custom",
        custom_prompt=custom_prompt,
        duration_seconds=duration_seconds,
        instrumental=True,
    )


async def select_music_for_platform(
    platform: str,
    category: str = "workout",
    tiktok_sound: dict | None = None,
) -> dict:
    """Decide the music strategy for a given platform.

    Returns a dict describing the chosen approach:
    - approach: "ig_trending" | "tiktok_trending" | "suno_original" | "suno_generic"
    - sound_id: platform sound ID (if using trending sound)
    - music_path: path to generated audio file (if Suno)
    - cost_usd: generation cost

    Args:
        platform: "instagram" or "tiktok"
        category: Content category (used for Suno style selection)
        tiktok_sound: Dict from trend_analyzer with keys:
            sound_id, title, author, risk_level, style_description
    """
    # ─── Instagram: always use trending IG sound (metadata only) ───
    if platform == "instagram":
        try:
            from services.trend_analyzer import get_trending_sound_for_ig
            ig_sound = await get_trending_sound_for_ig()
            if ig_sound and ig_sound.get("sound_id"):
                return {
                    "approach": "ig_trending",
                    "sound_id": ig_sound["sound_id"],
                    "music_path": None,
                    "cost_usd": 0.0,
                }
        except Exception as e:
            logger.warning("Failed to get IG trending sound: %s", e)

        # Fallback: no sound (IG will use default)
        return {
            "approach": "ig_no_sound",
            "sound_id": None,
            "music_path": None,
            "cost_usd": 0.0,
        }

    # ─── TikTok: trending if safe, Suno remake if risky ───
    if platform == "tiktok" and tiktok_sound:
        risk = tiktok_sound.get("risk_level", "unknown")

        if risk == "safe":
            return {
                "approach": "tiktok_trending",
                "sound_id": tiktok_sound.get("sound_id"),
                "music_path": None,
                "cost_usd": 0.0,
            }

        # Risky or blocked — generate Suno remake
        style_desc = tiktok_sound.get("style_description", "")
        if not style_desc:
            style_config = MUSIC_STYLES.get(category, MUSIC_STYLES["lifestyle"])
            style_desc = style_config["prompt"]

        try:
            result = await generate_music_for_trend(
                trend_style=style_desc,
                duration_seconds=70,
                ref_title=tiktok_sound.get("title"),
                ref_author=tiktok_sound.get("author"),
            )
            return {
                "approach": "suno_original",
                "sound_id": None,
                "music_path": result.audio_path,
                "cost_usd": result.cost_usd,
            }
        except Exception as e:
            logger.error("Suno remake failed: %s", e)

    # ─── Fallback: generic Suno track ───
    try:
        result = await generate_music(
            style=category if category in MUSIC_STYLES else "lifestyle",
            duration_seconds=70,
            instrumental=True,
        )
        return {
            "approach": "suno_generic",
            "sound_id": None,
            "music_path": result.audio_path,
            "cost_usd": result.cost_usd,
        }
    except Exception as e:
        logger.warning("Generic Suno generation failed: %s", e)
        return {
            "approach": "no_music",
            "sound_id": None,
            "music_path": None,
            "cost_usd": 0.0,
        }


def get_available_styles() -> dict:
    """Return available music style templates."""
    return {k: v["prompt"] for k, v in MUSIC_STYLES.items()}
