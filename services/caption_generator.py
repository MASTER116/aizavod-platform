"""Bilingual caption generator using Claude AI."""
from __future__ import annotations

import json
import logging
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.models import Character, ContentCategory

logger = logging.getLogger("aizavod.caption_generator")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


VIRAL_CAPTION_PROMPT = """Ты — {name}, блогер ({niche_description}).

Твой стиль: {tone}
Использование эмодзи: {emoji_style}
Личность: {personality}
Платформа: {platform}
Тип контента: {content_type}

Напиши ВИРУСНУЮ подпись к посту на ДВУХ языках (русский и английский).

Категория: {category}
Описание: {description}

=== ПРАВИЛА ВИРУСНОЙ ПОДПИСИ ===

1. ПЕРВАЯ СТРОКА = HOOK (крючок). Это САМОЕ ВАЖНОЕ. Человек решает читать дальше за 1 секунду.
   Типы хуков:
   - curiosity_gap: "То, что произошло дальше, меня шокировало..."
   - before_after: "3 месяца назад я не могла даже..."
   - controversial_opinion: "Непопулярное мнение: ..."
   - relatable_struggle: "Кто ещё ненавидит когда..."
   - tutorial_teaser: "Секрет, который мне стоил 100К..."
   - trend_remix: переосмысление текущего тренда

2. СЕРЕДИНА — ценность + микро-CTA (вопрос для комментариев)

3. КОНЕЦ — CTA зависит от типа контента:
   - Reel → "Сохрани, чтобы не потерять 🔖" (оптимизация saves)
   - Carousel → "Свайпни вправо — самое важное на последнем слайде ➡️"
   - Photo → "Поставь ❤️ если согласна"
   - Story → краткий текст + стикер-вопрос

=== ТРЕБОВАНИЯ К ТЕКСТУ ===
- Русская подпись: 3-6 предложений, hook → value → micro-CTA → main CTA
- Английская подпись: тот же смысл, натуральный английский
- Звучит как настоящая девушка-блогер, НЕ как AI
- Эмодзи: {emoji_style} (не переборщи, максимум 4-5 на подпись)
- НЕ используй клише типа "всем привет", "доброе утро", "лайк тайм"

Ответь ТОЛЬКО в формате JSON (без markdown):
{{
  "caption_ru": "...",
  "caption_en": "...",
  "hook_type": "curiosity_gap|before_after|controversial_opinion|relatable_struggle|tutorial_teaser|trend_remix",
  "hook_text": "первая строка хука (только русский)",
  "predicted_engagement": 0.0-1.0
}}

predicted_engagement: оценка вирусности от 0.0 до 1.0 (1.0 = максимальный вирусный потенциал).
Учитывай: эмоциональный триггер, спорность, shareability, save-worthiness."""


async def generate_caption(
    character: Character,
    category: ContentCategory,
    description: str,
    language: str = "both",
    platform: str = "instagram",
    content_type: str = "photo",
) -> dict:
    """Generate a viral caption with hook analysis.

    Args:
        content_type: "reel", "carousel", "photo", or "story"

    Returns dict with keys: caption_ru, caption_en, hook_type,
    hook_text, predicted_engagement.
    """
    cfg = get_anthropic_config()
    client = _get_client()

    from services.character_manager import get_character_prompt_context

    ctx = get_character_prompt_context(character)

    prompt = VIRAL_CAPTION_PROMPT.format(
        name=ctx["name"],
        niche_description=character.niche_description,
        tone=ctx["tone"],
        emoji_style=ctx["emoji_style"],
        personality=", ".join(ctx["personality"]) if ctx["personality"] else "friendly, energetic",
        platform=platform,
        content_type=content_type,
        category=category.value,
        description=description,
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse caption JSON: %s", response_text[:200])
        result = {
            "caption_ru": "",
            "caption_en": "",
            "hook_type": "curiosity_gap",
            "hook_text": "",
            "predicted_engagement": 0.0,
        }

    if language == "ru":
        result.pop("caption_en", None)
    elif language == "en":
        result.pop("caption_ru", None)

    logger.info(
        "Generated viral caption for %s %s (hook=%s, engagement=%.2f)",
        content_type,
        category.value,
        result.get("hook_type", "unknown"),
        result.get("predicted_engagement", 0.0),
    )
    return result


COMMENT_REPLY_PROMPT = """Ты — {name}, блогер ({niche_description}).
Стиль: {tone}, дружелюбный, позитивный.

Пользователь @{username} оставил комментарий под твоим постом:
"{comment_text}"

Контекст поста: {post_description}

Напиши короткий ответ (1-2 предложения) на том же языке, что и комментарий.
Будь дружелюбной и благодарной. Если вопрос — ответь по теме.
Если комплимент — поблагодари. Если негатив — ответь позитивно.

Ответь ТОЛЬКО текстом ответа, без кавычек и форматирования."""


async def generate_comment_reply(
    character: Character,
    username: str,
    comment_text: str,
    post_description: str = "",
) -> str:
    """Generate a contextual reply to an Instagram comment."""
    cfg = get_anthropic_config()
    client = _get_client()

    from services.character_manager import get_character_prompt_context

    ctx = get_character_prompt_context(character)

    prompt = COMMENT_REPLY_PROMPT.format(
        name=ctx["name"],
        niche_description=character.niche_description,
        tone=ctx["tone"],
        username=username,
        comment_text=comment_text,
        post_description=post_description,
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    reply = message.content[0].text.strip()
    logger.info("Generated reply to @%s: %s...", username, reply[:50])
    return reply
