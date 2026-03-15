"""Управление агентом — статус, сделки, ЛС."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import httpx
from telegram_bot.config import get_backend_url, get_backend_api_key

router = Router()


async def _api(method: str, path: str, json_body: dict = None) -> dict:
    url = f"{get_backend_url()}{path}"
    headers = {}
    api_key = get_backend_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, json=json_body, timeout=30)
        resp.raise_for_status()
        return resp.json()


# ─── Статус агента ───────────────────────────────────────────────────────


@router.message(Command("agent"))
async def cmd_agent_status(message: Message):
    try:
        status = await _api("GET", "/admin/api/agent/status")

        text = (
            f"🤖 *Статус агента*\n\n"
            f"Модель: `{status['model']}`\n"
            f"Решений сегодня: {status['decisions_today']}/{status['max_daily_decisions']}\n"
            f"Осталось: {status['decisions_remaining']}\n"
            f"Ошибок сегодня: {status['errors_today']}\n"
            f"Последнее действие: {status.get('last_action', 'нет')}\n"
            f"Последнее решение: {status.get('last_decision_at', 'никогда')}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Запустить цикл", callback_data="agent_trigger")],
            [InlineKeyboardButton(text="📋 Последние решения", callback_data="agent_decisions")],
            [InlineKeyboardButton(text="💬 Сводка ЛС", callback_data="agent_dms")],
            [InlineKeyboardButton(text="💼 Сделки", callback_data="agent_deals")],
        ])

        await message.answer(text, reply_markup=kb)
    except Exception as e:
        await message.answer(f"Ошибка получения статуса агента: {e}")


@router.callback_query(F.data == "agent_trigger")
async def cb_agent_trigger(callback: CallbackQuery):
    await callback.answer("Запускаю цикл агента...")
    try:
        result = await _api("POST", "/admin/api/agent/trigger", {"task_type": "manual"})
        actions = result.get("actions", 0)
        await callback.message.answer(f"✅ Цикл агента завершён: {actions} действий")
    except Exception as e:
        await callback.message.answer(f"Ошибка запуска агента: {e}")


@router.callback_query(F.data == "agent_decisions")
async def cb_agent_decisions(callback: CallbackQuery):
    await callback.answer()
    try:
        decisions = await _api("GET", "/admin/api/agent/decisions?limit=5")

        if not decisions:
            await callback.message.answer("Решений агента ещё нет.")
            return

        lines = ["📋 *Последние решения агента*\n"]
        for d in decisions:
            status = "✅" if d["executed"] else "❌"
            lines.append(
                f"{status} *{d['task_type']}* (увер.: {d['confidence_score']:.2f})\n"
                f"   {d.get('reasoning', '')[:100]}\n"
                f"   _{d['created_at']}_\n"
            )

        await callback.message.answer("\n".join(lines))
    except Exception as e:
        await callback.message.answer(f"Ошибка получения решений: {e}")


# ─── ЛС ─────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "agent_dms")
async def cb_agent_dms(callback: CallbackQuery):
    await callback.answer()
    try:
        summary = await _api("GET", "/admin/api/dms/summary")

        text = (
            f"💬 *Сводка ЛС*\n\n"
            f"Всего разговоров: {summary['total_conversations']}\n"
            f"Непрочитанных: {summary['total_unread']}\n\n"
        )

        cat_labels = {
            "fan": "💛 Фанаты",
            "brand_inquiry": "🏢 Бренды",
            "spam": "🚫 Спам",
            "question": "❓ Вопросы",
            "uncategorized": "📨 Прочее",
        }

        for cat, data in summary.get("by_category", {}).items():
            label = cat_labels.get(cat, f"📨 {cat}")
            text += f"{label}: {data['count']}\n"

        await callback.message.answer(text)
    except Exception as e:
        await callback.message.answer(f"Ошибка получения ЛС: {e}")


@router.message(Command("dms"))
async def cmd_dms(message: Message):
    try:
        convs = await _api("GET", "/admin/api/dms/conversations?limit=10")

        if not convs:
            await message.answer("Разговоров в ЛС ещё нет.")
            return

        cat_labels = {
            "fan": "💛 фанат",
            "brand_inquiry": "🏢 бренд",
            "spam": "🚫 спам",
            "question": "❓ вопрос",
        }

        lines = ["💬 *Последние ЛС*\n"]
        for c in convs:
            label = cat_labels.get(c["category"], f"📨 {c['category']}")
            unread = f" ({c['unread_count']} новых)" if c["unread_count"] > 0 else ""
            lines.append(f"{label} @{c['username']}{unread}")

        await message.answer("\n".join(lines))
    except Exception as e:
        await message.answer(f"Ошибка получения ЛС: {e}")


# ─── Сделки ──────────────────────────────────────────────────────────────


@router.callback_query(F.data == "agent_deals")
async def cb_agent_deals(callback: CallbackQuery):
    await callback.answer()
    try:
        deals = await _api("GET", "/admin/api/deals/?limit=10")

        if not deals:
            await callback.message.answer("Рекламных сделок ещё нет.")
            return

        status_labels = {
            "detected": "🔍 обнаружена",
            "evaluating": "⏳ оценка",
            "awaiting_approval": "⚠️ ждёт одобрения",
            "proposal_sent": "📤 предложение отправлено",
            "negotiating": "🤝 переговоры",
            "completed": "✅ завершена",
            "rejected": "❌ отклонена",
        }

        lines = ["💼 *Рекламные сделки*\n"]
        for d in deals:
            label = status_labels.get(d["status"], f"📋 {d['status']}")

            lines.append(
                f"{label} *{d['brand_name']}*\n"
                f"   Совпадение: {'⭐' * int(d['brand_fit_score'] * 5)} | Цена: ${d['proposed_price_usd']:.0f}"
            )

            if d["status"] == "awaiting_approval":
                lines.append(f"   → /approve\\_deal {d['id']} | /reject\\_deal {d['id']}")

        await callback.message.answer("\n".join(lines))
    except Exception as e:
        await callback.message.answer(f"Ошибка получения сделок: {e}")


@router.message(Command("approve_deal"))
async def cmd_approve_deal(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Формат: /approve\\_deal <id\\_сделки>")
        return

    try:
        deal_id = int(parts[1])
        result = await _api("POST", "/admin/api/deals/approve", {"deal_id": deal_id})

        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
        else:
            await message.answer(f"✅ Сделка {deal_id} одобрена! Предложение готово к отправке.")
    except Exception as e:
        await message.answer(f"Ошибка одобрения сделки: {e}")


@router.message(Command("reject_deal"))
async def cmd_reject_deal(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Формат: /reject\\_deal <id\\_сделки> [причина]")
        return

    try:
        deal_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else ""
        result = await _api("POST", "/admin/api/deals/reject", {"deal_id": deal_id, "reason": reason})

        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
        else:
            await message.answer(f"✅ Сделка {deal_id} отклонена.")
    except Exception as e:
        await message.answer(f"Ошибка отклонения сделки: {e}")
