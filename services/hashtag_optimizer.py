"""AI-powered hashtag optimization for Instagram posts.

Features:
- Claude AI generates optimized hashtag sets based on content + audience data
- Anti-shadowban: never repeat exact same set (rotation)
- Mix: 5 large + 10 medium + 10 niche + 5 content-specific
- Fallback: static pools if AI unavailable
- Performance tracking via Redis (which hashtags drive reach)
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.models import ContentCategory

logger = logging.getLogger("aizavod.hashtag_optimizer")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


# Recent hashtag sets (in-memory cache to avoid exact duplicates)
_recent_sets: list[str] = []
_MAX_RECENT = 50


HASHTAG_PROMPT = """Ты — эксперт по хештегам Instagram для growth hacking.

Аккаунт: @nika_flexx
Ниша: фитнес, лайфстайл, мотивация
Подписчики: {followers}

Пост:
- Тип: {content_type}
- Категория: {category}
- Описание: {description}
- Hook: {hook_text}

Лучшие хештеги из прошлых постов (по reach):
{top_hashtags}

=== ПРАВИЛА ===
1. РОВНО 30 хештегов
2. Микс: 5 large (>1M постов) + 10 medium (100K-1M) + 10 niche (<100K) + 5 content-specific
3. НЕ ПОВТОРЯТЬ точный набор предыдущих постов (anti-shadowban)
4. Включить 2-3 русскоязычных хештега
5. Хештеги должны быть релевантны КОНКРЕТНОМУ посту, не generic
6. Формат: каждый начинается с #, без кавычек

Ответь ТОЛЬКО в формате JSON:
{{
  "hashtags": ["#tag1", "#tag2", ...],
  "large": ["#tag1", ...],
  "medium": ["#tag1", ...],
  "niche": ["#tag1", ...],
  "content_specific": ["#tag1", ...]
}}"""


async def get_optimized_hashtags(
    category: ContentCategory,
    content_type: str = "photo",
    description: str = "",
    hook_text: str = "",
    followers: int = 0,
    top_hashtags: str = "",
) -> str:
    """Generate AI-optimized hashtags for a post.

    Falls back to static pools if AI is unavailable.
    """
    try:
        result = await _ai_hashtags(
            category=category,
            content_type=content_type,
            description=description,
            hook_text=hook_text,
            followers=followers,
            top_hashtags=top_hashtags,
        )
        hashtags = result.get("hashtags", [])
        if hashtags:
            # Anti-shadowban: check for duplicate set
            set_hash = _hash_set(hashtags)
            if set_hash in _recent_sets:
                random.shuffle(hashtags)
                hashtags = hashtags[:27] + _get_random_niche(category, 3)

            _recent_sets.append(set_hash)
            if len(_recent_sets) > _MAX_RECENT:
                _recent_sets.pop(0)

            tag_str = " ".join(hashtags[:30])
            logger.info("AI hashtags for %s %s: %d tags", content_type, category.value, len(hashtags))
            return tag_str
    except Exception as e:
        logger.warning("AI hashtag generation failed, using fallback: %s", e)

    return get_hashtags_static(category)


async def _ai_hashtags(
    category: ContentCategory,
    content_type: str,
    description: str,
    hook_text: str,
    followers: int,
    top_hashtags: str,
) -> dict:
    """Get hashtags from Claude AI."""
    cfg = get_anthropic_config()
    client = _get_client()

    prompt = HASHTAG_PROMPT.format(
        followers=followers,
        content_type=content_type,
        category=category.value,
        description=description[:300],
        hook_text=hook_text[:100],
        top_hashtags=top_hashtags or "No data yet — first posts",
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse hashtag JSON: %s", response_text[:200])
        return {}


async def track_hashtag_performance() -> dict:
    """Track which hashtags correlate with high reach.

    Analyzes published posts and their analytics to find best-performing hashtags.
    """
    from backend.database import SessionLocal
    from backend.models import Post, PostAnalytics, PostStatus

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=30)
        posts = (
            db.query(Post)
            .filter(Post.status == PostStatus.PUBLISHED)
            .filter(Post.published_at >= cutoff)
            .filter(Post.hashtags.isnot(None))
            .all()
        )

        hashtag_reach: dict[str, list[int]] = {}

        for p in posts:
            analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == p.id).first()
            if not analytics or not analytics.reach:
                continue

            tags = [t.strip() for t in (p.hashtags or "").split() if t.startswith("#")]
            for tag in tags:
                hashtag_reach.setdefault(tag, []).append(analytics.reach)

        # Calculate average reach per hashtag
        results = {}
        for tag, reaches in hashtag_reach.items():
            results[tag] = {
                "avg_reach": sum(reaches) / len(reaches),
                "uses": len(reaches),
            }

        # Sort by avg_reach
        sorted_tags = sorted(results.items(), key=lambda x: -x[1]["avg_reach"])

        top_10 = {tag: data for tag, data in sorted_tags[:10]}
        bottom_10 = {tag: data for tag, data in sorted_tags[-10:]}

        logger.info(
            "Tracked %d unique hashtags from %d posts",
            len(results),
            len(posts),
        )

        return {
            "total_tracked": len(results),
            "top_performers": top_10,
            "worst_performers": bottom_10,
        }

    finally:
        db.close()


def _hash_set(tags: list[str]) -> str:
    """Create a hash of a sorted hashtag set for duplicate detection."""
    normalized = sorted(t.lower().strip() for t in tags)
    return hashlib.md5("|".join(normalized).encode()).hexdigest()


def _get_random_niche(category: ContentCategory, count: int) -> list[str]:
    """Get random niche hashtags from static pool."""
    pool = HASHTAG_POOLS.get(category.value, HASHTAG_POOLS["workout"])
    niche = pool.get("niche", [])
    return random.sample(niche, min(count, len(niche)))


# ─── Static fallback pools ────────────────────────────────────────────────

HASHTAG_POOLS: dict[str, dict[str, list[str]]] = {
    "workout": {
        "large": [
            "#fitness", "#workout", "#gym", "#fitnessmotivation", "#training",
            "#fitgirl", "#gymlife", "#fitnessmodel", "#bodybuilding", "#exercise",
        ],
        "medium": [
            "#workoutmotivation", "#fitnessgirl", "#gymmotivation", "#fitnessaddict",
            "#fitlife", "#trainhard", "#strengthtraining", "#fitfam", "#gymgirl",
        ],
        "niche": [
            "#girlswholift", "#fitspo", "#fitnessbabe", "#workoutroutine",
            "#gymworkout", "#trainingday", "#fitnesslove", "#workoutinspo",
        ],
    },
    "lifestyle": {
        "large": [
            "#lifestyle", "#healthy", "#healthylifestyle", "#life", "#instagood",
            "#love", "#happy", "#beautiful", "#selfcare", "#wellness",
        ],
        "medium": [
            "#lifestyleblogger", "#healthyliving", "#dailylife", "#goodvibes",
            "#livingmybestlife", "#lifestylegoals", "#mindset", "#selflove",
        ],
        "niche": [
            "#fitlifestyle", "#wellnessjourney", "#healthyhabits", "#fitnesslifestyle",
            "#activelifestyle", "#lifestyleinspo", "#balancedlife",
        ],
    },
    "motivation": {
        "large": [
            "#motivation", "#inspiration", "#motivationalquotes", "#mindset",
            "#goals", "#success", "#nevergiveup", "#believeinyourself",
        ],
        "medium": [
            "#fitnessmotivation", "#gymmotivation", "#motivationdaily",
            "#fitnessinspo", "#staystrong", "#motivationmonday", "#keepgoing",
        ],
        "niche": [
            "#fitmotivation", "#strongwomen", "#girlpower", "#fitspiration",
            "#progressnotperfection", "#strongnotskinny", "#empoweredwomen",
        ],
    },
    "outfit": {
        "large": [
            "#ootd", "#fashion", "#style", "#outfit", "#instafashion",
            "#activewear", "#sportswear", "#athleisure",
        ],
        "medium": [
            "#gymoutfit", "#fitnessfashion", "#workoutwear", "#activewearfashion",
            "#sportylook", "#outfitinspo", "#styleinspo",
        ],
        "niche": [
            "#gymlook", "#fitnessstyle", "#workoutclothes", "#leggings",
            "#sportsbralife", "#activewearstyle", "#fitfashion",
        ],
    },
    "nutrition": {
        "large": [
            "#nutrition", "#healthyfood", "#foodie", "#healthyeating",
            "#mealprep", "#cleaneating", "#food", "#cooking",
        ],
        "medium": [
            "#fitfood", "#healthyrecipes", "#mealprepideas", "#eatclean",
            "#nutritiontips", "#healthymeal", "#proteinrich",
        ],
        "niche": [
            "#fitnessnutrition", "#mealprepsunday", "#highprotein",
            "#macros", "#healthysnacks", "#fitmeals", "#cleaneats",
        ],
    },
    "behind_scenes": {
        "large": [
            "#behindthescenes", "#bts", "#reallife", "#dayinmylife",
            "#authentic", "#real", "#nofilter",
        ],
        "medium": [
            "#fitnessbts", "#daytodaylife", "#unfiltered", "#rawandreal",
            "#keepitreal", "#momentslikethese",
        ],
        "niche": [
            "#fitnessjourney", "#fitgirlproblems", "#gymprep",
            "#realfitness", "#behindthefit",
        ],
    },
    "transformation": {
        "large": [
            "#transformation", "#beforeandafter", "#progress", "#results",
            "#fitnesstransformation", "#bodygoals",
        ],
        "medium": [
            "#progresspic", "#fitnessjourney", "#transformationtuesday",
            "#fitnessprogress", "#bodybuildingtransformation",
        ],
        "niche": [
            "#gaintrain", "#fitnessresults", "#myprogress",
            "#strengthgains", "#transformationgoals",
        ],
    },
    "tutorial": {
        "large": [
            "#tutorial", "#tips", "#howto", "#learn", "#education",
            "#fitnesstips", "#workouttips",
        ],
        "medium": [
            "#fitnesstutorial", "#exercisetips", "#formcheck",
            "#workoutguide", "#trainertips", "#fitnesscoach",
        ],
        "niche": [
            "#exerciseform", "#techniquetips", "#learntofit",
            "#fitnessadvice", "#coachtips",
        ],
    },
    "collaboration": {
        "large": [
            "#collab", "#collaboration", "#partner", "#ad", "#sponsored",
            "#brandambassador",
        ],
        "medium": [
            "#fitnesscollaboration", "#fitnesspartner", "#fitcollab",
            "#ambassadorlife", "#partnered",
        ],
        "niche": [
            "#fitnessbrand", "#sportsnutrition", "#supplemented",
            "#fitnessequipment",
        ],
    },
}

UNIVERSAL_HASHTAGS = [
    "#instagram", "#instadaily", "#photooftheday", "#instagood",
    "#picoftheday", "#follow", "#like4like",
]


def get_hashtags_static(
    category: ContentCategory,
    count: int = 30,
    include_universal: bool = True,
) -> str:
    """Static fallback: generate hashtags from pre-defined pools."""
    cat_key = category.value
    pool = HASHTAG_POOLS.get(cat_key, HASHTAG_POOLS["workout"])

    large = random.sample(pool["large"], min(10, len(pool["large"])))
    medium = random.sample(pool["medium"], min(10, len(pool["medium"])))
    niche = random.sample(pool["niche"], min(7, len(pool["niche"])))

    selected = large + medium + niche

    if include_universal:
        remaining = count - len(selected)
        if remaining > 0:
            selected += random.sample(UNIVERSAL_HASHTAGS, min(remaining, len(UNIVERSAL_HASHTAGS)))

    selected = list(dict.fromkeys(selected))[:count]
    random.shuffle(selected)

    return " ".join(selected)


# Keep backward compatibility
get_hashtags = get_hashtags_static
