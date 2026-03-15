"""Telegram handlers for opportunity scanning and market analysis.

Commands:
  /scan — search for grants, hackathons, competitions
  /ideas — generate money-making ideas
  /market <topic> — quick market assessment
  /competitors <niche> — competitor analysis
  /proposal <name> — generate competition application
  /sources — list all known opportunity sources
"""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger("aizavod.bot.opportunities")

router = Router()

MAX_TG_MSG = 4000  # Telegram message limit ~4096


def _truncate(text: str, limit: int = MAX_TG_MSG) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n\n... (обрезано)"


@router.message(Command("scan"))
async def cmd_scan(message: Message):
    """Scan web for opportunities."""
    await message.answer("Сканирую конкурсы, гранты, хакатоны...")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()

    args = message.text.replace("/scan", "").strip()
    results = await scanner.scan_web(args or None)

    if not results:
        await message.answer("Ничего не найдено. Попробуй: /scan AI hackathon 2026")
        return

    lines = [f"Найдено: {len(results)} возможностей\n"]
    for i, r in enumerate(results[:10], 1):
        rel = "🟢" if r.relevance_score > 0.6 else "🟡" if r.relevance_score > 0.3 else "⚪"
        lines.append(f"{rel} <b>{i}. {r.title}</b>")
        if r.description:
            lines.append(f"   {r.description[:150]}")
        lines.append(f"   <a href=\"{r.url}\">Ссылка</a> | {r.type}\n")

    await message.answer(_truncate("\n".join(lines)), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("ideas"))
async def cmd_ideas(message: Message):
    """Generate money-making ideas."""
    await message.answer("Генерирую идеи для заработка...")

    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()

    context = message.text.replace("/ideas", "").strip()
    ideas = await scanner.generate_ideas(context)

    # Split long messages
    if len(ideas) > MAX_TG_MSG:
        parts = _split_message(ideas)
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(ideas)


@router.message(Command("market"))
async def cmd_market(message: Message):
    """Quick market assessment."""
    topic = message.text.replace("/market", "").strip()
    if not topic:
        await message.answer("Укажи тему: /market AI-боты для ресторанов")
        return

    await message.answer(f"Анализирую рынок: {topic}...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.quick_market_scan(topic)

    if len(result) > MAX_TG_MSG:
        parts = _split_message(result)
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(result)


@router.message(Command("competitors"))
async def cmd_competitors(message: Message):
    """Competitor analysis."""
    niche = message.text.replace("/competitors", "").strip()
    if not niche:
        await message.answer("Укажи нишу: /competitors SaaS автоматизация бизнеса РФ")
        return

    await message.answer(f"Анализирую конкурентов: {niche}...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.analyze_competitors(niche)

    if len(result) > MAX_TG_MSG:
        parts = _split_message(result)
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(result)


@router.message(Command("proposal"))
async def cmd_proposal(message: Message):
    """Generate competition application."""
    text = message.text.replace("/proposal", "").strip()
    if not text:
        await message.answer(
            "Формат: /proposal Название конкурса | Описание\n"
            "Пример: /proposal Цифровой прорыв | Хакатон по ИИ, приз 3 млн"
        )
        return

    parts = text.split("|", 1)
    name = parts[0].strip()
    desc = parts[1].strip() if len(parts) > 1 else ""

    await message.answer(f"Готовлю заявку на: {name}...")

    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    result = await analyzer.generate_proposal(name, desc)

    if len(result) > MAX_TG_MSG:
        msg_parts = _split_message(result)
        for part in msg_parts:
            await message.answer(part)
    else:
        await message.answer(result)


@router.message(Command("sources"))
async def cmd_sources(message: Message):
    """List opportunity sources."""
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    summary = await scanner.scan_sources_summary()
    await message.answer(summary, parse_mode="HTML")


def _split_message(text: str, limit: int = MAX_TG_MSG) -> list[str]:
    """Split long text into multiple messages at paragraph boundaries."""
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    current = ""

    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            if current:
                parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        parts.append(current)

    return parts
