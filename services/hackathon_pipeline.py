"""Hackathon Pipeline v2 — REAL end-to-end hackathon participation.

Uses Claude Code CLI (`claude -p`) for all AI tasks instead of API.

Full cycle:
1. DISCOVER  — find hackathons on DevPost with enough time
2. SELECT    — Claude picks the most winnable hackathon
3. ANALYZE   — deep analysis of rules, requirements, judging criteria
4. BUILD     — Claude Code generates real MVP project
5. DEPLOY    — push to GitHub via PyGithub, enable Pages
6. MATERIALS — generate screenshots via Playwright
7. SUBMIT    — submit on DevPost via Playwright
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path

import httpx

logger = logging.getLogger("aizavod.hackathon_pipeline")

MIN_HOURS_BEFORE_DEADLINE = 2


# ─── Claude CLI helper ───────────────────────────────────────────────────────


def _run_claude(prompt: str, cwd: str | None = None, timeout: int = 300,
                allow_tools: bool = False) -> str:
    """Run Claude Code CLI with a prompt and return output."""
    cmd = ["claude", "-p", prompt]
    if allow_tools:
        cmd.append("--dangerously-skip-permissions")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and not output:
            output = result.stderr.strip()
        return output
    except subprocess.TimeoutExpired:
        return "ERROR: timeout"
    except Exception as e:
        return f"ERROR: {e}"


def _extract_json(text: str) -> dict | list | None:
    """Extract JSON from Claude output."""
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for pattern in [
        re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL),
        re.compile(r"(\[(?:[^\[\]]*(?:\[.*?\])*[^\[\]]*)*\])", re.DOTALL),
        re.compile(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", re.DOTALL),
    ]:
        m = pattern.search(text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    return None


# ─── Data Classes ─────────────────────────────────────────────────────────────


class HackathonInfo:
    def __init__(self, title, url, prize, deadline, description, participants=0):
        self.title = title
        self.url = url
        self.prize = prize
        self.deadline = deadline
        self.description = description
        self.participants = participants
        self.hours_left = self._parse_hours_left(deadline)
        self._project_type = "web_app"
        self._confidence = 0.5
        self._reason = ""

    @staticmethod
    def _parse_hours_left(deadline: str) -> float:
        if not deadline:
            return 999
        dl = deadline.lower()
        m = re.search(r"about\s+(\d+)\s+hours?", dl)
        if m:
            return float(m.group(1))
        m = re.search(r"(\d+)\s+days?", dl)
        if m:
            return float(m.group(1)) * 24
        m = re.search(r"(\d+)\s+months?", dl)
        if m:
            return float(m.group(1)) * 30 * 24
        m = re.search(r"over\s+(\d+)\s+days?", dl)
        if m:
            return float(m.group(1)) * 24
        return 999


# ─── Main Pipeline ────────────────────────────────────────────────────────────


async def launch_hackathon_pipeline(
    max_hackathons: int = 10,
    min_prize: int = 1,
    min_hours: int = 12,
    notify_callback=None,
) -> str:
    """Launch the full hackathon pipeline."""
    start_time = time.time()
    results = []

    async def notify(msg: str):
        logger.info(msg)
        if notify_callback:
            try:
                await notify_callback(msg)
            except Exception:
                pass

    await notify("🔍 Этап 1/7: Поиск хакатонов на DevPost...")

    hackathons = await _discover_hackathons()
    if not hackathons:
        return "❌ Не найдено открытых хакатонов на DevPost."

    await notify(f"📊 Найдено {len(hackathons)} открытых хакатонов")

    await notify("🎯 Этап 2/7: Отбор лучших хакатонов...")
    selected = await _select_hackathons(hackathons, max_hackathons, min_prize, min_hours)

    if not selected:
        return "❌ Нет подходящих хакатонов (все слишком скоро или без призов)."

    summary_lines = [
        f"🏆 **Hackathon Pipeline v2**\n",
        f"Отобрано: {len(selected)}\n",
    ]

    for i, hack in enumerate(selected, 1):
        summary_lines.append(
            f"**{i}. {hack.title}**\n"
            f"   💰 {hack.prize} | ⏰ {hack.deadline}\n"
            f"   🔗 {hack.url}\n"
        )

    for hack in selected:
        await notify(f"\n{'='*40}\n🚀 Работаю над: {hack.title}")
        try:
            result = await _process_single_hackathon(hack, notify)
            results.append(result)
        except Exception as e:
            logger.error("Pipeline failed for %s: %s", hack.title, e)
            results.append({"hackathon": hack.title, "success": False, "error": str(e)})
            await notify(f"❌ Ошибка: {e}")

    elapsed = int((time.time() - start_time) / 60)
    success_count = sum(1 for r in results if r.get("success"))
    summary_lines.append(f"\n{'='*40}")
    summary_lines.append(f"📊 Итоги: ✅ {success_count}/{len(selected)} | ⏱ {elapsed} мин")

    for r in results:
        s = "✅" if r.get("success") else "❌"
        summary_lines.append(f"\n{s} **{r.get('hackathon', '?')}**")
        if r.get("github_url"):
            summary_lines.append(f"   GitHub: {r['github_url']}")
        if r.get("demo_url"):
            summary_lines.append(f"   Demo: {r['demo_url']}")
        if r.get("submission_url"):
            summary_lines.append(f"   Submission: {r['submission_url']}")
        if r.get("error"):
            summary_lines.append(f"   Error: {r['error']}")

    return "\n".join(summary_lines)


async def _process_single_hackathon(hack: HackathonInfo, notify) -> dict:
    """Process one hackathon: analyze → build → deploy → submit."""
    result = {"hackathon": hack.title, "url": hack.url, "success": False}

    # ── Step 3: Analyze ──
    await notify("📋 Этап 3/7: Анализ правил...")
    analysis = await _analyze_hackathon(hack)
    result["analysis"] = analysis

    if analysis.get("skip"):
        result["error"] = f"Пропущен: {analysis.get('reason', 'не подходит')}"
        return result

    # ── Step 4: Build MVP with Claude Code ──
    await notify("🔨 Этап 4/7: Claude Code генерирует MVP...")
    from services.project_generator import generate_project

    project = await generate_project(
        hackathon_title=hack.title,
        hackathon_description=analysis.get("full_text", hack.description),
        requirements=analysis.get("requirements", ""),
        technologies_required=analysis.get("required_tech", []),
        project_type=analysis.get("project_type", "web_app"),
    )

    if not project.get("success"):
        result["error"] = f"Генерация: {project.get('error', 'unknown')}"
        return result

    result["project_name"] = project["project_name"]
    await notify(f"✅ Проект: {project['display_name']} ({len(project['files'])} файлов)")

    # ── Step 5: Deploy ──
    await notify("🚀 Этап 5/7: GitHub + Pages...")
    from services.project_deployer import deploy_project

    deploy = await deploy_project(
        project_dir=project["project_dir"],
        project_name=project["project_name"],
        description=project.get("tagline", ""),
    )

    result["github_url"] = deploy.get("github_url", "")
    result["demo_url"] = deploy.get("demo_url", "")
    await notify(f"✅ GitHub: {deploy.get('github_url', 'N/A')}")

    # ── Step 6: Screenshots ──
    await notify("📸 Этап 6/7: Скриншоты...")
    from services.project_generator import generate_screenshots

    screenshots = await generate_screenshots(
        project_dir=project["project_dir"],
        demo_url=deploy.get("demo_url", ""),
    )
    result["screenshots"] = screenshots

    # ── Step 7: Submit ──
    await notify("📨 Этап 7/7: Подача на DevPost...")

    from services.devpost_automation import get_devpost
    devpost = get_devpost()

    # If non-DevPost platform, try to register on it
    is_devpost = "devpost.com" in hack.url
    if not is_devpost:
        await notify(f"📝 Регистрируюсь на {hack.url.split('/')[2]}...")
        reg = await devpost.register_on_platform(hack.url)

        if reg.get("needs_verification"):
            await notify(
                f"⚠️ Нужно подтверждение!\n"
                f"Платформа: {reg['platform']}\n"
                f"Email: azatmaster@gmail.com\n"
                f"Проверь почту и скинь код/ссылку активации.\n"
                f"Скриншот: {reg.get('screenshot', '')}"
            )
            # Continue with submission anyway — some platforms don't block
        elif reg.get("already_registered"):
            await notify(f"✅ Уже зарегистрирован на {reg['platform']}")

    await devpost.register_for_hackathon(hack.url)

    desc = project.get("devpost_description", {})
    submission = await devpost.submit_project(
        hackathon_url=hack.url,
        project_name=project.get("display_name", project["project_name"]),
        tagline=project.get("tagline", ""),
        inspiration=desc.get("inspiration", ""),
        what_it_does=desc.get("what_it_does", ""),
        how_built=desc.get("how_we_built_it", ""),
        challenges=desc.get("challenges_we_ran_into", ""),
        accomplishments=desc.get("accomplishments", ""),
        what_learned=desc.get("what_we_learned", ""),
        whats_next=desc.get("whats_next", ""),
        github_url=deploy.get("github_url", ""),
        demo_url=deploy.get("demo_url", ""),
        screenshot_paths=screenshots,
        technologies=project.get("technologies", []),
    )

    result["submission_url"] = submission.get("url", "")
    result["success"] = submission.get("success", False)

    if submission.get("success"):
        await notify(f"🎉 ПОДАНО! {hack.title}\n   {submission['url']}")
    else:
        await notify(f"⚠️ Проверь вручную: {submission.get('url', 'N/A')}")
        if submission.get("url") and "submission" in submission.get("url", ""):
            result["success"] = True

    await devpost.close()
    return result


# ─── Discovery ────────────────────────────────────────────────────────────────


async def _discover_hackathons() -> list[HackathonInfo]:
    """Discover hackathons from multiple platforms."""
    hackathons = []

    async with httpx.AsyncClient(
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; HackBot/1.0)"},
    ) as client:
        # Run all sources in parallel
        results = await asyncio.gather(
            _fetch_devpost(client),
            _fetch_hackerearth(client),
            _fetch_unstop(client),
            _fetch_devfolio(client),
            _fetch_mlh(client),
            _fetch_dorahacks(client),
            _fetch_web_search(client),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error("Discovery source error: %s", result)
            elif isinstance(result, list):
                hackathons.extend(result)

    # Deduplicate by URL
    seen = set()
    unique = []
    for h in hackathons:
        key = h.url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            unique.append(h)

    logger.info("Total hackathons discovered: %d (from %d raw)", len(unique), len(hackathons))
    return unique


async def _fetch_devpost(client: httpx.AsyncClient) -> list[HackathonInfo]:
    """DevPost — primary source."""
    results = []
    for page in range(1, 6):
        try:
            resp = await client.get(
                "https://devpost.com/api/hackathons",
                params={"status": "open", "order_by": "deadline", "page": page},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("hackathons"):
                break
            for h in data["hackathons"]:
                results.append(HackathonInfo(
                    title=h.get("title", ""),
                    url=h.get("url", ""),
                    prize=re.sub(r"<[^>]+>", "", str(h.get("prize_amount", h.get("prize", "")))),
                    deadline=h.get("submission_period_dates", h.get("time_left_to_submit", "")),
                    description=h.get("tagline", ""),
                    participants=h.get("registrations_count", 0),
                ))
        except Exception as e:
            logger.error("DevPost page %d: %s", page, e)
            break
    logger.info("DevPost: %d hackathons", len(results))
    return results


async def _fetch_hackerearth(client: httpx.AsyncClient) -> list[HackathonInfo]:
    """HackerEarth — scrape challenge listings."""
    results = []
    try:
        resp = await client.get(
            "https://www.hackerearth.com/chrome-extension/events/",
            params={"type": "hackathon", "status": "upcoming"},
        )
        resp.raise_for_status()
        data = resp.json()

        for event in data.get("response", []):
            title = event.get("title", "")
            url = event.get("url", "")
            if not url.startswith("http"):
                url = "https://www.hackerearth.com" + url

            results.append(HackathonInfo(
                title=f"[HackerEarth] {title}",
                url=url,
                prize=event.get("prize", ""),
                deadline=event.get("end_date", ""),
                description=event.get("description", "")[:200],
                participants=event.get("registrations", 0),
            ))
    except Exception as e:
        logger.warning("HackerEarth: %s", e)

    # Also try ongoing
    try:
        resp2 = await client.get(
            "https://www.hackerearth.com/chrome-extension/events/",
            params={"type": "hackathon", "status": "ongoing"},
        )
        resp2.raise_for_status()
        data2 = resp2.json()
        for event in data2.get("response", []):
            title = event.get("title", "")
            url = event.get("url", "")
            if not url.startswith("http"):
                url = "https://www.hackerearth.com" + url
            results.append(HackathonInfo(
                title=f"[HackerEarth] {title}",
                url=url,
                prize=event.get("prize", ""),
                deadline=event.get("end_date", ""),
                description=event.get("description", "")[:200],
                participants=event.get("registrations", 0),
            ))
    except Exception as e:
        logger.warning("HackerEarth ongoing: %s", e)

    logger.info("HackerEarth: %d hackathons", len(results))
    return results


async def _fetch_unstop(client: httpx.AsyncClient) -> list[HackathonInfo]:
    """Unstop — scrape listings page."""
    results = []
    try:
        resp = await client.get(
            "https://unstop.com/hackathons",
            headers={"Accept": "text/html"},
        )
        if resp.status_code == 200:
            # Extract hackathon links and titles
            links = re.findall(
                r'href="(/hackathons/[^"]+)"[^>]*>.*?<[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)',
                resp.text, re.DOTALL,
            )
            if not links:
                # Simpler pattern
                links = re.findall(r'href="(/hackathons/[^"]+)"', resp.text)
                for link in set(links[:20]):
                    slug = link.split("/")[-1]
                    name = slug.replace("-", " ").title()
                    results.append(HackathonInfo(
                        title=f"[Unstop] {name}",
                        url=f"https://unstop.com{link}",
                        prize="", deadline="", description="",
                    ))
            else:
                for link, title in links[:20]:
                    results.append(HackathonInfo(
                        title=f"[Unstop] {title.strip()}",
                        url=f"https://unstop.com{link}",
                        prize="", deadline="", description="",
                    ))
    except Exception as e:
        logger.warning("Unstop: %s", e)

    logger.info("Unstop: %d hackathons", len(results))
    return results


async def _fetch_devfolio(client: httpx.AsyncClient) -> list[HackathonInfo]:
    """Devfolio — scrape hackathon listings."""
    results = []
    try:
        # Devfolio GraphQL-like API
        resp = await client.get(
            "https://api.devfolio.co/api/hackathons",
            params={"type": "upcoming", "limit": 30},
        )
        if resp.status_code == 200:
            data = resp.json()
            for h in data.get("hackathons", data.get("data", [])):
                title = h.get("name", h.get("title", ""))
                slug = h.get("slug", "")
                url = f"https://devfolio.co/hackathons/{slug}" if slug else ""
                results.append(HackathonInfo(
                    title=f"[Devfolio] {title}",
                    url=url or h.get("url", ""),
                    prize=h.get("prize_pool", h.get("prize", "")),
                    deadline=h.get("ends_at", h.get("deadline", "")),
                    description=h.get("tagline", h.get("description", ""))[:200],
                    participants=h.get("participants_count", 0),
                ))
    except Exception as e:
        logger.warning("Devfolio: %s", e)

    # Fallback: scrape listing page
    if not results:
        try:
            resp = await client.get("https://devfolio.co/hackathons")
            if resp.status_code == 200:
                text = resp.text
                # Extract hackathon links
                links = re.findall(r'href="(/hackathons/[^"]+)"', text)
                for link in set(links[:20]):
                    slug = link.split("/")[-1]
                    results.append(HackathonInfo(
                        title=f"[Devfolio] {slug.replace('-', ' ').title()}",
                        url=f"https://devfolio.co{link}",
                        prize="", deadline="", description="",
                    ))
        except Exception as e:
            logger.warning("Devfolio fallback: %s", e)

    logger.info("Devfolio: %d hackathons", len(results))
    return results


async def _fetch_mlh(client: httpx.AsyncClient) -> list[HackathonInfo]:
    """MLH (Major League Hacking) — scrape events page."""
    results = []
    try:
        resp = await client.get("https://mlh.io/seasons/2026/events")
        if resp.status_code == 200:
            text = resp.text
            # Parse event cards
            events = re.findall(
                r'class="event-link"[^>]*href="([^"]+)".*?'
                r'class="event-name"[^>]*>([^<]+)',
                text, re.DOTALL,
            )
            for url, title in events:
                results.append(HackathonInfo(
                    title=f"[MLH] {title.strip()}",
                    url=url if url.startswith("http") else f"https://mlh.io{url}",
                    prize="", deadline="", description="MLH Hackathon",
                ))
    except Exception as e:
        logger.warning("MLH: %s", e)

    # Try JSON API
    if not results:
        try:
            resp = await client.get(
                "https://mlh.io/events",
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
                data = resp.json()
                for e in data if isinstance(data, list) else data.get("events", []):
                    results.append(HackathonInfo(
                        title=f"[MLH] {e.get('name', '')}",
                        url=e.get("url", e.get("link", "")),
                        prize="", deadline=e.get("end_date", ""),
                        description=e.get("description", "")[:200],
                    ))
        except Exception as e:
            logger.warning("MLH JSON: %s", e)

    logger.info("MLH: %d hackathons", len(results))
    return results


async def _fetch_dorahacks(client: httpx.AsyncClient) -> list[HackathonInfo]:
    """DoraHacks — web3 hackathons with real prizes."""
    results = []
    try:
        resp = await client.get(
            "https://dorahacks.io/api/hackathon/list",
            params={"status": "active", "page": 1, "limit": 30},
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data if isinstance(data, list) else data.get("data", data.get("hackathons", []))
            for h in items:
                title = h.get("name", h.get("title", ""))
                hid = h.get("id", "")
                slug = h.get("slug", hid)
                url = f"https://dorahacks.io/hackathon/{slug}" if slug else ""
                results.append(HackathonInfo(
                    title=f"[DoraHacks] {title}",
                    url=url or h.get("url", ""),
                    prize=h.get("total_prize", h.get("prize_pool", "")),
                    deadline=h.get("end_time", h.get("deadline", "")),
                    description=h.get("description", "")[:200],
                    participants=h.get("participants", 0),
                ))
    except Exception as e:
        logger.warning("DoraHacks: %s", e)

    # Fallback: scrape page
    if not results:
        try:
            resp = await client.get("https://dorahacks.io/hackathon")
            if resp.status_code == 200:
                links = re.findall(r'href="(/hackathon/[^"]+)"', resp.text)
                for link in set(links[:15]):
                    slug = link.split("/")[-1]
                    results.append(HackathonInfo(
                        title=f"[DoraHacks] {slug.replace('-', ' ').title()}",
                        url=f"https://dorahacks.io{link}",
                        prize="", deadline="", description="Web3 hackathon",
                    ))
        except Exception as e:
            logger.warning("DoraHacks fallback: %s", e)

    logger.info("DoraHacks: %d hackathons", len(results))
    return results


async def _fetch_web_search(client: httpx.AsyncClient) -> list[HackathonInfo]:
    """DuckDuckGo search for hackathons not on major platforms."""
    results = []
    queries = [
        "online hackathon 2026 cash prize open registration",
        "AI hackathon 2026 prize money submit",
        "web3 hackathon 2026 bounty prize open",
    ]

    for query in queries:
        try:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
            )
            if resp.status_code != 200:
                continue

            # Parse results
            links = re.findall(
                r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                resp.text, re.DOTALL,
            )
            for raw_url, raw_title in links[:10]:
                title = re.sub(r"<[^>]+>", "", raw_title).strip()
                url = raw_url
                if "uddg=" in url:
                    m = re.search(r"uddg=([^&]+)", url)
                    if m:
                        from urllib.parse import unquote
                        url = unquote(m.group(1))

                # Skip known aggregators (already scraped), news, etc.
                skip_domains = ["devpost.com", "hackerearth.com", "unstop.com",
                                "devfolio.co", "mlh.io", "dorahacks.io",
                                "youtube.com", "reddit.com", "medium.com",
                                "wikipedia.org", "twitter.com"]
                if any(d in url.lower() for d in skip_domains):
                    continue

                results.append(HackathonInfo(
                    title=f"[Web] {title[:80]}",
                    url=url,
                    prize="", deadline="", description="Found via search",
                ))
        except Exception as e:
            logger.warning("DuckDuckGo search: %s", e)

    logger.info("Web search: %d hackathons", len(results))
    return results


async def _select_hackathons(hackathons, max_count, min_prize, min_hours):
    candidates = []
    for h in hackathons:
        if h.hours_left < min_hours:
            continue
        prize_val = _parse_prize(h.prize)
        if prize_val < min_prize:
            continue
        candidates.append((h, prize_val))

    if not candidates:
        return []

    # Sort: best ratio of prize per participant
    candidates.sort(
        key=lambda x: x[1] / max(x[0].participants, 1),
        reverse=True,
    )

    hack_list = []
    for h, pv in candidates[:30]:
        hack_list.append({
            "title": h.title, "url": h.url,
            "prize_usd": pv, "hours_left": h.hours_left,
            "participants": h.participants, "description": h.description,
        })

    prompt = f"""You are a hackathon strategist. GOAL: win cash prizes. Submit to ALL viable hackathons.

PARTICIPANT PROFILE:
- 32-year-old software engineer & AI startup founder
- Based in Netherlands (EU) — our IP is Dutch
- NOT a student
- Can claim any country for registration — Netherlands, USA, Germany, etc.
- Speaks English and Russian

HACKATHONS WITH CASH PRIZES:
{json.dumps(hack_list, indent=2, ensure_ascii=False)}

RULES:
- Select ALL hackathons we can participate in
- SKIP only if: student-only OR requires physical presence we can't attend
- DO NOT skip based on country restrictions — we register as Netherlands/EU resident
- DO NOT skip based on prize size — even $50 is worth submitting
- DO NOT skip based on number of participants
- We build with AI (Claude Code) — web apps, APIs, AI tools, dashboards, Chrome extensions, data viz
- We're a professional, not a student — skip student-only competitions

Return ALL viable hackathons as JSON array (no markdown):
[{{"url": "...", "reason": "brief note", "project_type": "web_app|api|ai_tool", "confidence": 0.0-1.0}}]"""

    resp = _run_claude(prompt, timeout=120)
    selections = _extract_json(resp)

    if not selections or not isinstance(selections, list):
        candidates.sort(key=lambda x: x[1] / max(x[0].hours_left, 1), reverse=True)
        return [c[0] for c in candidates[:max_count]]

    selected = []
    for sel in selections[:max_count]:
        url = sel.get("url", "")
        for h, _ in candidates:
            if h.url == url:
                h._project_type = sel.get("project_type", "web_app")
                h._confidence = sel.get("confidence", 0.5)
                h._reason = sel.get("reason", "")
                selected.append(h)
                break

    return selected


# ─── Analysis ─────────────────────────────────────────────────────────────────


async def _analyze_hackathon(hack: HackathonInfo) -> dict:
    from services.devpost_automation import get_devpost
    devpost = get_devpost()
    details = await devpost.get_hackathon_details(hack.url)

    prompt = f"""Analyze this hackathon for autonomous AI participation.

PARTICIPANT: 32yo software engineer, AI startup founder, based in Netherlands (EU). NOT a student.

HACKATHON: {hack.title}
URL: {hack.url}
PRIZE: {hack.prize}
DEADLINE: {hack.deadline}
HOURS LEFT: {hack.hours_left:.0f}

PAGE CONTENT:
{details.get('full_text', '')[:5000]}

{f"RULES: {details.get('rules_text', '')[:2000]}" if details.get('rules_text') else ''}

IMPORTANT: Do NOT set skip=true for country restrictions — we register as Netherlands/EU.
Only skip if it's physically impossible (requires in-person attendance we can't do, or student-only).

Respond ONLY in JSON:
{{
    "requirements": "What needs to be built",
    "required_tech": ["required", "technologies"],
    "judging_criteria": ["criterion1"],
    "project_type": "web_app|api|ai_tool",
    "skip": false,
    "reason": "",
    "strategy": "How to win"
}}"""

    resp = _run_claude(prompt, timeout=120)
    analysis = _extract_json(resp)

    if not analysis:
        return {
            "requirements": hack.description,
            "required_tech": [],
            "project_type": hack._project_type,
            "full_text": details.get("full_text", ""),
        }

    analysis["full_text"] = details.get("full_text", "")
    return analysis


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _parse_prize(prize_str) -> int:
    if not prize_str:
        return 0
    # Strip HTML tags first
    prize_str = re.sub(r"<[^>]+>", "", str(prize_str))
    clean = re.sub(r"[^\d,.]", "", prize_str.replace(",", ""))
    try:
        return int(float(clean))
    except (ValueError, TypeError):
        return 0


async def get_pipeline_status() -> str:
    projects_dir = Path("/opt/aizavod/hackathon_projects")
    if not projects_dir.exists():
        return "Нет проектов."
    lines = ["**Hackathon Projects:**\n"]
    for pdir in sorted(projects_dir.iterdir()):
        if pdir.is_dir():
            files = [f for f in pdir.rglob("*") if f.is_file()]
            has_git = (pdir / ".git").exists()
            s = "✅" if has_git else "🔨"
            lines.append(f"{s} **{pdir.name}** ({len(files)} files)")
    return "\n".join(lines) if len(lines) > 1 else "Нет проектов."
