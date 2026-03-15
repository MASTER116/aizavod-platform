"""Trend Analyzer — fetches real trend data from TikTok + IG, summarizes with Claude.

Data sources:
- TikTok: TikTokTrendReader (trending sounds, hashtags, video formats)
- Instagram: instagrapi reels by hashtag (IG trending sounds via reel music info)
- Claude: Extracts camera techniques + cinematography styles from raw data

Outputs:
- TrendSnapshot saved to DB
- trend_summary string ready for injection into viral_engine, content_strategy, etc.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.models import Platform, TrendSnapshot

logger = logging.getLogger("aizavod.trend_analyzer")


TREND_ANALYSIS_PROMPT = """Ты — аналитик трендов для фитнес/лайфстайл контента.

Свежие данные с TikTok и Instagram:

=== ТРЕНДЫ TIKTOK ===
Топ звуков: {tiktok_sounds}
Топ хэштегов: {tiktok_hashtags}
Топ видео (описания): {tiktok_video_descriptions}

=== ТРЕНДЫ INSTAGRAM ===
Топ звуков из Reels: {ig_sounds}
Топ хэштегов: {ig_hashtags}

=== ЗАДАЧА ===
Проанализируй данные и выдели:

1. ФОРМАТЫ ВИДЕО — какие типы роликов сейчас вирусятся?
   (POV, day-in-life, tutorial, before/after, challenge, etc.)

2. ОПЕРАТОРСКИЕ ПРИЁМЫ — какие camera angles и cinematography styles в тренде?
   (low angle, close-up face, overhead, tracking shot, handheld, dolly, etc.)

3. ТЕМЫ — какие нарративы/темы набирают силу в фитнес нише?

4. МУЗЫКА — какие жанры/стили музыки сейчас актуальны?

5. ХУКИ — какие verbal/visual hooks сейчас работают?

Ответь ТОЛЬКО в формате JSON:
{{
  "trending_formats": [
    {{
      "format": "POV workout",
      "camera_angle": "low angle wide shot",
      "cinematography": "handheld shaky, intimate feel",
      "description": "От первого лица — камера следует за упражнением",
      "fitness_niche_fit": 0.95,
      "example_count": 12
    }}
  ],
  "trending_themes": [
    {{"theme": "morning routine 5am", "velocity": 2.1, "description": "..."}}
  ],
  "trending_hooks": ["hook text 1", "hook text 2"],
  "music_mood": "energetic trap beats, 140 BPM, workout bangers",
  "ig_sound_recommendations": ["sound_id_1", "sound_id_2"],
  "content_ideas": [
    {{"title": "...", "format": "...", "why_trending": "..."}}
  ],
  "trend_summary": "Краткое резюме трендов (3-4 предложения) для использования в промптах"
}}"""


def _get_client() -> AsyncAnthropic:
    cfg = get_anthropic_config()
    return AsyncAnthropic(api_key=cfg.api_key)


async def fetch_and_analyze_trends(
    niche: str = "fitness",
    platforms: list[str] | None = None,
) -> TrendSnapshot:
    """Main entry point: fetch trends from all platforms, analyze with Claude, save to DB.

    Args:
        niche: Content niche for hashtag filtering.
        platforms: Platforms to fetch from (defaults to ["tiktok", "instagram"]).

    Returns:
        Saved TrendSnapshot instance.
    """
    platforms = platforms or ["tiktok", "instagram"]

    # ── Gather raw data ──
    tiktok_sounds: list[dict] = []
    tiktok_hashtags: list[dict] = []
    tiktok_videos: list[dict] = []
    ig_sounds: list[dict] = []
    ig_hashtags: list[str] = []

    if "tiktok" in platforms:
        try:
            from services.tiktok_client import get_tiktok_trend_reader
            reader = get_tiktok_trend_reader()
            tiktok_sounds = await reader.get_trending_sounds(count=20)
            tiktok_hashtags = await reader.get_trending_hashtags(niche=niche, count=30)
            tiktok_videos = await reader.get_trending_videos(hashtag=niche, count=20)
        except Exception as e:
            logger.warning("TikTok trend fetch failed: %s", e)

    if "instagram" in platforms:
        try:
            from services.instagram_client import get_instagram_client
            ig_client = get_instagram_client()
            ig_sounds = await ig_client.get_trending_reels_sounds(count=20)
        except Exception as e:
            logger.warning("IG trend fetch failed: %s", e)

    # ── Prepare video descriptions for Claude ──
    video_descs = [
        f"{v.get('description', '')[:100]} (views: {v.get('view_count', 0)}, music: {v.get('music_title', '')})"
        for v in tiktok_videos[:15]
    ]

    # ── Ask Claude to analyze ──
    cfg = get_anthropic_config()
    client = _get_client()

    prompt = TREND_ANALYSIS_PROMPT.format(
        tiktok_sounds=json.dumps(tiktok_sounds[:10], ensure_ascii=False)[:2000],
        tiktok_hashtags=json.dumps(tiktok_hashtags[:15], ensure_ascii=False)[:2000],
        tiktok_video_descriptions="\n".join(video_descs)[:3000],
        ig_sounds=json.dumps(ig_sounds[:10], ensure_ascii=False)[:2000],
        ig_hashtags=json.dumps(ig_hashtags[:10], ensure_ascii=False)[:1000],
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = message.content[0].text.strip()

    # Parse JSON from Claude response
    try:
        # Handle markdown code blocks
        if "```" in raw_text:
            start = raw_text.index("{")
            end = raw_text.rindex("}") + 1
            raw_text = raw_text[start:end]
        analysis = json.loads(raw_text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse trend analysis JSON: %s", e)
        analysis = {
            "trending_formats": [],
            "trending_themes": [],
            "trending_hooks": [],
            "music_mood": "",
            "ig_sound_recommendations": [],
            "content_ideas": [],
            "trend_summary": "Trend analysis parsing failed. Using previous data.",
        }

    # ── Save to DB ──
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        snapshot = TrendSnapshot(
            platform=Platform.TIKTOK,
            snapshot_date=date.today(),
            trending_sounds=json.dumps(tiktok_sounds, ensure_ascii=False),
            trending_hashtags=json.dumps(
                tiktok_hashtags + [{"hashtag": h} for h in ig_hashtags],
                ensure_ascii=False,
            ),
            trending_formats=json.dumps(
                analysis.get("trending_formats", []), ensure_ascii=False,
            ),
            trending_themes=json.dumps(
                analysis.get("trending_themes", []), ensure_ascii=False,
            ),
            ig_trending_sound_ids=json.dumps(
                analysis.get("ig_sound_recommendations", []), ensure_ascii=False,
            ),
            trend_summary=analysis.get("trend_summary", ""),
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        logger.info(
            "Trend analysis complete: snapshot_id=%d, formats=%d, summary=%s...",
            snapshot.id,
            len(analysis.get("trending_formats", [])),
            snapshot.trend_summary[:80],
        )
        return snapshot
    finally:
        db.close()


async def get_latest_trend_summary(platform: Platform | None = None) -> str:
    """Get the most recent trend_summary string for injection into prompts.

    Falls back to static description if no snapshot exists.
    """
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        query = db.query(TrendSnapshot).order_by(TrendSnapshot.created_at.desc())
        if platform:
            query = query.filter(TrendSnapshot.platform == platform)
        snapshot = query.first()

        if snapshot and snapshot.trend_summary:
            return snapshot.trend_summary

        return (
            "Current trends: gym POV, day-in-life routines, before/after transformations, "
            "morning routine 5am club, protein recipes, workout challenges. "
            "Camera angles: low angle wide, handheld POV, close-up face reactions. "
            "Music: energetic trap beats, motivational instrumental."
        )
    finally:
        db.close()


async def get_trending_camera_angles() -> list[dict]:
    """Returns trending_formats from latest snapshot.

    Used by long_video_pipeline to build per-clip motion prompts.
    """
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        snapshot = (
            db.query(TrendSnapshot)
            .order_by(TrendSnapshot.created_at.desc())
            .first()
        )
        if snapshot:
            try:
                formats = json.loads(snapshot.trending_formats)
                return [
                    {
                        "camera_angle": f.get("camera_angle", "medium shot"),
                        "cinematography": f.get("cinematography", "stable"),
                        "format": f.get("format", ""),
                        "fitness_niche_fit": f.get("fitness_niche_fit", 0.5),
                    }
                    for f in formats
                ]
            except json.JSONDecodeError:
                pass

        # Static fallback
        return [
            {"camera_angle": "low angle wide shot", "cinematography": "handheld shaky", "format": "POV workout", "fitness_niche_fit": 0.95},
            {"camera_angle": "close-up face", "cinematography": "stable, shallow DOF", "format": "reaction / emotion", "fitness_niche_fit": 0.85},
            {"camera_angle": "overhead top-down", "cinematography": "static tripod", "format": "food prep / layout", "fitness_niche_fit": 0.70},
            {"camera_angle": "medium tracking shot", "cinematography": "slow dolly", "format": "walking / gym tour", "fitness_niche_fit": 0.80},
        ]
    finally:
        db.close()


async def get_trending_sound_for_ig() -> dict | None:
    """Returns the top trending IG sound from latest snapshot."""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        snapshot = (
            db.query(TrendSnapshot)
            .order_by(TrendSnapshot.created_at.desc())
            .first()
        )
        if snapshot:
            try:
                sound_ids = json.loads(snapshot.ig_trending_sound_ids)
                if sound_ids:
                    return {"sound_id": sound_ids[0], "title": "", "author": ""}
            except json.JSONDecodeError:
                pass
        return None
    finally:
        db.close()


async def get_tiktok_sound_recommendation() -> dict | None:
    """Returns the top trending TikTok sound + its copyright risk."""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        snapshot = (
            db.query(TrendSnapshot)
            .order_by(TrendSnapshot.created_at.desc())
            .first()
        )
        if not snapshot:
            return None

        try:
            sounds = json.loads(snapshot.trending_sounds)
        except json.JSONDecodeError:
            return None

        if not sounds:
            return None

        top_sound = sounds[0]

        # Check copyright
        try:
            from services.tiktok_client import get_tiktok_trend_reader
            reader = get_tiktok_trend_reader()
            copyright_info = await reader.check_sound_copyright(top_sound.get("sound_id", ""))
        except Exception:
            copyright_info = {"risk_level": "risky"}

        return {
            "sound_id": top_sound.get("sound_id", ""),
            "title": top_sound.get("title", ""),
            "author": top_sound.get("author", ""),
            "risk_level": copyright_info.get("risk_level", "risky"),
            "style_description": f"Style similar to: {top_sound.get('title', 'workout beat')}, "
                                 f"by {top_sound.get('author', 'unknown')}",
        }
    finally:
        db.close()
