"""Audience Analyzer — demographics, segments, posting schedule, competitor analysis.

Gathers data from Instagram analytics and PostAnalytics, processes with Claude,
and stores insights in AudienceInsight and CompetitorProfile tables.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, date
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.database import SessionLocal
from backend.models import (
    AudienceInsight,
    Character,
    CompetitorProfile,
    DailyMetrics,
    Post,
    PostAnalytics,
    PostStatus,
)

logger = logging.getLogger("aizavod.audience_analyzer")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


AUDIENCE_ANALYSIS_PROMPT = """Ты — аналитик Instagram-аудитории.

Данные аккаунта @nika_flexx:

Подписчики: {followers}
Рост за 7 дней: {growth_7d}
Средний ER: {avg_er:.2f}%

Статистика постов за 30 дней:
{posts_stats}

Распределение по категориям (ER):
{category_stats}

Распределение по типам контента (ER):
{type_stats}

Распределение по времени публикации (ER):
{time_stats}

Проанализируй:
1. Demographics (предполагаемые на основе engagement паттернов)
2. Активные часы (когда лучший ER)
3. Предпочтения контента (какие категории/типы заходят)
4. Сегменты аудитории (superfans / regular / passive)
5. Рекомендации по росту

Ответь ТОЛЬКО в формате JSON:
{{
  "demographics": {{
    "primary_age": "18-24|25-34|35-44",
    "gender_split": "female 70%, male 30%",
    "primary_geo": "Russia, CIS",
    "interests": ["fitness", "lifestyle", "motivation"]
  }},
  "active_hours": {{
    "best_hours": [9, 12, 18, 21],
    "worst_hours": [2, 3, 4, 5],
    "best_days": ["Monday", "Wednesday", "Friday"]
  }},
  "content_preferences": {{
    "best_categories": ["..."],
    "worst_categories": ["..."],
    "best_content_type": "reel|carousel|photo",
    "optimal_caption_length": "short|medium|long"
  }},
  "segments": {{
    "superfans_pct": 5,
    "regular_pct": 30,
    "passive_pct": 50,
    "ghost_pct": 15
  }},
  "recommendations": ["Рекомендация 1", "Рекомендация 2", "..."],
  "growth_actions": ["Действие 1", "Действие 2", "..."]
}}"""


COMPETITOR_ANALYSIS_PROMPT = """Ты — аналитик конкурентов в Instagram.

Наш аккаунт: @nika_flexx ({our_followers} подписчиков, ER {our_er:.2f}%)
Ниша: {niche}

Конкурент: @{competitor_username}
Подписчики: {comp_followers}
Постов за 30 дней: {comp_posts_count}

Данные о контенте конкурента:
{comp_content_data}

Проанализируй:
1. Сильные стороны конкурента
2. Слабые стороны / gaps, которые мы можем занять
3. Контент-микс конкурента (% reels/carousel/photo)
4. Хештег-стратегия
5. Что мы можем скопировать/адаптировать

Ответь ТОЛЬКО в формате JSON:
{{
  "strengths": ["..."],
  "weaknesses": ["..."],
  "content_mix": {{"reels": 60, "carousel": 25, "photo": 15}},
  "hashtag_strategy": "описание",
  "posting_frequency": "X posts/day",
  "best_content_themes": ["..."],
  "gaps_we_can_fill": ["..."],
  "actionable_insights": ["Что сделать 1", "Что сделать 2"]
}}"""


async def analyze_audience(character: Character) -> dict:
    """Run full audience analysis and save to AudienceInsight."""
    cfg = get_anthropic_config()
    client = _get_client()
    db = SessionLocal()

    try:
        # Gather data
        stats = _gather_audience_stats(db, character)

        prompt = AUDIENCE_ANALYSIS_PROMPT.format(**stats)

        message = await client.messages.create(
            model=cfg.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse audience analysis: %s", response_text[:200])
            return {"id": None, "error": "parse_failed"}

        # Save insight
        insight = AudienceInsight(
            character_id=character.id,
            snapshot_date=date.today(),
            demographics=json.dumps(result.get("demographics", {}), ensure_ascii=False),
            active_hours=json.dumps(result.get("active_hours", {}), ensure_ascii=False),
            content_preferences=json.dumps(result.get("content_preferences", {}), ensure_ascii=False),
            audience_segments=json.dumps(result.get("segments", {}), ensure_ascii=False),
            recommendations=json.dumps(result.get("recommendations", []), ensure_ascii=False),
        )
        db.add(insight)
        db.commit()

        logger.info("Audience analysis saved (insight_id=%d)", insight.id)
        return {"id": insight.id, "recommendations": result.get("recommendations", [])}

    finally:
        db.close()


async def analyze_competitors(character: Character) -> dict:
    """Analyze competitors and save to CompetitorProfile.

    Uses Instagram client to fetch competitor data.
    """
    db = SessionLocal()
    try:
        # Get existing competitor profiles or discover new ones
        existing = (
            db.query(CompetitorProfile)
            .filter(CompetitorProfile.character_id == character.id)
            .all()
        )

        if not existing:
            # Seed with default competitors based on niche
            competitors = _get_default_competitors(character.niche)
        else:
            competitors = [{"username": c.username} for c in existing]

        analyzed = 0
        for comp_data in competitors:
            try:
                await _analyze_single_competitor(
                    character, comp_data["username"], db
                )
                analyzed += 1
            except Exception as e:
                logger.warning("Failed to analyze @%s: %s", comp_data["username"], e)

        db.commit()
        return {"count": analyzed}

    finally:
        db.close()


async def _analyze_single_competitor(
    character: Character,
    username: str,
    db,
) -> None:
    """Analyze a single competitor and save/update their profile."""
    cfg = get_anthropic_config()
    client = _get_client()

    # Try to fetch competitor data via IG client
    comp_content_data = "No direct data available — analyze based on niche knowledge"
    comp_followers = 0
    comp_posts_count = 0

    try:
        from services.instagram_client import get_instagram_client
        ig = get_instagram_client()
        user_info = await ig.get_user_info(username)
        comp_followers = user_info.get("followers", 0)
        comp_posts_count = user_info.get("media_count", 0)
    except Exception:
        pass

    # Our stats
    latest_metrics = (
        db.query(DailyMetrics)
        .order_by(DailyMetrics.date.desc())
        .first()
    )
    our_followers = latest_metrics.followers_count if latest_metrics else 0
    our_er = 0.0

    prompt = COMPETITOR_ANALYSIS_PROMPT.format(
        our_followers=our_followers,
        our_er=our_er,
        niche=character.niche_description,
        competitor_username=username,
        comp_followers=comp_followers,
        comp_posts_count=comp_posts_count,
        comp_content_data=comp_content_data,
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
        logger.error("Failed to parse competitor analysis for @%s", username)
        return

    # Upsert CompetitorProfile
    profile = (
        db.query(CompetitorProfile)
        .filter(CompetitorProfile.character_id == character.id)
        .filter(CompetitorProfile.username == username)
        .first()
    )

    if not profile:
        profile = CompetitorProfile(
            character_id=character.id,
            username=username,
        )
        db.add(profile)

    profile.followers_count = comp_followers
    profile.content_mix = json.dumps(result.get("content_mix", {}), ensure_ascii=False)
    profile.strengths = json.dumps(result.get("strengths", []), ensure_ascii=False)
    profile.weaknesses = json.dumps(result.get("weaknesses", []), ensure_ascii=False)
    profile.gaps = json.dumps(result.get("gaps_we_can_fill", []), ensure_ascii=False)
    profile.last_analyzed_at = datetime.utcnow()

    logger.info("Competitor @%s analyzed (%d followers)", username, comp_followers)


def _gather_audience_stats(db, character: Character) -> dict:
    """Gather stats from DB for audience analysis prompt."""
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)

    # Followers & growth
    latest = (
        db.query(DailyMetrics)
        .order_by(DailyMetrics.date.desc())
        .first()
    )
    week_ago_metrics = (
        db.query(DailyMetrics)
        .filter(DailyMetrics.date <= week_ago.date())
        .order_by(DailyMetrics.date.desc())
        .first()
    )

    followers = latest.followers_count if latest else 0
    growth_7d = 0
    if latest and week_ago_metrics:
        growth_7d = latest.followers_count - week_ago_metrics.followers_count

    # Posts with analytics
    posts = (
        db.query(Post)
        .filter(Post.character_id == character.id)
        .filter(Post.status == PostStatus.PUBLISHED)
        .filter(Post.published_at >= month_ago)
        .all()
    )

    # ER stats
    ers = []
    category_ers = {}
    type_ers = {}
    hour_ers = {}

    for p in posts:
        analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == p.id).first()
        if not analytics or not analytics.engagement_rate:
            continue

        er = analytics.engagement_rate
        ers.append(er)

        cat = p.category.value
        category_ers.setdefault(cat, []).append(er)

        ctype = p.content_type.value
        type_ers.setdefault(ctype, []).append(er)

        if p.published_at:
            hour = p.published_at.hour
            hour_ers.setdefault(hour, []).append(er)

    avg_er = sum(ers) / len(ers) if ers else 0.0

    # Format stats
    category_lines = []
    for cat, er_list in sorted(category_ers.items(), key=lambda x: -(sum(x[1])/len(x[1]))):
        category_lines.append(f"- {cat}: avg ER={sum(er_list)/len(er_list):.2f}% ({len(er_list)} posts)")

    type_lines = []
    for ctype, er_list in sorted(type_ers.items(), key=lambda x: -(sum(x[1])/len(x[1]))):
        type_lines.append(f"- {ctype}: avg ER={sum(er_list)/len(er_list):.2f}% ({len(er_list)} posts)")

    time_lines = []
    for hour in sorted(hour_ers.keys()):
        er_list = hour_ers[hour]
        time_lines.append(f"- {hour:02d}:00: avg ER={sum(er_list)/len(er_list):.2f}% ({len(er_list)} posts)")

    return {
        "followers": followers,
        "growth_7d": growth_7d,
        "avg_er": avg_er,
        "posts_stats": f"{len(posts)} posts in 30 days, avg ER={avg_er:.2f}%",
        "category_stats": "\n".join(category_lines) or "No category data yet",
        "type_stats": "\n".join(type_lines) or "No type data yet",
        "time_stats": "\n".join(time_lines) or "No time data yet",
    }


def get_optimal_posting_schedule(character: Character) -> list[str]:
    """Get optimal posting times based on historical ER data."""
    db = SessionLocal()
    try:
        month_ago = datetime.utcnow() - timedelta(days=30)
        posts = (
            db.query(Post)
            .filter(Post.character_id == character.id)
            .filter(Post.status == PostStatus.PUBLISHED)
            .filter(Post.published_at >= month_ago)
            .all()
        )

        hour_ers = {}
        for p in posts:
            analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == p.id).first()
            if not analytics or not analytics.engagement_rate or not p.published_at:
                continue
            hour = p.published_at.hour
            hour_ers.setdefault(hour, []).append(analytics.engagement_rate)

        if not hour_ers:
            return ["09:00", "12:00", "18:00", "21:00"]

        # Sort hours by average ER, take top 4
        sorted_hours = sorted(
            hour_ers.items(),
            key=lambda x: sum(x[1]) / len(x[1]),
            reverse=True,
        )

        return [f"{h:02d}:00" for h, _ in sorted_hours[:4]]

    finally:
        db.close()


def _get_default_competitors(niche: str) -> list[dict]:
    """Return seed competitor usernames based on niche."""
    niche_lower = niche.lower() if niche else ""
    if "fitness" in niche_lower or "workout" in niche_lower:
        return [
            {"username": "kayla_itsines"},
            {"username": "pamela_rf"},
            {"username": "tammy_hembrow"},
        ]
    return [
        {"username": "selenagomez"},
        {"username": "kyliejenner"},
    ]
