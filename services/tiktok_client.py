"""TikTok client — posting (official API) and trend reading (unofficial).

TikTokPostingClient: official Content Posting API (open.tiktokapis.com/v2).
TikTokTrendReader: unofficial TikTokApi for reading trending data (read-only).
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import httpx

from backend.config import get_tiktok_config

logger = logging.getLogger("aizavod.tiktok_client")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"


def _resolve_path(path: str) -> Path:
    if path.startswith("/media/"):
        return _MEDIA_DIR.parent / path.lstrip("/")
    return Path(path)


# ---------------------------------------------------------------------------
# TikTok Content Posting API (official)
# ---------------------------------------------------------------------------

class TikTokPostingClient:
    """Wraps the official TikTok Content Posting API v2.

    Endpoint: https://open.tiktokapis.com/v2
    Auth: Authorization: Bearer {access_token}
    """

    BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(self):
        cfg = get_tiktok_config()
        self._access_token = cfg.access_token
        self._open_id = cfg.open_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    async def upload_video(
        self,
        video_path: str,
        caption: str,
        title: str | None = None,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_stitch: bool = False,
        disable_comment: bool = False,
        sound_id: str | None = None,
    ) -> str:
        """Upload a video to TikTok using the file upload flow.

        3-step process:
        1. POST /post/publish/video/init/ → get upload_url + publish_id
        2. PUT upload_url with raw video bytes (chunked if >64MB)
        3. Poll /post/publish/status/fetch/ until PUBLISH_COMPLETE

        Returns:
            tiktok_video_id
        """
        abs_path = _resolve_path(video_path)
        if not abs_path.exists():
            raise FileNotFoundError(f"Video not found: {abs_path}")

        file_size = abs_path.stat().st_size

        # Step 1: Initialize upload
        post_info: dict = {
            "title": title or caption[:150],
            "description": caption[:2200],
            "privacy_level": privacy_level,
            "disable_duet": disable_duet,
            "disable_stitch": disable_stitch,
            "disable_comment": disable_comment,
        }
        if sound_id:
            post_info["music_id"] = sound_id

        source_info = {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1,
        }

        init_payload = {
            "post_info": post_info,
            "source_info": source_info,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE_URL}/post/publish/video/init/",
                headers=self._headers(),
                json=init_payload,
            )
            resp.raise_for_status()
            data = resp.json()

        error = data.get("error", {})
        if error.get("code") != "ok":
            raise RuntimeError(f"TikTok init failed: {error}")

        upload_url = data["data"]["upload_url"]
        publish_id = data["data"]["publish_id"]

        logger.info("TikTok upload initialized: publish_id=%s", publish_id)

        # Step 2: Upload video bytes
        video_bytes = abs_path.read_bytes()
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.put(
                upload_url,
                content=video_bytes,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                },
            )
            resp.raise_for_status()

        logger.info("TikTok video uploaded (%d bytes)", file_size)

        # Step 3: Poll publish status
        video_id = await self._poll_publish_status(publish_id)
        return video_id

    async def _poll_publish_status(
        self,
        publish_id: str,
        max_attempts: int = 60,
        interval_sec: float = 5.0,
    ) -> str:
        """Poll until PUBLISH_COMPLETE or failure."""
        for attempt in range(max_attempts):
            await asyncio.sleep(interval_sec)

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/post/publish/status/fetch/",
                    headers=self._headers(),
                    json={"publish_id": publish_id},
                )
                resp.raise_for_status()
                data = resp.json()

            status = data.get("data", {}).get("status", "")
            if status == "PUBLISH_COMPLETE":
                video_id = data["data"].get("publicaly_available_post_id", [""])[0]
                logger.info("TikTok publish complete: video_id=%s", video_id)
                return video_id
            elif status == "FAILED":
                fail_reason = data.get("data", {}).get("fail_reason", "unknown")
                raise RuntimeError(f"TikTok publish failed: {fail_reason}")

            logger.debug("TikTok publish status: %s (attempt %d/%d)", status, attempt + 1, max_attempts)

        raise RuntimeError(f"TikTok publish timed out after {max_attempts * interval_sec}s")

    async def get_creator_info(self) -> dict:
        """GET /post/publish/creator_info/query/ — privacy_level_options, max_video_post_duration_sec."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE_URL}/post/publish/creator_info/query/",
                headers=self._headers(),
                json={},
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def get_post_analytics(self, video_id: str) -> dict:
        """Fetch video analytics (views, likes, comments, shares)."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE_URL}/video/query/",
                headers=self._headers(),
                json={
                    "filters": {"video_ids": [video_id]},
                    "fields": [
                        "id", "title", "create_time", "share_url",
                        "view_count", "like_count", "comment_count", "share_count",
                    ],
                },
            )
            resp.raise_for_status()
            videos = resp.json().get("data", {}).get("videos", [])
            return videos[0] if videos else {}

    async def get_comments(self, video_id: str, limit: int = 50) -> list[dict]:
        """Fetch video comments."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE_URL}/video/comment/list/",
                headers=self._headers(),
                json={"video_id": video_id, "max_count": min(limit, 100)},
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("comments", [])

    async def get_account_info(self) -> dict:
        """Fetch account info (followers, following, video_count)."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE_URL}/user/info/",
                headers=self._headers(),
                params={
                    "fields": "open_id,display_name,avatar_url,follower_count,following_count,video_count",
                },
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("user", {})


# ---------------------------------------------------------------------------
# TikTok Trend Reader (unofficial, read-only)
# ---------------------------------------------------------------------------

class TikTokTrendReader:
    """Read-only TikTok trend data via TikTokApi (unofficial).

    Falls back to basic httpx scraping if TikTokApi is unavailable.
    """

    def __init__(self):
        self._api = None

    async def _get_api(self):
        if self._api is not None:
            return self._api
        try:
            from TikTokApi import TikTokApi
            self._api = TikTokApi()
            await self._api.create_sessions(
                num_sessions=1,
                sleep_after=3,
                headless=True,
            )
        except ImportError:
            logger.warning("TikTokApi not installed, trend reading will use fallback")
            self._api = None
        except Exception as e:
            logger.warning("Failed to create TikTokApi session: %s", e)
            self._api = None
        return self._api

    async def get_trending_sounds(self, count: int = 20) -> list[dict]:
        """Fetch trending sounds/music on TikTok."""
        api = await self._get_api()
        if api is None:
            return self._fallback_trending_sounds()
        try:
            sounds = []
            async for sound in api.trending.sounds(count=count):
                sounds.append({
                    "sound_id": str(sound.id),
                    "title": sound.title or "",
                    "author": sound.author or "",
                    "duration_sec": getattr(sound, "duration", 0),
                    "usage_count": getattr(sound, "stats", {}).get("videoCount", 0),
                    "is_original": getattr(sound, "original", False),
                })
            return sounds
        except Exception as e:
            logger.warning("TikTokApi trending sounds failed: %s", e)
            return self._fallback_trending_sounds()

    async def get_trending_hashtags(
        self, niche: str = "fitness", count: int = 30,
    ) -> list[dict]:
        """Fetch trending hashtags related to niche."""
        api = await self._get_api()
        if api is None:
            return self._fallback_trending_hashtags(niche)
        try:
            hashtags = []
            tag = api.hashtag(name=niche)
            async for video in tag.videos(count=count):
                for ht in getattr(video, "hashtags", []):
                    ht_name = getattr(ht, "name", "")
                    existing = next((h for h in hashtags if h["hashtag"] == ht_name), None)
                    if existing:
                        existing["video_count"] += 1
                    else:
                        hashtags.append({
                            "hashtag": ht_name,
                            "view_count": getattr(ht, "view_count", 0),
                            "video_count": 1,
                            "trend_velocity": 0.0,
                        })
            hashtags.sort(key=lambda x: x["video_count"], reverse=True)
            return hashtags[:count]
        except Exception as e:
            logger.warning("TikTokApi trending hashtags failed: %s", e)
            return self._fallback_trending_hashtags(niche)

    async def get_trending_videos(
        self, hashtag: str, count: int = 20,
    ) -> list[dict]:
        """Fetch top videos under a hashtag."""
        api = await self._get_api()
        if api is None:
            return []
        try:
            videos = []
            tag = api.hashtag(name=hashtag)
            async for video in tag.videos(count=count):
                videos.append({
                    "video_id": str(video.id),
                    "author": getattr(video.author, "username", "") if video.author else "",
                    "description": video.desc or "",
                    "view_count": getattr(video.stats, "play_count", 0) if video.stats else 0,
                    "like_count": getattr(video.stats, "digg_count", 0) if video.stats else 0,
                    "share_count": getattr(video.stats, "share_count", 0) if video.stats else 0,
                    "music_id": str(video.sound.id) if video.sound else "",
                    "music_title": video.sound.title if video.sound else "",
                    "duration_sec": getattr(video, "duration", 0),
                })
            return videos
        except Exception as e:
            logger.warning("TikTokApi trending videos failed: %s", e)
            return []

    async def check_sound_copyright(self, sound_id: str) -> dict:
        """Check if a sound has copyright restrictions.

        Returns risk_level: safe / risky / blocked.
        """
        api = await self._get_api()
        if api is None:
            return {
                "sound_id": sound_id,
                "has_copyright": True,
                "commercial_available": False,
                "risk_level": "risky",
            }
        try:
            sound = api.sound(id=sound_id)
            info = await sound.info()
            author = getattr(info, "author", "") or ""
            is_original = getattr(info, "original", False)

            # Heuristic: major labels → risky, original creators → safe
            major_labels = [
                "sony", "universal", "warner", "atlantic", "columbia",
                "republic", "interscope", "def jam", "capitol",
            ]
            author_lower = author.lower()
            has_copyright = any(label in author_lower for label in major_labels)

            if has_copyright:
                risk_level = "blocked"
            elif is_original:
                risk_level = "safe"
            else:
                risk_level = "risky"

            return {
                "sound_id": sound_id,
                "has_copyright": has_copyright,
                "commercial_available": not has_copyright,
                "risk_level": risk_level,
            }
        except Exception as e:
            logger.warning("Copyright check failed for %s: %s", sound_id, e)
            return {
                "sound_id": sound_id,
                "has_copyright": True,
                "commercial_available": False,
                "risk_level": "risky",
            }

    # ── Fallbacks ──

    @staticmethod
    def _fallback_trending_sounds() -> list[dict]:
        """Static fallback when TikTokApi is unavailable."""
        return [
            {"sound_id": "", "title": "Trending Workout Beat", "author": "original",
             "duration_sec": 60, "usage_count": 0, "is_original": True},
            {"sound_id": "", "title": "Gym Motivation Mix", "author": "original",
             "duration_sec": 90, "usage_count": 0, "is_original": True},
        ]

    @staticmethod
    def _fallback_trending_hashtags(niche: str) -> list[dict]:
        """Static fallback hashtags."""
        base = {
            "fitness": ["fitnessgirl", "gymtok", "workoutmotivation", "fitcheck",
                        "gymmotivation", "fitnesstok", "healthylifestyle", "strongwoman"],
            "lifestyle": ["dayinmylife", "aestheticlifestyle", "morningroutine",
                          "nightroutine", "productivity", "selfcare"],
        }
        tags = base.get(niche, base["fitness"])
        return [
            {"hashtag": t, "view_count": 0, "video_count": 0, "trend_velocity": 0.0}
            for t in tags
        ]


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_posting_client: TikTokPostingClient | None = None
_trend_reader: TikTokTrendReader | None = None


def get_tiktok_posting_client() -> TikTokPostingClient:
    global _posting_client
    if _posting_client is None:
        _posting_client = TikTokPostingClient()
    return _posting_client


def get_tiktok_trend_reader() -> TikTokTrendReader:
    global _trend_reader
    if _trend_reader is None:
        _trend_reader = TikTokTrendReader()
    return _trend_reader
