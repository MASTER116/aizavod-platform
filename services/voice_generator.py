"""Voice synthesis service using Fish Audio S1 API.

Fish Audio S1:
- #1 on TTS-Arena benchmark
- 0.8% Word Error Rate
- Supports 13+ languages including Russian and English
- Voice cloning from 10 seconds of audio
- Latency under 200ms
- ~70% cheaper than ElevenLabs
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

import httpx

from backend.config import get_fish_audio_config

logger = logging.getLogger("aizavod.voice_generator")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"

FISH_AUDIO_BASE_URL = "https://api.fish.audio"


class VoiceResult:
    def __init__(
        self,
        audio_path: str,
        duration_seconds: float,
        cost_usd: float,
        characters_used: int,
    ):
        self.audio_path = audio_path
        self.duration_seconds = duration_seconds
        self.cost_usd = cost_usd
        self.characters_used = characters_used


async def generate_speech(
    text: str,
    voice_id: str | None = None,
    language: str = "ru",
    speed: float = 1.0,
) -> VoiceResult:
    """Generate speech audio from text using Fish Audio S1.

    Args:
        text: Text to convert to speech
        voice_id: Fish Audio voice ID (use custom cloned voice or preset)
        language: Language code ("ru", "en")
        speed: Speech speed multiplier (0.5-2.0)

    Returns:
        VoiceResult with path to generated audio file
    """
    cfg = get_fish_audio_config()
    if not cfg.api_key:
        raise RuntimeError("FISH_AUDIO_API_KEY not configured")

    voice_id = voice_id or cfg.default_voice_id

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "reference_id": voice_id,
        "format": "mp3",
        "mp3_bitrate": 192,
        "latency": "normal",
    }

    gen_dir = _MEDIA_DIR / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    filename = f"voice_{uuid.uuid4().hex}.mp3"
    file_path = gen_dir / filename

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FISH_AUDIO_BASE_URL}/v1/tts",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        file_path.write_bytes(resp.content)

    # Estimate cost: ~$0.015 per 1K characters
    char_count = len(text)
    estimated_cost = (char_count / 1000) * 0.015

    # Estimate audio duration: ~150 words/min for Russian, ~170 for English
    words = len(text.split())
    wpm = 150 if language == "ru" else 170
    estimated_duration = (words / wpm) * 60

    logger.info(
        "Generated speech: %s (%d chars, ~%.1fs, cost=$%.4f)",
        filename, char_count, estimated_duration, estimated_cost,
    )

    return VoiceResult(
        audio_path=f"/media/generated/{filename}",
        duration_seconds=estimated_duration,
        cost_usd=estimated_cost,
        characters_used=char_count,
    )


async def clone_voice(
    audio_path: str,
    voice_name: str,
    description: str = "",
) -> str:
    """Clone a voice from an audio sample (minimum 10 seconds).

    Args:
        audio_path: Path to the reference audio file
        voice_name: Name for the cloned voice
        description: Optional description

    Returns:
        Voice ID for use in generate_speech()
    """
    cfg = get_fish_audio_config()
    if not cfg.api_key:
        raise RuntimeError("FISH_AUDIO_API_KEY not configured")

    abs_path = Path(audio_path)
    if audio_path.startswith("/media/"):
        abs_path = _MEDIA_DIR.parent / audio_path.lstrip("/")

    if not abs_path.exists():
        raise FileNotFoundError(f"Audio file not found: {abs_path}")

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
    }

    async with httpx.AsyncClient() as client:
        with open(abs_path, "rb") as f:
            resp = await client.post(
                f"{FISH_AUDIO_BASE_URL}/model",
                headers=headers,
                data={
                    "visibility": "private",
                    "type": "tts",
                    "title": voice_name,
                    "description": description,
                },
                files={"voices": (abs_path.name, f, "audio/mpeg")},
                timeout=120,
            )
            resp.raise_for_status()

    voice_data = resp.json()
    voice_id = voice_data.get("_id", "")

    logger.info("Cloned voice: %s -> %s", voice_name, voice_id)
    return voice_id
