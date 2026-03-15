"""Content strategy engine — Claude AI generates content calendars and analyzes performance."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.models import Character, ContentCategory, ContentType

logger = logging.getLogger("aizavod.content_strategy")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


VIRAL_CALENDAR_PROMPT = """Ты — growth-hacking менеджер контента, цель — максимальный рост подписчиков.

Персонаж: {name}
Ниша: {niche_description}
Платформы: {platforms}
Стиль: {tone}
Любимые темы: {topics}

=== ТЕКУЩАЯ СТАТИСТИКА ===
- Подписчики: {followers}
- Средний ER: {avg_er}%
- Лучшие категории: {best_categories}
- Целевой рост: {target_growth} подписчиков/месяц

=== КОНТЕНТ-МИКС (обязательно соблюдать) ===
- Reels: {reels_pct}% (главный драйвер reach и роста)
- Carousels: {carousels_pct}% (драйвер saves и экспертности)
- Photo: {photo_pct}% (поддержка эстетики ленты)
- Stories: {stories_per_day}/день (engagement + связь с аудиторией)

=== ТЕКУЩИЕ ТРЕНДЫ ===
{trend_context}

=== TRENDING CAMERA ANGLES ===
{camera_angles}

=== ОПТИМАЛЬНОЕ ВРЕМЯ ПОСТИНГА (UTC) ===
Целевые аудитории: Россия (MSK = UTC+3) + Европа (CET = UTC+1).
Пики активности:
- Утро: 06:00-08:00 UTC (09:00-11:00 MSK / 07:00-09:00 CET)
- Обед: 09:00-11:00 UTC (12:00-14:00 MSK / 10:00-12:00 CET)
- Вечер: 15:00-19:00 UTC (18:00-22:00 MSK / 16:00-20:00 CET) ← ГЛАВНЫЙ ПИК

Расписание публикаций (1 мастер-видео = 3 публикации):
1. TikTok 65s: ~15:00 UTC (18:00 MSK) — вечерний прайм-тайм RU
2. IG Reel часть 1: ~17:00 UTC (20:00 MSK / 18:00 CET) — пик ОБЕИХ аудиторий
3. IG Reel часть 2: ~19:00 UTC (22:00 MSK / 20:00 CET) — вечер EU, поздний RU

Время Stories: 08:00, 13:00, 17:00 UTC (утро/день/вечер обеих аудиторий)

ПРАВИЛО: всегда ставь рилсы в диапазоне 15:00-19:00 UTC! Никогда ночью (22:00-06:00 UTC).
Варьируй ±15 минут от дня к дню чтобы избежать паттернов.

=== GROWTH-HACKING ПРАВИЛА ===

Для КАЖДОГО Reel:
- TikTok: 65 секунд (7 клипов × 10 сек, генерируется автоматически)
- Instagram: автоматический сплит на 2 × ~30с Reels
- HOOK в первые 1-3 секунды (скролл-стоппер)
- Loop ending (видео хочется пересмотреть)
- Text overlay на экране
- CTA: "Сохрани 🔖" или "Отправь подруге"
- motion_prompt: описание движений для Kling I2V
- audio_suggestion: trending sound / original voice
- camera_angle: один из trending camera angles
- outfit: конкретная одежда (для consistency между клипами)
- location: конкретная локация

Для КАЖДОГО Carousel:
- Cover slide: BOLD заголовок, максимум 5 слов
- 7-10 слайдов, каждый = 1 мысль
- Оптимизация на SAVES
- Последний слайд = CTA (save + follow)
- slide_count: сколько слайдов

Для КАЖДОГО Photo:
- Эстетика ленты, визуальная привлекательность
- Вовлекающая подпись с вопросом

=== ПЛАН НА {days} ДНЕЙ ===

Категории: {categories_desc}

Для каждого поста:
1. content_type: reel / carousel / photo
2. category: одна из перечисленных
3. description_ru / description_en: описание
4. time: оптимальное время (HH:MM)
5. scene: описание для генерации изображения (английский, для FLUX)
6. pose, outfit, setting
7. hook_text: текст хука (для reels/carousels)
8. hook_type: curiosity_gap / before_after / controversial_opinion / relatable_struggle / tutorial_teaser / trend_remix
9. motion_prompt: (для reels) описание движений
10. audio_suggestion: (для reels) тип аудио
11. slide_count: (для carousels) кол-во слайдов
12. cover_text: (для carousels) текст обложки

Ответь ТОЛЬКО в формате JSON (без markdown):
{{
  "calendar": [
    {{
      "day": 1,
      "date": "YYYY-MM-DD",
      "posts": [
        {{
          "content_type": "reel",
          "category": "workout",
          "description_ru": "...",
          "description_en": "...",
          "time": "09:00",
          "scene": "...",
          "pose": "...",
          "outfit": "...",
          "setting": "...",
          "hook_text": "...",
          "hook_type": "curiosity_gap",
          "motion_prompt": "...",
          "audio_suggestion": "trending upbeat music",
          "camera_angle": "low angle wide shot",
          "slide_count": null,
          "cover_text": null
        }}
      ],
      "stories": [
        {{
          "description_ru": "...",
          "description_en": "...",
          "time": "08:00",
          "interactive": {{"type": "poll", "question_ru": "...", "question_en": "...", "options": ["A", "B"]}}
        }}
      ]
    }}
  ]
}}"""


async def generate_weekly_calendar(
    character: Character,
    days: int = 7,
    followers: int = 0,
    avg_er: float = 0.0,
    best_categories: str = "workout, lifestyle",
    posts_per_day: int = 2,
    stories_per_day: int = 5,
    reels_per_week: int = 3,
    reels_pct: int = 65,
    carousels_pct: int = 25,
    target_growth: int = 10000,
) -> list[dict]:
    """Generate a viral-optimized content calendar for N days."""
    cfg = get_anthropic_config()
    client = _get_client()

    from services.character_manager import get_character_prompt_context

    ctx = get_character_prompt_context(character)
    start_date = datetime.utcnow() + timedelta(days=1)

    # Build categories description
    try:
        cats = json.loads(character.content_categories)
    except (json.JSONDecodeError, TypeError):
        cats = ["workout", "lifestyle", "motivation"]
    categories_desc = "\n".join(f"- {c}" for c in cats)

    # Platforms list
    try:
        platforms_list = json.loads(character.platforms)
    except (json.JSONDecodeError, TypeError):
        platforms_list = ["instagram"]

    photo_pct = 100 - reels_pct - carousels_pct

    # Fetch real trends for prompt injection
    trend_context_text = "No trend data yet — use general fitness trends"
    camera_angles_text = "medium shot, close-up, low angle, tracking shot"
    try:
        from services.trend_analyzer import get_latest_trend_summary, get_trending_camera_angles
        trend_context_text = await get_latest_trend_summary()
        angles = await get_trending_camera_angles()
        if angles:
            camera_angles_text = "\n".join(
                f"- {a.get('camera_angle', 'medium shot')}: {a.get('cinematography', '')}"
                for a in angles
            )
    except Exception:
        pass

    prompt = VIRAL_CALENDAR_PROMPT.format(
        name=ctx["name"],
        niche_description=character.niche_description,
        platforms=", ".join(platforms_list),
        tone=ctx["tone"],
        topics=", ".join(ctx["topics"]) if ctx["topics"] else character.niche,
        followers=followers,
        avg_er=avg_er,
        best_categories=best_categories,
        target_growth=target_growth,
        reels_pct=reels_pct,
        carousels_pct=carousels_pct,
        photo_pct=photo_pct,
        days=days,
        stories_per_day=stories_per_day,
        categories_desc=categories_desc,
        trend_context=trend_context_text,
        camera_angles=camera_angles_text,
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        data = json.loads(response_text)
        calendar = data.get("calendar", [])
    except json.JSONDecodeError:
        logger.error("Failed to parse calendar JSON: %s", response_text[:200])
        calendar = []

    for i, day_entry in enumerate(calendar):
        day_entry["date"] = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")

    logger.info("Generated %d-day viral content calendar with %d days", days, len(calendar))
    return calendar


async def adapt_strategy_from_data(character: Character) -> dict:
    """Analyze 30 days of real data and adjust strategy automatically.

    Returns adjusted parameters (content_mix, posting_times, focus_categories).
    """
    from backend.database import SessionLocal
    from backend.models import Post, PostAnalytics, PostStatus, DailyMetrics

    cfg = get_anthropic_config()
    client = _get_client()
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

        if len(posts) < 5:
            return {"adapted": False, "reason": "Not enough data (need 5+ published posts)"}

        # Build detailed performance breakdown
        type_data = {}
        category_data = {}
        hour_data = {}

        for p in posts:
            a = db.query(PostAnalytics).filter(PostAnalytics.post_id == p.id).first()
            if not a:
                continue

            er = a.engagement_rate or 0.0
            saves = a.saves or 0

            ct = p.content_type.value
            type_data.setdefault(ct, {"er": [], "saves": [], "count": 0})
            type_data[ct]["er"].append(er)
            type_data[ct]["saves"].append(saves)
            type_data[ct]["count"] += 1

            cat = p.category.value
            category_data.setdefault(cat, {"er": [], "count": 0})
            category_data[cat]["er"].append(er)
            category_data[cat]["count"] += 1

            if p.published_at:
                h = p.published_at.hour
                hour_data.setdefault(h, {"er": [], "count": 0})
                hour_data[h]["er"].append(er)
                hour_data[h]["count"] += 1

        # Summarize for prompt
        type_summary = "\n".join(
            f"- {t}: avg_ER={sum(d['er'])/len(d['er']):.2f}%, avg_saves={sum(d['saves'])/len(d['saves']):.0f}, count={d['count']}"
            for t, d in type_data.items() if d["er"]
        )
        cat_summary = "\n".join(
            f"- {c}: avg_ER={sum(d['er'])/len(d['er']):.2f}%, count={d['count']}"
            for c, d in category_data.items() if d["er"]
        )
        hour_summary = "\n".join(
            f"- {h:02d}:00: avg_ER={sum(d['er'])/len(d['er']):.2f}%, count={d['count']}"
            for h, d in sorted(hour_data.items()) if d["er"]
        )

        # Growth data
        metrics = db.query(DailyMetrics).order_by(DailyMetrics.date.desc()).limit(30).all()
        growth = 0
        if len(metrics) >= 2:
            growth = metrics[0].followers_count - metrics[-1].followers_count

        prompt = f"""Ты — growth-аналитик Instagram.

Данные за 30 дней ({len(posts)} постов):

По типам контента:
{type_summary or 'No data'}

По категориям:
{cat_summary or 'No data'}

По времени публикации:
{hour_summary or 'No data'}

Рост подписчиков за 30 дней: {growth}

На основе РЕАЛЬНЫХ данных адаптируй стратегию:

Ответь ТОЛЬКО в формате JSON:
{{
  "reels_pct": 65,
  "carousels_pct": 25,
  "photo_pct": 10,
  "focus_categories": ["category1", "category2"],
  "reduce_categories": ["category3"],
  "best_posting_times": ["09:00", "12:00", "18:00"],
  "recommendations": ["рекомендация1", "рекомендация2"],
  "projected_monthly_growth": 0
}}"""

        message = await client.messages.create(
            model=cfg.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            result = json.loads(message.content[0].text.strip())
            result["adapted"] = True
            logger.info("Strategy adapted: reels=%d%%, carousels=%d%%",
                        result.get("reels_pct", 65), result.get("carousels_pct", 25))
            return result
        except json.JSONDecodeError:
            return {"adapted": False, "reason": "Failed to parse AI response"}

    finally:
        db.close()


STRATEGY_ANALYSIS_PROMPT = """Ты — аналитик аккаунта в соцсетях.

Проанализируй результаты за последнюю неделю:

Лучшие посты (по engagement):
{top_posts}

Худшие посты:
{worst_posts}

Общая статистика:
- Средний ER: {avg_er}%
- Рост подписчиков: {followers_growth}
- Лучшее время: {best_times}
- Лучшая категория: {best_category}

Дай рекомендации:
1. Какие категории усилить
2. Какие ослабить
3. Оптимальное время постинга
4. Рекомендации по стилю контента
5. Content mix (процентное распределение)

Ответь в формате JSON:
{{
  "recommendations": ["..."],
  "content_mix": {{
    "workout": 0.30,
    "lifestyle": 0.20,
    "motivation": 0.15,
    "outfit": 0.10,
    "nutrition": 0.10,
    "behind_scenes": 0.05,
    "transformation": 0.05,
    "tutorial": 0.05
  }},
  "best_posting_times": ["09:00", "12:00", "18:00", "21:00"],
  "increase_categories": ["..."],
  "decrease_categories": ["..."]
}}"""


async def analyze_weekly_performance(
    top_posts: str = "No data yet",
    worst_posts: str = "No data yet",
    avg_er: float = 0.0,
    followers_growth: int = 0,
    best_times: str = "09:00, 18:00",
    best_category: str = "workout",
) -> dict:
    """Analyze weekly performance and return strategy adjustments."""
    cfg = get_anthropic_config()
    client = _get_client()

    prompt = STRATEGY_ANALYSIS_PROMPT.format(
        top_posts=top_posts,
        worst_posts=worst_posts,
        avg_er=avg_er,
        followers_growth=followers_growth,
        best_times=best_times,
        best_category=best_category,
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse strategy JSON: %s", response_text[:200])
        return {"recommendations": [], "content_mix": {}}
