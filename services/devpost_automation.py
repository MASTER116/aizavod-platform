"""DevPost Browser Automation — Playwright-based interaction with DevPost.

Handles:
- Login / session management
- Hackathon discovery and registration
- Project submission (fill forms, upload screenshots, submit)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aizavod.devpost_automation")

DEVPOST_EMAIL = os.getenv("DEVPOST_EMAIL", "")
DEVPOST_PASSWORD = os.getenv("DEVPOST_PASSWORD", "")
STATE_PATH = "/tmp/devpost_state.json"


class DevPostAutomation:
    """Playwright-based DevPost automation."""

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None

    async def _ensure_browser(self):
        if self._browser:
            return
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().__aenter__()
        self._browser = await self._pw.chromium.launch(headless=True)
        if Path(STATE_PATH).exists():
            try:
                self._context = await self._browser.new_context(
                    storage_state=STATE_PATH
                )
            except Exception:
                self._context = await self._browser.new_context()
        else:
            self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

    async def close(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
        if hasattr(self, "_pw") and self._pw:
            await self._pw.__aexit__(None, None, None)

    async def login(self) -> bool:
        """Login to DevPost. Returns True on success."""
        await self._ensure_browser()
        page = self._page

        # Check if already logged in
        await page.goto("https://devpost.com/software/new")
        await page.wait_for_timeout(2000)
        if "login" not in page.url:
            logger.info("Already logged in to DevPost")
            return True

        await page.goto("https://secure.devpost.com/users/login")
        await page.wait_for_timeout(3000)

        try:
            await page.click('button:has-text("Accept")', timeout=3000)
        except Exception:
            pass

        email_input = await page.query_selector("input[name*=email], #user_email")
        pw_input = await page.query_selector("input[name*=password], #user_password")

        if not email_input or not pw_input:
            logger.error("DevPost login form not found")
            return False

        await email_input.fill(DEVPOST_EMAIL)
        await pw_input.fill(DEVPOST_PASSWORD)
        await pw_input.press("Enter")
        await page.wait_for_timeout(5000)

        if "login" not in page.url:
            await self._context.storage_state(path=STATE_PATH)
            logger.info("DevPost login successful")
            return True

        logger.error("DevPost login failed, URL: %s", page.url)
        return False

    async def register_for_hackathon(self, hackathon_url: str) -> bool:
        """Register / join a hackathon on DevPost."""
        await self._ensure_browser()
        if not await self.login():
            return False

        page = self._page
        await page.goto(hackathon_url)
        await page.wait_for_timeout(3000)

        for selector in [
            'a:has-text("Join Hackathon")',
            'a:has-text("Register")',
            'a:has-text("Start a Submission")',
            'a:has-text("Enter a Submission")',
            'button:has-text("Join")',
            'a.btn:has-text("Join")',
            '#challenge-register',
        ]:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    logger.info("Clicked register button: %s", selector)

                    try:
                        confirm = await page.query_selector(
                            'button:has-text("Accept"), button:has-text("Agree"), '
                            'button:has-text("Confirm"), input[type=submit]'
                        )
                        if confirm:
                            await confirm.click()
                            await page.wait_for_timeout(2000)
                    except Exception:
                        pass

                    await self._context.storage_state(path=STATE_PATH)
                    return True
            except Exception:
                continue

        content = await page.content()
        if any(x in content.lower() for x in [
            "you're registered", "manage your submission",
            "edit submission", "your submission",
        ]):
            logger.info("Already registered for hackathon")
            return True

        logger.warning("Could not find registration button on %s", hackathon_url)
        return False

    async def submit_project(
        self,
        hackathon_url: str,
        project_name: str,
        tagline: str,
        inspiration: str,
        what_it_does: str,
        how_built: str,
        challenges: str,
        accomplishments: str,
        what_learned: str,
        whats_next: str,
        github_url: str,
        demo_url: str = "",
        video_url: str = "",
        screenshot_paths: list[str] | None = None,
        technologies: list[str] | None = None,
    ) -> dict:
        """Submit a project to a hackathon on DevPost.

        Returns dict with 'success' bool and 'url' of submission.
        """
        await self._ensure_browser()
        if not await self.login():
            return {"success": False, "error": "Login failed"}

        page = self._page

        # Navigate to hackathon submission page
        await page.goto(hackathon_url)
        await page.wait_for_timeout(3000)

        # Find submission link
        submit_link = None
        for sel in [
            'a:has-text("Start a Submission")',
            'a:has-text("Enter a Submission")',
            'a:has-text("Manage Submission")',
            'a:has-text("Edit Submission")',
            'a[href*="/submissions/new"]',
            'a[href*="/manage"]',
        ]:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    submit_link = el
                    break
            except Exception:
                continue

        if not submit_link:
            return {"success": False, "error": "No submission button found"}

        await submit_link.click()
        await page.wait_for_timeout(5000)
        logger.info("Submission page URL: %s", page.url)

        # === Fill submission form ===
        await self._fill_field(page, [
            "#submission_title", "input[name*=title]",
            "#software_header_attributes_title",
        ], project_name)

        await self._fill_field(page, [
            "#submission_tagline", "input[name*=tagline]",
            "#software_header_attributes_tagline",
        ], tagline)

        # Rich text sections — DevPost uses contenteditable divs
        sections = {
            "inspiration": inspiration,
            "what_it_does": what_it_does,
            "how_we_built_it": how_built,
            "how_i_built_it": how_built,
            "challenges_we_ran_into": challenges,
            "challenges_i_ran_into": challenges,
            "accomplishments": accomplishments,
            "what_we_learned": what_learned,
            "what_i_learned": what_learned,
            "whats_next": whats_next,
        }

        for field_key, value in sections.items():
            if not value:
                continue
            filled = False
            for sel in [
                f"textarea[name*={field_key}]",
                f"div[data-field*={field_key}] .ql-editor",
                f"#submission_{field_key}",
                f"[id*={field_key}] .ql-editor",
                f"[data-target*={field_key}] .ql-editor",
            ]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        tag = await el.evaluate("el => el.tagName")
                        if tag == "TEXTAREA":
                            await el.fill(value)
                        else:
                            await el.evaluate(
                                "(el, v) => { el.innerHTML = v; }",
                                value
                            )
                        filled = True
                        break
                except Exception:
                    continue
            if not filled:
                # Try finding by label text
                try:
                    label_text = field_key.replace("_", " ").title()
                    label = await page.query_selector(
                        f'label:has-text("{label_text}")'
                    )
                    if label:
                        for_id = await label.get_attribute("for")
                        if for_id:
                            editor = await page.query_selector(
                                f"#{for_id} .ql-editor, #{for_id}"
                            )
                            if editor:
                                await editor.evaluate(
                                    "(el, v) => { el.innerHTML = v; }",
                                    value
                                )
                except Exception:
                    pass

        # Links
        await self._fill_field(page, [
            "input[name*=repository_url]", "input[name*=github]",
            "input[placeholder*=GitHub]", "input[placeholder*=github]",
        ], github_url)

        if demo_url:
            await self._fill_field(page, [
                "input[name*=app_url]", "input[name*=website]",
                "input[name*=demo]", "input[placeholder*=URL]",
            ], demo_url)

        if video_url:
            await self._fill_field(page, [
                "input[name*=video]", "input[placeholder*=YouTube]",
                "input[placeholder*=video]", "input[placeholder*=Vimeo]",
            ], video_url)

        # Screenshots
        if screenshot_paths:
            for sel in ["input[type=file][accept*=image]", "input[type=file]"]:
                try:
                    file_input = await page.query_selector(sel)
                    if file_input:
                        existing = [p for p in screenshot_paths if Path(p).exists()]
                        if existing:
                            await file_input.set_input_files(existing[:5])
                            await page.wait_for_timeout(3000)
                        break
                except Exception:
                    continue

        # Technologies
        if technologies:
            for sel in [
                "input[name*=built_with]", "input[placeholder*=technolog]",
                ".tag-input input", "input[placeholder*=built]",
            ]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        for tech in technologies[:10]:
                            await el.fill(tech)
                            await el.press("Enter")
                            await page.wait_for_timeout(500)
                        break
                except Exception:
                    continue

        # Save draft first
        await self._click_button(page, [
            'button:has-text("Save")', "input[value*=Save]",
        ])
        await page.wait_for_timeout(3000)

        # Submit
        await self._click_button(page, [
            'button:has-text("Submit")', "input[value*=Submit]",
            'a:has-text("Submit")', "#submit-btn",
        ])
        await page.wait_for_timeout(5000)

        # Handle confirmation
        try:
            confirm = await page.query_selector(
                'button:has-text("Confirm"), button:has-text("Yes")'
            )
            if confirm:
                await confirm.click()
                await page.wait_for_timeout(3000)
        except Exception:
            pass

        final_url = page.url
        await page.screenshot(path="/tmp/devpost_submission.png")
        await self._context.storage_state(path=STATE_PATH)

        content = await page.content()
        success = any(x in content.lower() for x in [
            "submitted", "submission received", "congratulations",
            "your project has been", "manage submission",
        ])

        return {
            "success": success,
            "url": final_url,
            "screenshot": "/tmp/devpost_submission.png",
        }

    async def get_hackathon_details(self, hackathon_url: str) -> dict:
        """Scrape detailed hackathon info from its page."""
        await self._ensure_browser()
        page = self._page

        await page.goto(hackathon_url)
        await page.wait_for_timeout(3000)

        title = await page.title()
        body_text = await page.inner_text("body")

        result = {
            "title": title,
            "url": hackathon_url,
            "full_text": body_text[:8000],
        }

        try:
            prize_el = await page.query_selector(".prize-amount, [class*=prize]")
            if prize_el:
                result["prize"] = await prize_el.inner_text()
        except Exception:
            pass

        try:
            deadline_el = await page.query_selector(
                "[class*=deadline], [class*=countdown], time"
            )
            if deadline_el:
                result["deadline"] = await deadline_el.inner_text()
        except Exception:
            pass

        # Get rules page if exists
        rules_link = await page.query_selector('a[href*=rules]')
        if rules_link:
            rules_url = await rules_link.get_attribute("href")
            if rules_url and not rules_url.startswith("http"):
                rules_url = hackathon_url.rstrip("/") + "/" + rules_url.lstrip("/")
            await page.goto(rules_url)
            await page.wait_for_timeout(2000)
            result["rules_text"] = (await page.inner_text("body"))[:5000]

        return result

    async def register_on_platform(self, url: str, email: str = "azatmaster@gmail.com",
                                   name: str = "Azat Kh",
                                   password: str = "AiZavod2026!Hack") -> dict:
        """Try to register/sign up on a hackathon platform.

        Fills email, name, password in signup forms.
        Returns dict with 'needs_verification', 'platform', 'screenshot'.
        """
        await self._ensure_browser()
        page = self._page

        await page.goto(url)
        await page.wait_for_timeout(3000)

        # Find signup/register link
        for sel in [
            'a:has-text("Sign Up")', 'a:has-text("Register")',
            'a:has-text("Create Account")', 'a:has-text("Sign up")',
            'a:has-text("Join")', 'button:has-text("Sign Up")',
            'a[href*=signup]', 'a[href*=register]',
        ]:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    break
            except Exception:
                continue

        # Fill registration form
        # Email
        for sel in [
            "input[name*=email]", "input[type=email]",
            "input[placeholder*=email]", "input[placeholder*=Email]",
            "#email", "#user_email",
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.fill(email)
                    break
            except Exception:
                continue

        # Name / Username
        for sel in [
            "input[name*=name]", "input[name*=username]",
            "input[placeholder*=name]", "input[placeholder*=Name]",
            "#name", "#username", "#first_name",
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.fill(name)
                    break
            except Exception:
                continue

        # Password
        for sel in [
            "input[name*=password]", "input[type=password]",
            "#password",
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.fill(password)
                    break
            except Exception:
                continue

        # Confirm password if exists
        for sel in [
            "input[name*=confirm]", "input[name*=password_confirmation]",
            "input[placeholder*=Confirm]", "#password_confirmation",
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.fill(password)
                    break
            except Exception:
                continue

        # Accept terms checkbox
        for sel in [
            "input[name*=terms]", "input[name*=agree]", "input[name*=accept]",
            "input[type=checkbox]",
        ]:
            try:
                el = await page.query_selector(sel)
                if el and not await el.is_checked():
                    await el.check()
            except Exception:
                continue

        # Submit
        submitted = await self._click_button(page, [
            'button:has-text("Sign Up")', 'button:has-text("Register")',
            'button:has-text("Create")', 'button[type=submit]',
            'input[type=submit]',
        ])

        if submitted:
            await page.wait_for_timeout(5000)

        screenshot_path = f"/tmp/register_{url.split('/')[-1][:20]}.png"
        await page.screenshot(path=screenshot_path)

        # Check if verification needed
        content = await page.content()
        body_text = (await page.inner_text("body")).lower()
        needs_verification = any(kw in body_text for kw in [
            "verify", "confirm", "verification", "check your email",
            "activate", "подтвер", "активац", "код",
        ])

        already_registered = any(kw in body_text for kw in [
            "already", "уже зарегистр", "existing account", "log in",
        ])

        return {
            "needs_verification": needs_verification,
            "already_registered": already_registered,
            "url": page.url,
            "screenshot": screenshot_path,
            "platform": url.split("/")[2] if "/" in url else url,
        }

    async def take_screenshot(self, url: str, path: str) -> str:
        """Take a screenshot of a URL for submission materials."""
        await self._ensure_browser()
        page = self._page
        await page.goto(url)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=path, full_page=False)
        return path

    @staticmethod
    async def _fill_field(page, selectors: list[str], value: str):
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.fill(value)
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    async def _click_button(page, selectors: list[str]):
        for sel in selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    return True
            except Exception:
                continue
        return False


_instance: DevPostAutomation | None = None


def get_devpost() -> DevPostAutomation:
    global _instance
    if _instance is None:
        _instance = DevPostAutomation()
    return _instance
