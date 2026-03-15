"""Instagram publisher — adapter wrapping the existing InstagramClient."""
from __future__ import annotations

import logging
from typing import Optional

from backend.models import Platform
from services.instagram_client import get_instagram_client
from services.publisher import PlatformPublisher

logger = logging.getLogger("aizavod.instagram_publisher")


class InstagramPublisher(PlatformPublisher):
    """Adapter: PlatformPublisher → InstagramClient."""

    platform = Platform.INSTAGRAM

    async def publish_photo(self, image_path: str, caption: str) -> str:
        client = get_instagram_client()
        return await client.publish_photo(image_path, caption)

    async def publish_video(
        self, video_path: str, caption: str, thumbnail_path: Optional[str] = None
    ) -> str:
        client = get_instagram_client()
        return await client.publish_reel(video_path, caption, thumbnail_path)

    async def publish_story(self, media_path: str, caption: Optional[str] = None) -> str:
        client = get_instagram_client()
        if media_path.endswith((".mp4", ".mov", ".avi")):
            return await client.publish_story_video(media_path, caption)
        return await client.publish_story_photo(media_path, caption)

    async def get_post_analytics(self, post_id: str) -> dict:
        client = get_instagram_client()
        return await client.get_media_insights(post_id)

    async def get_comments(self, post_id: str, limit: int = 50) -> list[dict]:
        client = get_instagram_client()
        return await client.get_comments(post_id, amount=limit)

    async def reply_to_comment(self, post_id: str, comment_id: str, text: str) -> None:
        client = get_instagram_client()
        await client.reply_to_comment(post_id, comment_id, text)

    async def get_account_info(self) -> dict:
        client = get_instagram_client()
        return await client.get_account_info()
