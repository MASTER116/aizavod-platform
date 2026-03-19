"""Админ-панель: здоровье агентов, расходы, A/B тесты, metering, compliance, kill-switch."""

from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from telegram_bot.keyboards import admin_menu_kb, killswitch_kb, main_menu_kb

logger = logging.getLogger("aizavod.bot.admin_panel")

router = Router()


# ─── Меню админ-панели ─────────────────────────────────────────────────

@router.callback_query(F.data == "menu_admin")
async def cb_admin_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🔧 <b>Админ-панель Zavod-ii</b>\n\n"
        "Мониторинг, тесты, безопасность.",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


# ─── 1. Здоровье агентов ───────────────────────────────────────────────

@router.callback_query(F.data == "admin_health")
async def cb_health(callback: CallbackQuery):
    await callback.answer()
    from services.health_monitor import get_health_monitor
    hm = get_health_monitor()
    summary = hm.get_summary()

    lines = [
        "💚 <b>Здоровье агентов</b>\n",
        f"Всего: {summary['total_agents']}",
        f"✅ Healthy: {summary['healthy']}",
        f"⚠️ Degraded: {summary['degraded']}",
        f"❌ Unhealthy: {summary['unhealthy']}",
        f"☠️ Killed: {summary['killed']}",
    ]

    if summary["killed_agents"]:
        lines.append(f"\nKilled: {', '.join(summary['killed_agents'])}")

    # Per-agent details
    all_status = hm.get_all_status()
    if all_status:
        lines.append("\n<b>Детали:</b>")
        for s in all_status:
            if s:
                emoji = "✅" if s["is_alive"] else "☠️"
                lines.append(
                    f"{emoji} {s['name']}: {s['total_calls']} calls, "
                    f"err {s['error_rate']}, {s['avg_latency_ms']}ms"
                )

    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_menu_kb())


# ─── 2. Расходы и токены ───────────────────────────────────────────────

@router.callback_query(F.data == "admin_costs")
async def cb_costs(callback: CallbackQuery):
    await callback.answer()
    from services.conductor.observability import get_tracker
    tracker = get_tracker()
    summary = tracker.get_summary()

    lines = [
        "💵 <b>Расходы за сегодня</b>\n",
        f"Трейсов: {summary['total_traces']}",
        f"Расход: {summary['today_cost_usd']}",
        f"Порог алерта: {summary['today_alert_threshold']}",
        f"Активных агентов: {summary['active_agents']}",
        f"Пользователей: {summary['total_users_today']}",
    ]

    # Per-agent stats
    agent_stats = tracker.get_all_agent_stats()
    if agent_stats:
        lines.append("\n<b>По агентам:</b>")
        for s in agent_stats[:10]:
            lines.append(
                f"  {s['agent']}: {s['total_calls']} calls, "
                f"{s['total_cost_usd']}, {s['avg_latency_ms']}ms, "
                f"quality {s['avg_quality']}"
            )

    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_menu_kb())


# ─── 3. A/B эксперименты ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_ab")
async def cb_ab(callback: CallbackQuery):
    await callback.answer()
    from services.testing.ab_engine import get_ab_engine
    engine = get_ab_engine()
    experiments = engine.list_experiments()

    if not experiments:
        await callback.message.answer(
            "🧪 <b>A/B эксперименты</b>\n\nНет активных экспериментов.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb(),
        )
        return

    lines = ["🧪 <b>A/B эксперименты</b>\n"]
    for exp in experiments:
        status_emoji = {"running": "🔄", "completed": "✅", "promoted": "🏆", "draft": "📝"}.get(exp["status"], "❓")
        lines.append(
            f"{status_emoji} <b>{exp['agent']}</b> [{exp['status']}]\n"
            f"  Samples: {exp['samples']}\n"
            f"  Winner: {exp['winner'] or '—'} (p={exp['p_value'] or '—'})\n"
            f"  {exp['recommendation']}\n"
        )

    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_menu_kb())


# ─── 4. Metering (лимиты) ─────────────────────────────────────────────

@router.callback_query(F.data == "admin_metering")
async def cb_metering(callback: CallbackQuery):
    await callback.answer()
    from services.billing.metering import get_usage_meter
    meter = get_usage_meter()
    summary = meter.get_summary()

    lines = [
        "📊 <b>Metering</b>\n",
        f"Дата: {summary['date']}",
        f"Активных: {summary['active_users']}",
        f"Вызовов: {summary['total_calls_today']}",
        f"Расход: {summary['total_cost_today_usd']}",
    ]

    # Tier distribution
    dist = summary.get("tier_distribution", {})
    if any(dist.values()):
        lines.append("\n<b>По тарифам:</b>")
        for tier, count in dist.items():
            if count > 0:
                lines.append(f"  {tier.upper()}: {count}")

    # Per-user stats
    all_stats = meter.get_all_stats()
    if all_stats:
        lines.append("\n<b>Пользователи:</b>")
        for s in all_stats[:10]:
            lines.append(
                f"  ID {s['user_id']} [{s['tier']}]: "
                f"{s['calls']}/{s['calls_limit']} ({s['usage_percent']})"
            )

    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_menu_kb())


# ─── 5. Compliance аудит ───────────────────────────────────────────────

@router.callback_query(F.data == "admin_compliance")
async def cb_compliance(callback: CallbackQuery):
    await callback.answer()
    from services.compliance_agent import get_compliance_agent
    compliance = get_compliance_agent()

    # Data residency check
    storage = compliance.check_data_residency("Hetzner, Germany")
    audit = compliance.get_audit_log(limit=10)

    lines = [
        "🛡 <b>Compliance</b>\n",
        f"152-ФЗ хранение: {'✅ РФ' if storage['compliant'] else '❌ Зарубеж (' + storage['server_location'] + ')'}",
    ]

    if not storage["compliant"] and storage.get("violation"):
        v = storage["violation"]
        lines.append(f"  Штраф: {v['penalty']}")
        lines.append(f"  Рекомендация: {v['recommendation']}")

    if audit:
        lines.append(f"\n<b>Последние {len(audit)} действий:</b>")
        for entry in audit[-5:]:
            lines.append(f"  {entry['timestamp'][:16]} | {entry['agent']} | {entry['action']}")

    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_menu_kb())


# ─── 6. Kill-Switch ────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_killswitch")
async def cb_killswitch(callback: CallbackQuery):
    await callback.answer()
    from services.conductor.registry import AGENTS
    agent_names = [a.name for a in AGENTS]
    await callback.message.answer(
        "☠️ <b>Kill-Switch (DEADMAN)</b>\n\n"
        "Выбери агента для принудительной остановки.\n"
        "Остановленный агент не будет обрабатывать запросы.",
        parse_mode="HTML",
        reply_markup=killswitch_kb(agent_names),
    )


@router.callback_query(F.data.startswith("kill_"))
async def cb_kill_agent(callback: CallbackQuery):
    await callback.answer()
    agent_name = callback.data[5:]  # Remove "kill_" prefix

    from services.health_monitor import get_health_monitor
    hm = get_health_monitor()

    if hm.is_killed(agent_name):
        # Revive
        hm.revive(agent_name)
        await callback.message.answer(
            f"✅ Агент <b>{agent_name}</b> восстановлен.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb(),
        )
    else:
        # Kill
        hm.kill(agent_name, f"Manual kill via Telegram by {callback.from_user.id}")
        await callback.message.answer(
            f"☠️ Агент <b>{agent_name}</b> остановлен.\n"
            f"Нажми снова чтобы восстановить.",
            parse_mode="HTML",
            reply_markup=admin_menu_kb(),
        )
