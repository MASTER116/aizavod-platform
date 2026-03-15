"""Abstract publisher interface and registry for multi-platform publishing."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from backend.models import Platform

logger = logging.getLogger("aizavod.publisher")


class PlatformPublisher(ABC):
    """Base class for all platform publishers."""

    platform: Platform

    @abstractmethod
    async def publish_photo(self, image_path: str, caption: str) -> str:
        """Publish a photo. Returns platform-specific post ID."""

    @abstractmethod
    async def publish_video(
        self, video_path: str, caption: str, thumbnail_path: Optional[str] = None
    ) -> str:
        """Publish a video/reel. Returns platform-specific post ID."""

    @abstractmethod
    async def publish_story(self, media_path: str, caption: Optional[str] = None) -> str:
        """Publish a story. Returns platform-specific story ID."""

    @abstractmethod
    async def get_post_analytics(self, post_id: str) -> dict:
        """Fetch analytics for a specific post."""

    @abstractmethod
    async def get_comments(self, post_id: str, limit: int = 50) -> list[dict]:
        """Fetch comments on a post."""

    @abstractmethod
    async def reply_to_comment(self, post_id: str, comment_id: str, text: str) -> None:
        """Reply to a specific comment."""

    @abstractmethod
    async def get_account_info(self) -> dict:
        """Get account info (followers, posts count, etc.)."""


class PublisherRegistry:
    """Registry holding all platform publishers."""

    def __init__(self):
        self._publishers: dict[Platform, PlatformPublisher] = {}

    def register(self, publisher: PlatformPublisher) -> None:
        self._publishers[publisher.platform] = publisher
        logger.info("Registered publisher for %s", publisher.platform.value)

    def get(self, platform: Platform) -> PlatformPublisher:
        publisher = self._publishers.get(platform)
        if publisher is None:
            raise ValueError(f"No publisher registered for platform: {platform.value}")
        return publisher

    def has(self, platform: Platform) -> bool:
        return platform in self._publishers

    def platforms(self) -> list[Platform]:
        return list(self._publishers.keys())

    async def publish_to_all(
        self,
        platforms: list[Platform],
        image_path: str,
        caption: str,
    ) -> dict[Platform, str]:
        """Publish the same content to multiple platforms. Returns {platform: post_id}."""
        results: dict[Platform, str] = {}
        for platform in platforms:
            if not self.has(platform):
                logger.warning("Skipping %s — no publisher registered", platform.value)
                continue
            try:
                post_id = await self.get(platform).publish_photo(image_path, caption)
                results[platform] = post_id
            except Exception as e:
                logger.error("Failed to publish to %s: %s", platform.value, e)
        return results


# Global registry singleton
_registry: Optional[PublisherRegistry] = None


def get_publisher_registry() -> PublisherRegistry:
    global _registry
    if _registry is None:
        _registry = PublisherRegistry()
    return _registry
