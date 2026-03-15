"""Instagram client wrapper using instagrapi for posting, stories, and reels."""
from __future__ import annotations

import json
import logging
import random
import asyncio
from pathlib import Path
from typing import Optional

from instagrapi import Client
from instagrapi.types import StoryMention, StoryHashtag, StoryLink, StorySticker

from backend.config import get_instagram_config

logger = logging.getLogger("aizavod.instagram_client")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"


class InstagramClient:
    """Thread-safe Instagram client with session persistence and human-like delays."""

    def __init__(self):
        self._client = Client()
        self._logged_in = False

    def login(self, session_data: Optional[str] = None) -> None:
        """Login to Instagram with session persistence."""
        cfg = get_instagram_config()
        if not cfg.username or not cfg.password:
            raise RuntimeError("Instagram credentials not configured")

        if cfg.proxy:
            self._client.set_proxy(cfg.proxy)

        # Try session restore first
        if session_data:
            try:
                self._client.set_settings(json.loads(session_data))
                self._client.login(cfg.username, cfg.password)
                self._logged_in = True
                logger.info("Instagram login restored from session")
                return
            except Exception as e:
                logger.warning("Session restore failed, doing fresh login: %s", e)

        self._client.login(cfg.username, cfg.password)
        self._logged_in = True
        logger.info("Instagram login successful for @%s", cfg.username)

    def get_session_data(self) -> str:
        """Export current session for persistence."""
        return json.dumps(self._client.get_settings())

    def _ensure_login(self) -> None:
        if not self._logged_in:
            self.login()

    async def _human_delay(self, min_sec: float = 3.0, max_sec: float = 12.0) -> None:
        """Random delay to mimic human behavior.

        Default 3-12 sec. IG tracks action speed — too fast = bot detection.
        """
        delay = random.uniform(min_sec, max_sec)
        # Add occasional longer pause (10% chance of 2-3x delay)
        if random.random() < 0.1:
            delay *= random.uniform(2.0, 3.0)
        await asyncio.sleep(delay)

    def _resolve_path(self, path: str) -> Path:
        if path.startswith("/media/"):
            return _MEDIA_DIR.parent / path.lstrip("/")
        return Path(path)

    async def publish_photo(self, image_path: str, caption: str) -> str:
        """Publish a photo to the feed. Returns media ID."""
        self._ensure_login()
        await self._human_delay()

        abs_path = self._resolve_path(image_path)
        media = self._client.photo_upload(abs_path, caption)
        media_id = media.id

        logger.info("Published photo: media_id=%s", media_id)
        return media_id

    async def publish_carousel(self, image_paths: list[str], caption: str) -> str:
        """Publish a carousel (album) post. Returns media ID."""
        self._ensure_login()
        await self._human_delay()

        abs_paths = [self._resolve_path(p) for p in image_paths]
        media = self._client.album_upload(abs_paths, caption)
        media_id = media.id

        logger.info("Published carousel (%d images): media_id=%s", len(abs_paths), media_id)
        return media_id

    async def publish_reel(
        self,
        video_path: str,
        caption: str,
        thumbnail_path: Optional[str] = None,
        audio_id: Optional[str] = None,
    ) -> str:
        """Publish a reel (short video). Returns media ID.

        Args:
            video_path: Path to video file.
            caption: Caption text.
            thumbnail_path: Optional thumbnail image.
            audio_id: Optional IG trending audio ID to attach to the reel.
        """
        self._ensure_login()
        await self._human_delay(3.0, 10.0)

        abs_video = self._resolve_path(video_path)
        abs_thumb = self._resolve_path(thumbnail_path) if thumbnail_path else None

        extra_data = {}
        if audio_id:
            extra_data["audio_id"] = audio_id

        media = self._client.clip_upload(
            abs_video, caption, thumbnail=abs_thumb,
            extra_data=extra_data if extra_data else None,
        )
        media_id = media.id

        logger.info("Published reel: media_id=%s, audio_id=%s", media_id, audio_id)
        return media_id

    async def publish_story_photo(
        self,
        image_path: str,
        caption: Optional[str] = None,
        mentions: Optional[list[str]] = None,
        hashtags: Optional[list[str]] = None,
        link: Optional[str] = None,
    ) -> str:
        """Publish a photo story with optional interactive elements."""
        self._ensure_login()
        await self._human_delay()

        abs_path = self._resolve_path(image_path)

        story_mentions = []
        if mentions:
            for m in mentions:
                user = self._client.user_info_by_username(m.lstrip("@"))
                story_mentions.append(StoryMention(user=user, x=0.5, y=0.5, width=0.5, height=0.1))

        story_hashtags = []
        if hashtags:
            for h in hashtags[:3]:
                story_hashtags.append(StoryHashtag(hashtag=self._client.hashtag_info(h.lstrip("#")),
                                                    x=0.5, y=0.8, width=0.5, height=0.1))

        story_links = []
        if link:
            story_links.append(StoryLink(webUri=link))

        media = self._client.photo_upload_to_story(
            abs_path,
            caption=caption or "",
            mentions=story_mentions or [],
            hashtags=story_hashtags or [],
            links=story_links or [],
        )

        logger.info("Published story photo: %s", media.id)
        return media.id

    async def publish_story_video(self, video_path: str, caption: Optional[str] = None) -> str:
        """Publish a video story."""
        self._ensure_login()
        await self._human_delay()

        abs_path = self._resolve_path(video_path)
        media = self._client.video_upload_to_story(abs_path, caption=caption or "")
        logger.info("Published story video: %s", media.id)
        return media.id

    async def get_comments(self, media_id: str, amount: int = 50) -> list[dict]:
        """Fetch recent comments on a media."""
        self._ensure_login()
        comments = self._client.media_comments(media_id, amount=amount)
        return [
            {
                "id": str(c.pk),
                "username": c.user.username,
                "text": c.text,
                "created_at": c.created_at_utc.isoformat() if c.created_at_utc else None,
            }
            for c in comments
        ]

    async def reply_to_comment(self, media_id: str, comment_id: str, text: str) -> None:
        """Reply to a specific comment."""
        self._ensure_login()
        await self._human_delay(8.0, 25.0)
        self._client.media_comment(media_id, text, replied_to_comment_id=int(comment_id))
        logger.info("Replied to comment %s", comment_id)

    async def get_account_info(self) -> dict:
        """Get current account info (followers, following, posts count)."""
        self._ensure_login()
        info = self._client.account_info()
        return {
            "username": info.username,
            "full_name": info.full_name,
            "followers": info.follower_count,
            "following": info.following_count,
            "posts": info.media_count,
            "biography": info.biography,
        }

    async def get_media_insights(self, media_id: str) -> dict:
        """Get insights for a specific media."""
        self._ensure_login()
        try:
            insights = self._client.insights_media(media_id)
            return insights
        except Exception as e:
            logger.warning("Failed to get insights for %s: %s", media_id, e)
            return {}

    # ─── Trending Sounds ─────────────────────────────────────────────────

    async def get_trending_reels_sounds(self, count: int = 20) -> list[dict]:
        """Get trending Reels sounds by scanning top fitness reels.

        Scans top reels in fitness hashtags, extracts music_info, and ranks
        by usage frequency to find currently trending sounds.
        """
        self._ensure_login()

        hashtags = ["fitness", "gym", "workout", "fitnessmotivation", "gymlife"]
        sound_counts: dict[str, dict] = {}

        for tag in hashtags[:3]:
            try:
                medias = self._client.hashtag_medias_top(tag, amount=30)
                for m in medias:
                    if not hasattr(m, "music") or not m.music:
                        continue
                    music = m.music
                    sid = str(getattr(music, "id", ""))
                    if not sid:
                        continue
                    if sid not in sound_counts:
                        sound_counts[sid] = {
                            "sound_id": sid,
                            "title": getattr(music, "title", ""),
                            "artist": getattr(music, "artist", {}).get("name", "") if isinstance(getattr(music, "artist", None), dict) else str(getattr(music, "artist", "")),
                            "usage_count": 0,
                        }
                    sound_counts[sid]["usage_count"] += 1
            except Exception as e:
                logger.warning("Failed to scan hashtag #%s for sounds: %s", tag, e)

        # Sort by usage count
        ranked = sorted(sound_counts.values(), key=lambda x: x["usage_count"], reverse=True)
        return ranked[:count]

    # ─── DM Methods ───────────────────────────────────────────────────────

    async def get_direct_messages(self, limit: int = 20) -> list[dict]:
        """Fetch recent DM threads."""
        self._ensure_login()
        threads = self._client.direct_threads(amount=limit)
        result = []
        for thread in threads:
            messages = []
            for msg in thread.messages[:10]:
                messages.append({
                    "id": str(msg.id),
                    "text": msg.text or "",
                    "is_from_user": msg.user_id != self._client.user_id,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                })
            result.append({
                "thread_id": str(thread.id),
                "user_id": str(thread.users[0].pk) if thread.users else "",
                "username": thread.users[0].username if thread.users else "",
                "messages": messages,
            })
        return result

    async def get_user_info(self, username: str) -> dict:
        """Get public info for a username."""
        self._ensure_login()
        user = self._client.user_info_by_username(username)
        return {
            "user_id": str(user.pk),
            "username": user.username,
            "full_name": user.full_name,
            "followers": user.follower_count,
            "following": user.following_count,
            "media_count": user.media_count,
            "biography": user.biography,
            "is_verified": user.is_verified,
        }

    # ─── Engagement Methods ───────────────────────────────────────────────

    async def like_post(self, media_id: str) -> bool:
        """Like a post by media ID."""
        self._ensure_login()
        await self._human_delay(5.0, 15.0)
        return self._client.media_like(media_id)

    async def comment_on_post(self, media_id: str, text: str) -> str:
        """Comment on a post. Returns comment ID."""
        self._ensure_login()
        await self._human_delay(10.0, 30.0)
        comment = self._client.media_comment(media_id, text)
        return str(comment.pk)

    async def pin_comment(self, media_id: str, comment_id: str) -> bool:
        """Pin a comment on own post."""
        self._ensure_login()
        try:
            self._client.comment_pin(media_id, int(comment_id))
            return True
        except Exception as e:
            logger.warning("Failed to pin comment %s: %s", comment_id, e)
            return False

    async def get_hashtag_medias(self, hashtag: str, amount: int = 20) -> list[dict]:
        """Get recent medias for a hashtag (for niche engagement)."""
        self._ensure_login()
        medias = self._client.hashtag_medias_recent(hashtag, amount=amount)
        return [
            {
                "media_id": str(m.id),
                "username": m.user.username if m.user else "",
                "caption": (m.caption_text or "")[:200],
                "like_count": m.like_count,
            }
            for m in medias
        ]


# Singleton instance
_instance: Optional[InstagramClient] = None


def get_instagram_client() -> InstagramClient:
    global _instance
    if _instance is None:
        _instance = InstagramClient()
    return _instance
