"""Ad Deal Manager — evaluate brands, generate proposals, manage deal lifecycle.

Deal lifecycle:
  DETECTED → EVALUATING → AWAITING_APPROVAL → PROPOSAL_SENT → NEGOTIATING →
  BRIEF_RECEIVED → CONTENT_CREATING → PUBLISHED → PAYMENT_PENDING → COMPLETED

Key principle: AWAITING_APPROVAL step sends full package to admin via Telegram.
Nothing is sent to the brand without admin approval.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.database import SessionLocal
from backend.models import (
    AdDeal,
    AdDealStatus,
    Character,
    DailyMetrics,
    PostAnalytics,
    SystemSettings,
)

logger = logging.getLogger("aizavod.ad_manager")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


BRAND_FIT_PROMPT = """Ты — рекламный менеджер Instagram-блогера @nika_flexx.

Ника Флекс — AI-инфлюенсер, ниша: {niche}.
Подписчики: {followers}
Средний ER: {avg_er:.2f}%
Контент: фитнес, лайфстайл, мотивация

Бренд предлагает сотрудничество:
- Бренд: {brand_name}
- Username: @{brand_username}
- Сообщение: {brand_message}

Оцени:
1. Brand fit (0.0-1.0): насколько бренд подходит аудитории Ники
2. Риски (репутационные, legal, audience mismatch)
3. Рекомендуемая ставка (на основе метрик аккаунта)
4. Предложенные deliverables

Ответь ТОЛЬКО в формате JSON:
{{
  "brand_fit_score": 0.0-1.0,
  "fit_reasoning": "почему подходит или не подходит",
  "risks": ["риск1", "риск2"],
  "recommended_rate_usd": 0,
  "rate_breakdown": "объяснение ставки",
  "suggested_deliverables": ["1 Reel + упоминание", "3 Stories с свайпом"],
  "recommendation": "accept|negotiate|decline",
  "counter_proposal": "если negotiate — что предложить"
}}"""


PROPOSAL_DRAFT_PROMPT = """Ты — профессиональный менеджер по рекламе для @nika_flexx.

Составь коммерческое предложение для бренда:
- Бренд: {brand_name}
- Ниша Ники: {niche}
- Подписчики: {followers}
- Средний ER: {avg_er:.2f}%
- Средний reach: {avg_reach}
- Ставка: ${rate} USD
- Deliverables: {deliverables}

Тон: профессиональный, но дружелюбный. На английском языке.
Длина: 3-5 абзацев.

Ответь ТОЛЬКО текстом предложения (без JSON, без форматирования)."""


async def evaluate_brand_fit(
    deal_id: int,
    character: Character,
    db,
) -> dict:
    """Evaluate how well a brand fits the character's audience."""
    cfg = get_anthropic_config()
    client = _get_client()

    deal = db.query(AdDeal).get(deal_id)
    if not deal:
        return {"error": "Deal not found"}

    deal.status = AdDealStatus.EVALUATING
    db.commit()

    # Get metrics
    metrics = _get_account_metrics(db)

    # Get brand message context
    brand_message = ""
    if deal.dm_conversation_id:
        from backend.models import DMMessage
        msgs = (
            db.query(DMMessage)
            .filter(DMMessage.conversation_id == deal.dm_conversation_id)
            .filter(DMMessage.direction == "inbound")
            .order_by(DMMessage.created_at.desc())
            .limit(5)
            .all()
        )
        brand_message = "\n".join(m.text[:200] for m in reversed(msgs))

    prompt = BRAND_FIT_PROMPT.format(
        niche=character.niche_description,
        followers=metrics["followers"],
        avg_er=metrics["avg_er"],
        brand_name=deal.brand_name,
        brand_username=deal.brand_username or "unknown",
        brand_message=brand_message or "No message context",
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
        logger.error("Failed to parse brand fit: %s", response_text[:200])
        return {"error": "parse_failed"}

    # Update deal
    deal.brand_fit_score = result.get("brand_fit_score", 0.0)
    deal.market_rate_usd = result.get("recommended_rate_usd", 0.0)
    deal.proposed_price_usd = result.get("recommended_rate_usd", 0.0)
    deal.deliverables = json.dumps(result.get("suggested_deliverables", []), ensure_ascii=False)
    deal.notes = json.dumps({
        "fit_reasoning": result.get("fit_reasoning", ""),
        "risks": result.get("risks", []),
        "recommendation": result.get("recommendation", ""),
    }, ensure_ascii=False)

    # Move to awaiting approval
    deal.status = AdDealStatus.AWAITING_APPROVAL
    db.commit()

    # Notify admin
    await _notify_deal_for_approval(deal, result)

    logger.info(
        "Brand %s evaluated: fit=%.2f, rate=$%.0f, recommendation=%s",
        deal.brand_name,
        deal.brand_fit_score,
        deal.proposed_price_usd,
        result.get("recommendation", "unknown"),
    )

    return {
        "deal_id": deal.id,
        "brand_fit_score": deal.brand_fit_score,
        "recommended_rate": deal.proposed_price_usd,
        "recommendation": result.get("recommendation", "unknown"),
    }


async def generate_proposal_draft(deal_id: int, character: Character) -> str:
    """Generate a proposal draft for approved deal."""
    cfg = get_anthropic_config()
    client = _get_client()
    db = SessionLocal()

    try:
        deal = db.query(AdDeal).get(deal_id)
        if not deal:
            return ""

        metrics = _get_account_metrics(db)

        prompt = PROPOSAL_DRAFT_PROMPT.format(
            brand_name=deal.brand_name,
            niche=character.niche_description,
            followers=metrics["followers"],
            avg_er=metrics["avg_er"],
            avg_reach=metrics["avg_reach"],
            rate=deal.proposed_price_usd,
            deliverables=deal.deliverables,
        )

        message = await client.messages.create(
            model=cfg.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        proposal = message.content[0].text.strip()
        deal.proposal_draft = proposal
        db.commit()

        logger.info("Generated proposal draft for %s", deal.brand_name)
        return proposal

    finally:
        db.close()


async def approve_deal(deal_id: int) -> dict:
    """Admin approves a deal — generate proposal and prepare for sending."""
    db = SessionLocal()
    try:
        deal = db.query(AdDeal).get(deal_id)
        if not deal:
            return {"error": "Deal not found"}

        if deal.status != AdDealStatus.AWAITING_APPROVAL:
            return {"error": f"Deal is in status {deal.status.value}, expected awaiting_approval"}

        # Generate proposal if not yet done
        if not deal.proposal_draft:
            from services.character_manager import get_active_character
            character = get_active_character(db)
            if character:
                await generate_proposal_draft(deal_id, character)

        deal.status = AdDealStatus.PROPOSAL_SENT
        db.commit()

        logger.info("Deal %d approved, proposal ready for %s", deal_id, deal.brand_name)
        return {"deal_id": deal_id, "status": "proposal_sent"}

    finally:
        db.close()


async def reject_deal(deal_id: int, reason: str = "") -> dict:
    """Admin rejects a deal."""
    db = SessionLocal()
    try:
        deal = db.query(AdDeal).get(deal_id)
        if not deal:
            return {"error": "Deal not found"}

        deal.status = AdDealStatus.REJECTED
        if reason:
            existing_notes = json.loads(deal.notes or "{}")
            existing_notes["rejection_reason"] = reason
            deal.notes = json.dumps(existing_notes, ensure_ascii=False)

        db.commit()

        logger.info("Deal %d rejected: %s", deal_id, deal.brand_name)
        return {"deal_id": deal_id, "status": "rejected"}

    finally:
        db.close()


def create_deal_from_dm(
    character_id: int,
    conversation_id: int,
    brand_name: str,
    brand_username: str = "",
) -> int:
    """Create a new ad deal from a DM conversation."""
    db = SessionLocal()
    try:
        deal = AdDeal(
            character_id=character_id,
            dm_conversation_id=conversation_id,
            brand_name=brand_name,
            brand_username=brand_username,
            status=AdDealStatus.DETECTED,
        )
        db.add(deal)
        db.commit()

        logger.info("Created deal from DM: %s (@%s)", brand_name, brand_username)
        return deal.id

    finally:
        db.close()


async def _notify_deal_for_approval(deal: AdDeal, evaluation: dict) -> None:
    """Send deal evaluation to admin via Telegram for approval."""
    try:
        from telegram_bot.bot_instance import get_bot
        from backend.config import get_telegram_config

        bot = get_bot()
        cfg = get_telegram_config()

        recommendation = evaluation.get("recommendation", "unknown")
        emoji = {"accept": "✅", "negotiate": "🤝", "decline": "❌"}.get(recommendation, "❓")

        text = (
            f"💼 *Ad Deal Evaluation*\n\n"
            f"Brand: *{deal.brand_name}*"
            f"{f' (@{deal.brand_username})' if deal.brand_username else ''}\n"
            f"Brand Fit: {'⭐' * int(deal.brand_fit_score * 5)} "
            f"({deal.brand_fit_score:.2f})\n"
            f"Rate: ${deal.proposed_price_usd:.0f}\n"
            f"Recommendation: {emoji} {recommendation}\n\n"
            f"Reasoning: {evaluation.get('fit_reasoning', '')}\n\n"
            f"Deliverables: {deal.deliverables}\n\n"
            f"Risks: {', '.join(evaluation.get('risks', ['none']))}\n\n"
            f"Reply with:\n"
            f"/approve\\_deal {deal.id}\n"
            f"/reject\\_deal {deal.id} [reason]"
        )

        for admin_id in cfg.admin_ids:
            await bot.send_message(int(admin_id), text, parse_mode="Markdown")

    except Exception as e:
        logger.warning("Failed to send deal notification: %s", e)


def _get_account_metrics(db) -> dict:
    """Get basic account metrics for prompts."""
    from sqlalchemy import func

    latest = db.query(DailyMetrics).order_by(DailyMetrics.date.desc()).first()
    avg_er = db.query(func.avg(PostAnalytics.engagement_rate)).scalar() or 0.0
    avg_reach = db.query(func.avg(PostAnalytics.reach)).scalar() or 0

    return {
        "followers": latest.followers_count if latest else 0,
        "avg_er": avg_er,
        "avg_reach": int(avg_reach),
    }
