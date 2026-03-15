"""DM Manager — read, categorize, and notify about Instagram DMs.

Mode: READ-ONLY. No auto-replies.
- Reads new DMs via instagrapi
- Categorizes each DM (fan / brand_inquiry / spam / question) using Claude
- Sends notifications to admin via Telegram bot:
  - brand_inquiry → immediate notification + brand evaluation + suggested rate
  - fan → hourly summary (count + themes)
  - question → notification + suggested draft reply
  - spam → silent archive, log only
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
    DMCategory,
    DMConversation,
    DMMessage,
    SystemSettings,
)

logger = logging.getLogger("aizavod.dm_manager")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


DM_CATEGORIZE_PROMPT = """Ты — AI-ассистент, который категоризирует входящие DM для Instagram-блогера @nika_flexx.

Сообщение от @{username}:
"{message_text}"

Контекст предыдущих сообщений в этом треде:
{thread_context}

Категории:
- fan: фан-сообщение, комплимент, реакция на контент
- brand_inquiry: предложение о рекламе, сотрудничестве, партнёрстве от бренда/агентства
- spam: спам, боты, мошенничество, неуместное
- question: вопрос по теме контента, просьба совета, запрос информации

Ответь ТОЛЬКО в формате JSON:
{{
  "category": "fan|brand_inquiry|spam|question",
  "confidence": 0.0-1.0,
  "summary": "краткое резюме сообщения (1 предложение)",
  "priority": 0-10,
  "suggested_reply": "предложенный черновик ответа (для question/brand_inquiry) или null"
}}"""


async def process_dm_inbox(character: Character) -> dict:
    """Main DM processing loop: fetch → categorize → notify.

    Returns summary of processed messages.
    """
    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()

        # Fetch new DMs
        new_messages = await _fetch_new_dms(character, db)
        if not new_messages:
            return {"processed": 0, "categories": {}}

        # Categorize each message
        category_counts = {}
        brand_alerts = []
        question_alerts = []

        for msg_data in new_messages:
            result = await _categorize_dm(msg_data, db)
            cat = result.get("category", "uncategorized")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            if cat == "brand_inquiry":
                brand_alerts.append({
                    "username": msg_data["username"],
                    "summary": result.get("summary", ""),
                    "suggested_reply": result.get("suggested_reply"),
                    "priority": result.get("priority", 5),
                })
            elif cat == "question":
                question_alerts.append({
                    "username": msg_data["username"],
                    "summary": result.get("summary", ""),
                    "suggested_reply": result.get("suggested_reply"),
                })

        db.commit()

        # Send notifications
        if brand_alerts and settings and settings.dm_notify_brands_immediately:
            await _notify_brand_inquiries(brand_alerts)

        if question_alerts:
            await _notify_questions(question_alerts)

        # Check if it's time for fan summary
        if category_counts.get("fan", 0) > 0 and settings:
            await _maybe_send_fan_summary(character, settings, db)

        logger.info(
            "Processed %d DMs: %s",
            len(new_messages),
            json.dumps(category_counts),
        )

        return {
            "processed": len(new_messages),
            "categories": category_counts,
            "brand_alerts": len(brand_alerts),
            "question_alerts": len(question_alerts),
        }

    finally:
        db.close()


async def _fetch_new_dms(character: Character, db) -> list[dict]:
    """Fetch new DMs from Instagram via instagrapi."""
    try:
        from services.instagram_client import get_instagram_client
        ig = get_instagram_client()
        threads = await ig.get_direct_messages(limit=20)
    except Exception as e:
        logger.warning("Failed to fetch DMs: %s", e)
        return []

    new_messages = []

    for thread in threads:
        thread_id = str(thread.get("thread_id", ""))
        if not thread_id:
            continue

        # Get or create conversation
        conv = (
            db.query(DMConversation)
            .filter(DMConversation.platform_thread_id == thread_id)
            .first()
        )

        if not conv:
            conv = DMConversation(
                character_id=character.id,
                platform_thread_id=thread_id,
                user_id=str(thread.get("user_id", "")),
                username=thread.get("username", ""),
            )
            db.add(conv)
            db.flush()

        # Process messages in thread
        for msg in thread.get("messages", []):
            msg_id = str(msg.get("id", ""))
            if not msg_id:
                continue

            # Skip if already processed
            existing = (
                db.query(DMMessage)
                .filter(DMMessage.platform_message_id == msg_id)
                .first()
            )
            if existing:
                continue

            direction = "inbound" if msg.get("is_from_user", True) else "outbound"
            text = msg.get("text", "")

            dm_msg = DMMessage(
                conversation_id=conv.id,
                direction=direction,
                text=text,
                platform_message_id=msg_id,
            )
            db.add(dm_msg)

            if direction == "inbound" and text:
                conv.unread_count = (conv.unread_count or 0) + 1
                new_messages.append({
                    "conversation_id": conv.id,
                    "username": conv.username,
                    "text": text,
                    "thread_id": thread_id,
                })

    return new_messages


async def _categorize_dm(msg_data: dict, db) -> dict:
    """Categorize a single DM using Claude."""
    cfg = get_anthropic_config()
    client = _get_client()

    # Get thread context
    conv = db.query(DMConversation).get(msg_data["conversation_id"])
    recent_msgs = (
        db.query(DMMessage)
        .filter(DMMessage.conversation_id == conv.id)
        .order_by(DMMessage.created_at.desc())
        .limit(5)
        .all()
    )
    thread_context = "\n".join(
        f"{'→' if m.direction == 'outbound' else '←'} {m.text[:200]}"
        for m in reversed(recent_msgs)
    ) or "First message in thread"

    prompt = DM_CATEGORIZE_PROMPT.format(
        username=msg_data["username"],
        message_text=msg_data["text"][:500],
        thread_context=thread_context,
    )

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse DM categorization: %s", response_text[:200])
        result = {"category": "uncategorized", "confidence": 0.0, "summary": "", "priority": 0}

    # Update conversation category
    cat_str = result.get("category", "uncategorized")
    try:
        category = DMCategory(cat_str)
    except ValueError:
        category = DMCategory.UNCATEGORIZED

    conv.category = category
    conv.priority = result.get("priority", 0)

    # Update latest message categorization
    latest_msg = (
        db.query(DMMessage)
        .filter(DMMessage.conversation_id == conv.id)
        .order_by(DMMessage.created_at.desc())
        .first()
    )
    if latest_msg:
        latest_msg.categorized_as = cat_str

    logger.info(
        "DM from @%s categorized as %s (confidence=%.2f)",
        msg_data["username"],
        cat_str,
        result.get("confidence", 0.0),
    )

    return result


async def _notify_brand_inquiries(alerts: list[dict]) -> None:
    """Send immediate Telegram notifications for brand inquiries."""
    try:
        from telegram_bot.bot_instance import get_bot
        from backend.config import get_telegram_config

        bot = get_bot()
        cfg = get_telegram_config()

        for admin_id in cfg.admin_ids:
            for alert in alerts:
                text = (
                    f"🏢 *Brand Inquiry*\n\n"
                    f"From: @{alert['username']}\n"
                    f"Summary: {alert['summary']}\n"
                    f"Priority: {'🔴' if alert['priority'] >= 8 else '🟡' if alert['priority'] >= 5 else '🟢'} "
                    f"{alert['priority']}/10\n"
                )
                if alert.get("suggested_reply"):
                    text += f"\nSuggested reply:\n_{alert['suggested_reply']}_"

                await bot.send_message(int(admin_id), text, parse_mode="Markdown")

    except Exception as e:
        logger.warning("Failed to send brand inquiry notification: %s", e)


async def _notify_questions(alerts: list[dict]) -> None:
    """Send Telegram notifications for questions."""
    try:
        from telegram_bot.bot_instance import get_bot
        from backend.config import get_telegram_config

        bot = get_bot()
        cfg = get_telegram_config()

        for admin_id in cfg.admin_ids:
            for alert in alerts:
                text = (
                    f"❓ *DM Question*\n\n"
                    f"From: @{alert['username']}\n"
                    f"Summary: {alert['summary']}\n"
                )
                if alert.get("suggested_reply"):
                    text += f"\nDraft reply:\n_{alert['suggested_reply']}_"

                await bot.send_message(int(admin_id), text, parse_mode="Markdown")

    except Exception as e:
        logger.warning("Failed to send question notification: %s", e)


async def _maybe_send_fan_summary(
    character: Character,
    settings: SystemSettings,
    db,
) -> None:
    """Send periodic fan DM summary if interval has passed."""
    interval_hours = settings.dm_summary_interval_hours or 1
    cutoff = datetime.utcnow() - timedelta(hours=interval_hours)

    # Check if we already sent a summary recently
    recent_fan_convs = (
        db.query(DMConversation)
        .filter(DMConversation.character_id == character.id)
        .filter(DMConversation.category == DMCategory.FAN)
        .filter(DMConversation.updated_at >= cutoff)
        .filter(
            (DMConversation.notified_at.is_(None))
            | (DMConversation.notified_at < cutoff)
        )
        .all()
    )

    if not recent_fan_convs:
        return

    try:
        from telegram_bot.bot_instance import get_bot
        from backend.config import get_telegram_config

        bot = get_bot()
        cfg = get_telegram_config()

        fan_count = len(recent_fan_convs)
        usernames = [c.username for c in recent_fan_convs[:10]]

        text = (
            f"💬 *Fan DM Summary*\n\n"
            f"New fan messages: {fan_count}\n"
            f"From: {', '.join(f'@{u}' for u in usernames)}"
        )
        if fan_count > 10:
            text += f"\n...and {fan_count - 10} more"

        for admin_id in cfg.admin_ids:
            await bot.send_message(int(admin_id), text, parse_mode="Markdown")

        # Mark as notified
        for conv in recent_fan_convs:
            conv.notified_at = datetime.utcnow()

    except Exception as e:
        logger.warning("Failed to send fan DM summary: %s", e)


async def generate_dm_summary(character: Character) -> dict:
    """Generate a full DM summary for admin dashboard."""
    db = SessionLocal()
    try:
        convs = (
            db.query(DMConversation)
            .filter(DMConversation.character_id == character.id)
            .order_by(DMConversation.updated_at.desc())
            .limit(50)
            .all()
        )

        by_category = {}
        for conv in convs:
            cat = conv.category.value
            by_category.setdefault(cat, []).append({
                "username": conv.username,
                "unread": conv.unread_count,
                "priority": conv.priority,
            })

        total_unread = sum(c.unread_count or 0 for c in convs)

        return {
            "total_conversations": len(convs),
            "total_unread": total_unread,
            "by_category": {
                cat: {"count": len(items), "items": items[:5]}
                for cat, items in by_category.items()
            },
        }

    finally:
        db.close()
