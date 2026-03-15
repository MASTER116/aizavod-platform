"""Telegram handlers for agent management — status, deals, DMs."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import httpx
from telegram_bot.config import get_backend_url, get_backend_api_key

router = Router()


async def _api(method: str, path: str, json_body: dict = None) -> dict:
    """Call backend API."""
    url = f"{get_backend_url()}{path}"
    headers = {}
    api_key = get_backend_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, json=json_body, timeout=30)
        resp.raise_for_status()
        return resp.json()


# ─── Agent Status ─────────────────────────────────────────────────────────


@router.message(Command("agent"))
async def cmd_agent_status(message: Message):
    """Show agent orchestrator status."""
    try:
        status = await _api("GET", "/admin/api/agent/status")

        text = (
            f"🤖 *Agent Status*\n\n"
            f"Model: `{status['model']}`\n"
            f"Decisions today: {status['decisions_today']}/{status['max_daily_decisions']}\n"
            f"Remaining: {status['decisions_remaining']}\n"
            f"Errors today: {status['errors_today']}\n"
            f"Last action: {status.get('last_action', 'none')}\n"
            f"Last decision: {status.get('last_decision_at', 'never')}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Trigger Cycle", callback_data="agent_trigger")],
            [InlineKeyboardButton(text="📋 Recent Decisions", callback_data="agent_decisions")],
            [InlineKeyboardButton(text="💬 DM Summary", callback_data="agent_dms")],
            [InlineKeyboardButton(text="💼 Deals", callback_data="agent_deals")],
        ])

        await message.answer(text, reply_markup=kb)
    except Exception as e:
        await message.answer(f"❌ Failed to get agent status: {e}")


@router.callback_query(F.data == "agent_trigger")
async def cb_agent_trigger(callback: CallbackQuery):
    """Manually trigger agent cycle."""
    await callback.answer("Triggering agent cycle...")
    try:
        result = await _api("POST", "/admin/api/agent/trigger", {"task_type": "manual"})
        actions = result.get("actions", 0)
        await callback.message.answer(f"✅ Agent cycle completed: {actions} action(s)")
    except Exception as e:
        await callback.message.answer(f"❌ Agent trigger failed: {e}")


@router.callback_query(F.data == "agent_decisions")
async def cb_agent_decisions(callback: CallbackQuery):
    """Show recent agent decisions."""
    await callback.answer()
    try:
        decisions = await _api("GET", "/admin/api/agent/decisions?limit=5")

        if not decisions:
            await callback.message.answer("No agent decisions yet.")
            return

        lines = ["📋 *Recent Agent Decisions*\n"]
        for d in decisions:
            status = "✅" if d["executed"] else "❌"
            lines.append(
                f"{status} *{d['task_type']}* (conf: {d['confidence_score']:.2f})\n"
                f"   {d.get('reasoning', '')[:100]}\n"
                f"   _{d['created_at']}_\n"
            )

        await callback.message.answer("\n".join(lines))
    except Exception as e:
        await callback.message.answer(f"❌ Failed to get decisions: {e}")


# ─── DMs ──────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "agent_dms")
async def cb_agent_dms(callback: CallbackQuery):
    """Show DM summary."""
    await callback.answer()
    try:
        summary = await _api("GET", "/admin/api/dms/summary")

        text = (
            f"💬 *DM Summary*\n\n"
            f"Total conversations: {summary['total_conversations']}\n"
            f"Unread: {summary['total_unread']}\n\n"
        )

        for cat, data in summary.get("by_category", {}).items():
            emoji = {
                "fan": "💛", "brand_inquiry": "🏢",
                "spam": "🚫", "question": "❓",
                "uncategorized": "📨",
            }.get(cat, "📨")
            text += f"{emoji} {cat}: {data['count']}\n"

        await callback.message.answer(text)
    except Exception as e:
        await callback.message.answer(f"❌ Failed to get DMs: {e}")


@router.message(Command("dms"))
async def cmd_dms(message: Message):
    """Show DM conversations list."""
    try:
        convs = await _api("GET", "/admin/api/dms/conversations?limit=10")

        if not convs:
            await message.answer("No DM conversations yet.")
            return

        lines = ["💬 *Recent DMs*\n"]
        for c in convs:
            emoji = {
                "fan": "💛", "brand_inquiry": "🏢",
                "spam": "🚫", "question": "❓",
            }.get(c["category"], "📨")
            unread = f" ({c['unread_count']} new)" if c["unread_count"] > 0 else ""
            lines.append(f"{emoji} @{c['username']}{unread} — {c['category']}")

        await message.answer("\n".join(lines))
    except Exception as e:
        await message.answer(f"❌ Failed to get DMs: {e}")


# ─── Deals ────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "agent_deals")
async def cb_agent_deals(callback: CallbackQuery):
    """Show active ad deals."""
    await callback.answer()
    try:
        deals = await _api("GET", "/admin/api/deals/?limit=10")

        if not deals:
            await callback.message.answer("No ad deals yet.")
            return

        lines = ["💼 *Ad Deals*\n"]
        for d in deals:
            status_emoji = {
                "detected": "🔍", "evaluating": "⏳",
                "awaiting_approval": "⚠️", "proposal_sent": "📤",
                "negotiating": "🤝", "completed": "✅",
                "rejected": "❌",
            }.get(d["status"], "📋")

            lines.append(
                f"{status_emoji} *{d['brand_name']}* — {d['status']}\n"
                f"   Fit: {'⭐' * int(d['brand_fit_score'] * 5)} | Rate: ${d['proposed_price_usd']:.0f}"
            )

            if d["status"] == "awaiting_approval":
                lines.append(f"   → /approve\\_deal {d['id']} | /reject\\_deal {d['id']}")

        await callback.message.answer("\n".join(lines))
    except Exception as e:
        await callback.message.answer(f"❌ Failed to get deals: {e}")


@router.message(Command("approve_deal"))
async def cmd_approve_deal(message: Message):
    """Approve an ad deal: /approve_deal <deal_id>"""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /approve\\_deal <deal\\_id>")
        return

    try:
        deal_id = int(parts[1])
        result = await _api("POST", "/admin/api/deals/approve", {"deal_id": deal_id})

        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
        else:
            await message.answer(f"✅ Deal {deal_id} approved! Proposal ready to send.")
    except Exception as e:
        await message.answer(f"❌ Failed to approve deal: {e}")


@router.message(Command("reject_deal"))
async def cmd_reject_deal(message: Message):
    """Reject an ad deal: /reject_deal <deal_id> [reason]"""
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Usage: /reject\\_deal <deal\\_id> [reason]")
        return

    try:
        deal_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else ""
        result = await _api("POST", "/admin/api/deals/reject", {"deal_id": deal_id, "reason": reason})

        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
        else:
            await message.answer(f"✅ Deal {deal_id} rejected.")
    except Exception as e:
        await message.answer(f"❌ Failed to reject deal: {e}")
