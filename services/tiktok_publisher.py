"""TikTok publisher — implements PlatformPublisher for TikTok."""
from __future__ import annotations

import logging
from typing import Optional

from backend.models import Platform
from services.publisher import PlatformPublisher
from services.tiktok_client import get_tiktok_posting_client

logger = logging.getLogger("aizavod.tiktok_publisher")


class TikTokPublisher(PlatformPublisher):
    """Adapter: delegates to TikTokPostingClient (official Content Posting API)."""

    platform = Platform.TIKTOK

    async def publish_photo(self, image_path: str, caption: str) -> str:
        """TikTok doesn't support standalone photo posts via API v2."""
        raise NotImplementedError(
            "TikTok photo posting not supported. Use publish_video() with a short video."
        )

    async def publish_video(
        self,
        video_path: str,
        caption: str,
        thumbnail_path: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Post video to TikTok. Returns tiktok_video_id.

        Accepts optional keyword args:
            sound_id: TikTok trending sound ID to attach
        """
        client = get_tiktok_posting_client()
        sound_id = kwargs.get("sound_id")
        video_id = await client.upload_video(
            video_path, caption, sound_id=sound_id,
        )
        logger.info("Published to TikTok: video_id=%s", video_id)
        return video_id

    async def publish_story(self, media_path: str, caption: Optional[str] = None) -> str:
        """TikTok Stories not supported via official API."""
        raise NotImplementedError("TikTok Stories not supported via official API")

    async def get_post_analytics(self, post_id: str) -> dict:
        """Fetch video analytics."""
        client = get_tiktok_posting_client()
        data = await client.get_post_analytics(post_id)
        return {
            "views": data.get("view_count", 0),
            "likes": data.get("like_count", 0),
            "comments": data.get("comment_count", 0),
            "shares": data.get("share_count", 0),
            "engagement_rate": 0.0,
        }

    async def get_comments(self, post_id: str, limit: int = 50) -> list[dict]:
        """Fetch video comments."""
        client = get_tiktok_posting_client()
        return await client.get_comments(post_id, limit=limit)

    async def reply_to_comment(self, post_id: str, comment_id: str, text: str) -> None:
        """Comment reply — not implemented in v3 (TikTok API comment reply is limited)."""
        logger.warning("TikTok comment reply not implemented: post=%s, comment=%s", post_id, comment_id)

    async def get_account_info(self) -> dict:
        """Fetch TikTok account info."""
        client = get_tiktok_posting_client()
        data = await client.get_account_info()
        return {
            "username": data.get("display_name", ""),
            "followers": data.get("follower_count", 0),
            "following": data.get("following_count", 0),
            "posts_count": data.get("video_count", 0),
        }
