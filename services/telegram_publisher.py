"""Telegram channel publisher — publishes content via Bot API."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import httpx

from backend.config import get_telegram_config, get_telegram_channel_config
from backend.models import Platform
from services.publisher import PlatformPublisher

logger = logging.getLogger("aizavod.telegram_publisher")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"
_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramPublisher(PlatformPublisher):
    """Publishes content to a Telegram channel via Bot API."""

    platform = Platform.TELEGRAM

    def _base_url(self) -> str:
        cfg = get_telegram_config()
        return _API_BASE.format(token=cfg.bot_token)

    def _chat_id(self) -> str:
        cfg = get_telegram_channel_config()
        return cfg.channel_id or cfg.channel_username

    def _resolve_path(self, path: str) -> Path:
        if path.startswith("/media/"):
            return _MEDIA_DIR.parent / path.lstrip("/")
        return Path(path)

    async def publish_photo(self, image_path: str, caption: str) -> str:
        abs_path = self._resolve_path(image_path)
        url = f"{self._base_url()}/sendPhoto"

        async with httpx.AsyncClient(timeout=60) as client:
            with open(abs_path, "rb") as f:
                resp = await client.post(
                    url,
                    data={"chat_id": self._chat_id(), "caption": caption, "parse_mode": "HTML"},
                    files={"photo": (abs_path.name, f, "image/jpeg")},
                )
            resp.raise_for_status()
            data = resp.json()

        message_id = str(data["result"]["message_id"])
        logger.info("Published photo to Telegram: message_id=%s", message_id)
        return message_id

    async def publish_video(
        self, video_path: str, caption: str, thumbnail_path: Optional[str] = None
    ) -> str:
        abs_video = self._resolve_path(video_path)
        url = f"{self._base_url()}/sendVideo"

        files: dict = {"video": (abs_video.name, open(abs_video, "rb"), "video/mp4")}
        if thumbnail_path:
            abs_thumb = self._resolve_path(thumbnail_path)
            files["thumbnail"] = (abs_thumb.name, open(abs_thumb, "rb"), "image/jpeg")

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    url,
                    data={"chat_id": self._chat_id(), "caption": caption, "parse_mode": "HTML"},
                    files=files,
                )
                resp.raise_for_status()
                data = resp.json()
        finally:
            for _, file_tuple in files.items():
                file_tuple[1].close()

        message_id = str(data["result"]["message_id"])
        logger.info("Published video to Telegram: message_id=%s", message_id)
        return message_id

    async def publish_story(self, media_path: str, caption: Optional[str] = None) -> str:
        """Telegram doesn't have native stories for channels — publish as regular post."""
        if media_path.endswith((".mp4", ".mov", ".avi")):
            return await self.publish_video(media_path, caption or "")
        return await self.publish_photo(media_path, caption or "")

    async def get_post_analytics(self, post_id: str) -> dict:
        """Telegram Bot API doesn't provide per-message analytics."""
        return {}

    async def get_comments(self, post_id: str, limit: int = 50) -> list[dict]:
        """Telegram channels don't expose comments via Bot API easily."""
        return []

    async def reply_to_comment(self, post_id: str, comment_id: str, text: str) -> None:
        """Not supported for channel messages."""
        logger.warning("reply_to_comment not supported for Telegram channels")

    async def get_account_info(self) -> dict:
        url = f"{self._base_url()}/getChat"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data={"chat_id": self._chat_id()})
            resp.raise_for_status()
            data = resp.json()

        chat = data.get("result", {})

        # Try to get member count
        count_url = f"{self._base_url()}/getChatMemberCount"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                count_resp = await client.post(count_url, data={"chat_id": self._chat_id()})
                count_resp.raise_for_status()
                member_count = count_resp.json().get("result", 0)
        except Exception:
            member_count = 0

        return {
            "title": chat.get("title", ""),
            "username": chat.get("username", ""),
            "followers": member_count,
            "type": chat.get("type", ""),
        }
