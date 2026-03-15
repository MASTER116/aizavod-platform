"""Long Video Pipeline — orchestrates multi-clip 65-second video generation.

Flow:
1. Generate scene descriptions for 7 clips (Claude)
2. For each clip: generate image (FLUX) -> generate video (Kling 10s)
3. Concatenate 7 clips -> 70s raw video
4. Trim to 65s
5. Mix audio (music track) if needed
6. For Instagram: split at ~32.5s -> two ~30s Reels
7. Save all paths

Cost: ~$5.18 per 65s video (7 x $0.04 image + 7 x $0.70 video)
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.models import Character

logger = logging.getLogger("aizavod.long_video_pipeline")

CLIPS_COUNT = int(os.getenv("LONG_VIDEO_CLIPS_COUNT", "7"))
CLIP_DURATION = int(os.getenv("LONG_VIDEO_CLIP_DURATION", "10"))
TARGET_DURATION = int(os.getenv("LONG_VIDEO_TARGET_DURATION", "65"))
IG_SPLIT_POINT = int(os.getenv("LONG_VIDEO_IG_SPLIT_POINT", "32"))


SCENE_BREAKDOWN_PROMPT = """Ты — сценарист и кинооператор для вирусного TikTok/Instagram видео.

Персонаж: {name}
Описание персонажа: {character_description}
Тема видео: {video_concept}
Категория: {category}
Длительность: {target_duration} секунд ({clips_count} клипов по {clip_duration} секунд)

Trending camera angles: {camera_angles}
Trending format: {trending_format}
Hook text (первые 3 секунды): {hook_text}

Создай последовательность из {clips_count} клипов для непрерывного {target_duration}-секундного видео.

ПРАВИЛА НЕПРЕРЫВНОСТИ:
- Одна и та же одежда на протяжении всего видео (outfit consistency)
- Одна и та же локация или логичная смена сцен (outdoor -> indoor gym)
- Прогрессивное повествование: клипы 1-2 = hook, 3-5 = основной контент, 6-7 = кульминация + CTA
- Клип 1 ВСЕГДА начинается с hook — зритель должен остановить скролл за 1-3 секунды
- Каждый клип должен органично вытекать из предыдущего

OUTFIT для всего видео: {outfit}
ЛОКАЦИЯ: {location}

Для каждого клипа укажи:
1. Описание сцены (на АНГЛИЙСКОМ, для FLUX image generation)
2. Camera angle из trending angles
3. Motion prompt (на АНГЛИЙСКОМ, для Kling I2V)
4. Text overlay (короткая фраза поверх видео)
5. Narrative role (hook/content/buildup/cta)

Ответь ТОЛЬКО в формате JSON:
{{
  "outfit": "конкретное описание одежды (для consistency)",
  "location": "конкретная локация",
  "clips": [
    {{
      "clip_num": 1,
      "narrative_role": "hook",
      "scene_description": "...",
      "camera_angle": "low angle wide shot",
      "motion_prompt": "...",
      "text_overlay": "...",
      "transition_note": "..."
    }}
  ],
  "ig_split_point_sec": 32,
  "ig_part1_hook": "...",
  "ig_part2_hook": "..."
}}"""


@dataclass
class LongVideoResult:
    tiktok_video_path: str
    ig_part1_path: str
    ig_part2_path: str
    thumbnail_path: str
    total_cost_usd: float
    clip_paths: list[str] = field(default_factory=list)
    scene_data: dict = field(default_factory=dict)
    tiktok_sound_id: str | None = None
    ig_sound_id: str | None = None


def _get_client() -> AsyncAnthropic:
    cfg = get_anthropic_config()
    return AsyncAnthropic(api_key=cfg.api_key)


async def generate_long_video(
    character: Character,
    concept: dict,
    trend_context: dict | None = None,
) -> LongVideoResult:
    """Orchestrate full 65s video generation.

    Args:
        character: Active Character DB instance.
        concept: Dict with keys: hook_text, category, description_en, motion_prompt, etc.
        trend_context: Dict with trending_formats and camera_angles from trend_analyzer.

    Steps:
        1. _generate_scene_breakdown() -> 7 clip descriptions
        2. For each clip: generate_image() -> generate_reel() -> append to clips
        3. concatenate_clips() -> raw 70s
        4. trim_video() -> 65s TikTok
        5. Music: handled by caller or select_music_for_platform
        6. split_video() -> 2 x ~30s IG Reels
    """
    from services.image_generator import generate_image
    from services.video_generator import generate_reel
    from services.video_processor import (
        concatenate_clips,
        trim_video,
        split_video,
        extract_thumbnail,
    )

    # Step 1: Scene breakdown
    scene_data = await _generate_scene_breakdown(character, concept, trend_context)
    clips_desc = scene_data.get("clips", [])

    if not clips_desc:
        raise RuntimeError("Claude returned empty clips list")

    total_cost = 0.0
    clip_video_paths: list[str] = []

    # Step 2: Generate each clip sequentially (preserve consistency)
    for i, clip in enumerate(clips_desc):
        logger.info("Generating clip %d/%d: %s", i + 1, len(clips_desc), clip.get("narrative_role", ""))

        # Generate image
        scene_desc = clip.get("scene_description", "")
        camera_angle = clip.get("camera_angle", "medium shot")
        full_prompt = f"{scene_desc}. Camera angle: {camera_angle}."

        img_result = await generate_image(
            character=character,
            user_prompt=full_prompt,
            aspect_ratio="9:16",
        )
        total_cost += img_result.cost_usd

        # Generate video from image
        motion = clip.get("motion_prompt", "Slow cinematic movement")
        vid_result = await generate_reel(
            image_path=img_result.image_path,
            motion_prompt=motion,
            duration=CLIP_DURATION,
            aspect_ratio="9:16",
        )
        total_cost += vid_result.cost_usd
        clip_video_paths.append(vid_result.video_path)

    # Step 3: Concatenate all clips
    raw_video = await concatenate_clips(clip_video_paths)

    # Step 4: Trim to target duration
    tiktok_video = await trim_video(raw_video, duration_seconds=float(TARGET_DURATION))

    # Step 5: Extract thumbnail
    thumbnail = await extract_thumbnail(tiktok_video, at_seconds=0.5)

    # Step 6: Split for IG
    ig_split = scene_data.get("ig_split_point_sec", IG_SPLIT_POINT)
    ig_part1, ig_part2 = await split_video(tiktok_video, split_at_seconds=float(ig_split))

    logger.info(
        "Long video generated: %d clips, cost=$%.2f, TT=%s, IG1=%s, IG2=%s",
        len(clips_desc), total_cost,
        tiktok_video, ig_part1, ig_part2,
    )

    return LongVideoResult(
        tiktok_video_path=tiktok_video,
        ig_part1_path=ig_part1,
        ig_part2_path=ig_part2,
        thumbnail_path=thumbnail,
        total_cost_usd=total_cost,
        clip_paths=clip_video_paths,
        scene_data=scene_data,
    )


async def _generate_scene_breakdown(
    character: Character,
    concept: dict,
    trend_context: dict | None,
) -> dict:
    """Call Claude to generate multi-clip scene breakdown."""
    cfg = get_anthropic_config()
    client = _get_client()

    # Build camera angles text from trends
    camera_angles_text = "low angle, close-up, overhead, tracking shot"
    trending_format_text = "POV workout"

    if trend_context:
        formats = trend_context.get("trending_formats", [])
        if formats:
            camera_angles_text = ", ".join(
                f.get("camera_angle", "medium shot") for f in formats[:4]
            )
            trending_format_text = formats[0].get("format", "POV workout")

    prompt = SCENE_BREAKDOWN_PROMPT.format(
        name=character.name,
        character_description=getattr(character, "niche_description", character.niche),
        video_concept=concept.get("description_en", concept.get("scene_description", "")),
        category=concept.get("category", "workout"),
        target_duration=TARGET_DURATION,
        clips_count=CLIPS_COUNT,
        clip_duration=CLIP_DURATION,
        camera_angles=camera_angles_text,
        trending_format=trending_format_text,
        hook_text=concept.get("hook_text", ""),
        outfit=concept.get("outfit", "athletic outfit, sports bra and leggings"),
        location=concept.get("setting", concept.get("location", "modern gym")),
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = message.content[0].text.strip()

    # Parse JSON
    try:
        if "```" in raw_text:
            start = raw_text.index("{")
            end = raw_text.rindex("}") + 1
            raw_text = raw_text[start:end]
        return json.loads(raw_text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse scene breakdown JSON: %s\nRaw: %s", e, raw_text[:500])
        # Fallback: generate a basic 7-clip breakdown
        return _fallback_scene_breakdown(concept)


def _fallback_scene_breakdown(concept: dict) -> dict:
    """Generate a basic fallback breakdown if Claude parsing fails."""
    hook = concept.get("hook_text", "Watch this transformation")
    roles = ["hook", "hook", "content", "content", "content", "buildup", "cta"]
    angles = ["low angle wide", "close-up face", "medium shot", "tracking shot",
              "overhead", "low angle", "close-up face"]
    clips = []
    for i in range(CLIPS_COUNT):
        clips.append({
            "clip_num": i + 1,
            "narrative_role": roles[i],
            "scene_description": f"Fit woman in athletic outfit, gym setting, {roles[i]} scene",
            "camera_angle": angles[i],
            "motion_prompt": "Smooth cinematic movement, gentle motion",
            "text_overlay": hook if i == 0 else "",
            "transition_note": "smooth transition",
        })
    return {
        "outfit": "black sports bra, gray leggings",
        "location": "modern gym",
        "clips": clips,
        "ig_split_point_sec": IG_SPLIT_POINT,
        "ig_part1_hook": hook,
        "ig_part2_hook": "Part 2",
    }
