"""Viral Content Engine — generates high-virality content concepts.

Analyzes patterns from top-performing posts, generates viral hooks,
predicts engagement, and creates optimized content plans for Reels and Carousels.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.database import SessionLocal
from backend.models import (
    Character,
    Post,
    PostAnalytics,
    PostStatus,
    ViralContentAnalysis,
)

logger = logging.getLogger("aizavod.viral_engine")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


VIRAL_REEL_PROMPT = """Ты — эксперт по вирусному контенту в Instagram.

Персонаж: {name}, {niche_description}
Аудитория: {audience_summary}

Наши лучшие посты (по ER):
{top_posts}

Текущие тренды в нише:
{trends}

Создай концепцию ВИРУСНОГО Reel:

Требования:
- HOOK в первые 1-3 секунды (зритель должен остановить скролл)
- Длительность: 15-30 секунд (sweet spot для алгоритма)
- Loop ending — видео хочется пересмотреть
- Text overlay на экране (короткие фразы)
- CTA в конце: save/share/follow

Типы хуков (выбери лучший для данной темы):
- curiosity_gap: "Никто не верил что это возможно..."
- before_after: "0 день vs 90 день..."
- controversial_opinion: "Это убивает ваш прогресс..."
- relatable_struggle: "POV: ты пытаешься..."
- tutorial_teaser: "Этот секрет знают только..."
- trend_remix: адаптация текущего тренда

Категория: {category}

Ответь ТОЛЬКО в формате JSON:
{{
  "hook_type": "curiosity_gap|before_after|controversial_opinion|relatable_struggle|tutorial_teaser|trend_remix",
  "hook_text": "Текст хука на экране (1-2 строки)",
  "script_ru": "Полный сценарий на русском (что говорит/делает)",
  "scene_description": "Описание сцены для генерации изображения (на английском, для FLUX)",
  "motion_prompt": "Описание движения для Kling I2V (на английском)",
  "text_overlays": ["текст1", "текст2", "текст3"],
  "cta": "Призыв к действию",
  "audio_suggestion": "trending sound / original voice / music type",
  "predicted_viral_score": 0.0-1.0,
  "why_viral": "Почему это должно стать вирусным (1 предложение)"
}}"""


VIRAL_CAROUSEL_PROMPT = """Ты — эксперт по вирусным каруселям в Instagram.

Персонаж: {name}, {niche_description}
Аудитория: {audience_summary}

Создай концепцию ВИРУСНОЙ карусели (оптимизация на SAVES — главная метрика для карусели).

Категория: {category}

Требования:
- 7-10 слайдов (оптимум для алгоритма)
- Первый слайд = BOLD заголовок + крючок (человек должен свайпнуть)
- Каждый слайд = 1 мысль, крупный текст
- Предпоследний слайд = самый ценный контент
- Последний слайд = CTA (save + share + follow)
- Формат: value-bomb, каждый слайд хочется сохранить

Ответь ТОЛЬКО в формате JSON:
{{
  "cover_text": "Текст на обложке (большой, жирный)",
  "hook_type": "curiosity_gap|tutorial_teaser|relatable_struggle",
  "slides": [
    {{"slide_num": 1, "text": "...", "visual": "описание визуала"}},
    {{"slide_num": 2, "text": "...", "visual": "..."}}
  ],
  "cta_slide": "Текст CTA на последнем слайде",
  "predicted_viral_score": 0.0-1.0,
  "save_trigger": "Почему это сохранят (1 предложение)"
}}"""


VIRAL_ANALYSIS_PROMPT = """Ты — аналитик вирусного контента.

Проанализируй эти посты и определи паттерны вирусности:

{posts_data}

Для каждого поста определи:
1. Тип хука (curiosity_gap, before_after, controversial_opinion, relatable_struggle, tutorial_teaser, trend_remix)
2. Почему стал вирусным (или не стал)
3. Стратегия репликации

Общие паттерны:
- Какие хуки работают лучше всего?
- Оптимальная длина caption?
- Лучшее время публикации?
- Какие CTA дают больше saves?

Ответь ТОЛЬКО в формате JSON:
{{
  "patterns": [
    {{
      "post_id": 1,
      "hook_type": "...",
      "why_viral": "...",
      "replication_strategy": "..."
    }}
  ],
  "general_insights": {{
    "best_hook_types": ["..."],
    "optimal_caption_length": "short|medium|long",
    "best_cta_type": "save|share|comment|follow",
    "content_themes_trending": ["..."]
  }}
}}"""


async def generate_viral_reel_concept(
    character: Character,
    category: str = "workout",
    audience_summary: str = "",
    trends: str = "",
) -> dict:
    """Generate a viral Reel concept using Claude."""
    cfg = get_anthropic_config()
    client = _get_client()

    from services.character_manager import get_character_prompt_context
    ctx = get_character_prompt_context(character)

    # Get top posts for context
    top_posts = await _get_top_posts_summary(character)

    # Fetch real trends from DB if not provided
    if not trends:
        try:
            from services.trend_analyzer import get_latest_trend_summary
            trends = await get_latest_trend_summary()
        except Exception:
            trends = "Current trends: gym POV, day-in-life, motivation, before/after"

    prompt = VIRAL_REEL_PROMPT.format(
        name=ctx["name"],
        niche_description=character.niche_description,
        audience_summary=audience_summary or "Growing fitness/lifestyle audience, 18-35 age",
        top_posts=top_posts,
        trends=trends,
        category=category,
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse viral reel JSON: %s", response_text[:200])
        result = {}

    logger.info(
        "Generated viral reel concept: hook=%s, score=%.2f",
        result.get("hook_type", "unknown"),
        result.get("predicted_viral_score", 0.0),
    )
    return result


async def generate_viral_carousel_concept(
    character: Character,
    category: str = "tutorial",
    audience_summary: str = "",
) -> dict:
    """Generate a viral carousel concept optimized for saves."""
    cfg = get_anthropic_config()
    client = _get_client()

    from services.character_manager import get_character_prompt_context
    ctx = get_character_prompt_context(character)

    prompt = VIRAL_CAROUSEL_PROMPT.format(
        name=ctx["name"],
        niche_description=character.niche_description,
        audience_summary=audience_summary or "Growing fitness/lifestyle audience, 18-35 age",
        category=category,
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse viral carousel JSON: %s", response_text[:200])
        result = {}

    logger.info(
        "Generated viral carousel concept: hook=%s, slides=%d, score=%.2f",
        result.get("hook_type", "unknown"),
        len(result.get("slides", [])),
        result.get("predicted_viral_score", 0.0),
    )
    return result


async def analyze_viral_patterns(character: Character) -> dict:
    """Analyze our posts and identify viral patterns.

    Saves results to ViralContentAnalysis table.
    """
    cfg = get_anthropic_config()
    client = _get_client()
    db = SessionLocal()

    try:
        # Get last 30 days of published posts with analytics
        cutoff = datetime.utcnow() - timedelta(days=30)
        posts = (
            db.query(Post)
            .filter(Post.character_id == character.id)
            .filter(Post.status == PostStatus.PUBLISHED)
            .filter(Post.published_at >= cutoff)
            .all()
        )

        if not posts:
            return {"count": 0, "message": "No published posts to analyze"}

        # Build posts data for prompt
        posts_data = []
        for p in posts:
            analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == p.id).first()
            posts_data.append({
                "post_id": p.id,
                "type": p.content_type.value,
                "category": p.category.value,
                "caption_ru": (p.caption_ru or "")[:200],
                "hook_text": p.hook_text or "",
                "published_at": p.published_at.isoformat() if p.published_at else "",
                "likes": analytics.likes if analytics else 0,
                "comments": analytics.comments_count if analytics else 0,
                "saves": analytics.saves if analytics else 0,
                "shares": analytics.shares if analytics else 0,
                "reach": analytics.reach if analytics else 0,
                "er": analytics.engagement_rate if analytics else 0.0,
            })

        prompt = VIRAL_ANALYSIS_PROMPT.format(
            posts_data=json.dumps(posts_data, ensure_ascii=False, indent=2)
        )

        message = await client.messages.create(
            model=cfg.model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse viral analysis JSON: %s", response_text[:200])
            return {"count": 0, "error": "parse_failed"}

        # Save individual pattern analyses
        for pattern in result.get("patterns", []):
            analysis = ViralContentAnalysis(
                post_id=pattern.get("post_id"),
                character_id=character.id,
                hook_type=pattern.get("hook_type", ""),
                why_viral=pattern.get("why_viral", ""),
                replication_strategy=pattern.get("replication_strategy", ""),
            )
            db.add(analysis)

        db.commit()

        logger.info(
            "Analyzed %d posts for viral patterns, found insights: %s",
            len(posts),
            json.dumps(result.get("general_insights", {}), ensure_ascii=False)[:200],
        )

        return {
            "count": len(result.get("patterns", [])),
            "insights": result.get("general_insights", {}),
        }

    finally:
        db.close()


async def score_content_virality(
    hook_text: str,
    content_type: str,
    category: str,
    caption: str,
) -> float:
    """Pre-score content virality before publishing (0.0-1.0)."""
    cfg = get_anthropic_config()
    client = _get_client()

    prompt = f"""Score this Instagram content for viral potential (0.0-1.0):

Type: {content_type}
Category: {category}
Hook: {hook_text}
Caption (first 200 chars): {caption[:200]}

Evaluate:
- Hook strength (does it stop the scroll?)
- Emotional trigger (curiosity, controversy, relatability)
- Shareability (would someone share this?)
- Save-worthiness (is this reference-worthy content?)
- Trend relevance

Respond ONLY with a number between 0.0 and 1.0:"""

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        score = float(message.content[0].text.strip())
        return max(0.0, min(1.0, score))
    except ValueError:
        return 0.5


async def _get_top_posts_summary(character: Character) -> str:
    """Get summary of top-performing posts for viral concept generation."""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=30)
        posts = (
            db.query(Post)
            .filter(Post.character_id == character.id)
            .filter(Post.status == PostStatus.PUBLISHED)
            .filter(Post.published_at >= cutoff)
            .all()
        )

        if not posts:
            return "No published posts yet — this is the first content."

        # Sort by engagement rate
        post_entries = []
        for p in posts:
            analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == p.id).first()
            if analytics:
                post_entries.append((p, analytics))

        post_entries.sort(key=lambda x: x[1].engagement_rate or 0, reverse=True)

        lines = []
        for p, a in post_entries[:5]:
            lines.append(
                f"- {p.content_type.value} ({p.category.value}): "
                f"ER={a.engagement_rate:.2f}%, likes={a.likes}, saves={a.saves}, "
                f"hook={p.hook_text or 'none'}"
            )

        return "\n".join(lines) if lines else "No posts with analytics yet."

    finally:
        db.close()
