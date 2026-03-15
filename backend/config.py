from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class AdminPanelConfig:
    username: str
    password: str
    jwt_secret: str
    jwt_expire_minutes: int = 60 * 24


@dataclass
class ReplicateConfig:
    api_token: str
    flux_model: str
    kling_model: str
    character_lora_url: str


@dataclass
class FalAIConfig:
    api_key: str
    flux_model: str
    kling_model: str


@dataclass
class FishAudioConfig:
    api_key: str
    default_voice_id: str
    model: str


@dataclass
class SunoConfig:
    api_key: str
    is_free_tier: bool


@dataclass
class AgentConfig:
    orchestrator_model: str
    max_daily_decisions: int
    dm_summary_interval: int
    competitor_analysis_interval: int


@dataclass
class AnthropicConfig:
    api_key: str
    model: str


@dataclass
class InstagramConfig:
    username: str
    password: str
    proxy: str


@dataclass
class TelegramConfig:
    bot_token: str
    admin_ids: list[str] = field(default_factory=list)


@dataclass
class ContentConfig:
    posts_per_day: int
    stories_per_day: int
    reels_per_week: int
    caption_language: str
    auto_generate: bool
    auto_approve: bool
    auto_publish: bool
    auto_reply_comments: bool


def get_admin_panel_config() -> AdminPanelConfig:
    return AdminPanelConfig(
        username=os.getenv("ADMIN_PANEL_USER", "admin"),
        password=os.getenv("ADMIN_PANEL_PASSWORD", ""),
        jwt_secret=os.getenv("ADMIN_JWT_SECRET", "change-me-in-production"),
        jwt_expire_minutes=int(os.getenv("ADMIN_JWT_EXPIRE_MINUTES", "1440")),
    )


def get_replicate_config() -> ReplicateConfig:
    return ReplicateConfig(
        api_token=os.getenv("REPLICATE_API_TOKEN", ""),
        flux_model=os.getenv("FLUX_MODEL", "black-forest-labs/flux-2-pro"),
        kling_model=os.getenv("KLING_MODEL", "kling-ai/kling-v3"),
        character_lora_url=os.getenv("CHARACTER_LORA_URL", ""),
    )


def get_fal_ai_config() -> FalAIConfig:
    return FalAIConfig(
        api_key=os.getenv("FAL_API_KEY", ""),
        flux_model=os.getenv("FAL_FLUX_MODEL", "fal-ai/flux-pro/kontext"),
        kling_model=os.getenv(
            "FAL_KLING_MODEL",
            "fal-ai/kling-video/v2.6/standard/image-to-video",
        ),
    )


def get_fish_audio_config() -> FishAudioConfig:
    return FishAudioConfig(
        api_key=os.getenv("FISH_AUDIO_API_KEY", ""),
        default_voice_id=os.getenv("FISH_AUDIO_VOICE_ID", ""),
        model=os.getenv("FISH_AUDIO_MODEL", "speech-1.5"),
    )


def get_suno_config() -> SunoConfig:
    return SunoConfig(
        api_key=os.getenv("SUNO_API_KEY", ""),
        is_free_tier=os.getenv("SUNO_FREE_TIER", "true").lower() == "true",
    )


def get_agent_config() -> AgentConfig:
    return AgentConfig(
        orchestrator_model=os.getenv("AGENT_MODEL", "claude-opus-4-6"),
        max_daily_decisions=int(os.getenv("AGENT_MAX_DAILY_DECISIONS", "100")),
        dm_summary_interval=int(os.getenv("AGENT_DM_SUMMARY_INTERVAL", "60")),
        competitor_analysis_interval=int(
            os.getenv("AGENT_COMPETITOR_INTERVAL", "24")
        ),
    )


def get_anthropic_config() -> AnthropicConfig:
    return AnthropicConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("CLAUDE_MODEL", "claude-opus-4-6"),
    )


def get_instagram_config() -> InstagramConfig:
    return InstagramConfig(
        username=os.getenv("INSTAGRAM_USERNAME", ""),
        password=os.getenv("INSTAGRAM_PASSWORD", ""),
        proxy=os.getenv("INSTAGRAM_PROXY", ""),
    )


def get_telegram_config() -> TelegramConfig:
    admin_ids_raw = os.getenv("ADMIN_TELEGRAM_IDS", "")
    return TelegramConfig(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        admin_ids=[x.strip() for x in admin_ids_raw.split(",") if x.strip()],
    )


def get_content_config() -> ContentConfig:
    return ContentConfig(
        posts_per_day=int(os.getenv("POSTS_PER_DAY", "2")),
        stories_per_day=int(os.getenv("STORIES_PER_DAY", "5")),
        reels_per_week=int(os.getenv("REELS_PER_WEEK", "3")),
        caption_language=os.getenv("CAPTION_LANGUAGE", "both"),
        auto_generate=os.getenv("AUTO_GENERATE", "false").lower() == "true",
        auto_approve=os.getenv("AUTO_APPROVE", "false").lower() == "true",
        auto_publish=os.getenv("AUTO_PUBLISH", "false").lower() == "true",
        auto_reply_comments=os.getenv("AUTO_REPLY_COMMENTS", "false").lower() == "true",
    )


@dataclass
class TikTokConfig:
    client_key: str
    client_secret: str
    access_token: str
    open_id: str


@dataclass
class VKConfig:
    access_token: str
    group_id: str
    api_version: str = "5.199"


@dataclass
class TelegramChannelConfig:
    channel_username: str
    channel_id: str


@dataclass
class RedisConfig:
    url: str


@dataclass
class CeleryConfig:
    broker_url: str
    result_backend: str
    use_celery: bool


def get_tiktok_config() -> TikTokConfig:
    return TikTokConfig(
        client_key=os.getenv("TIKTOK_CLIENT_KEY", ""),
        client_secret=os.getenv("TIKTOK_CLIENT_SECRET", ""),
        access_token=os.getenv("TIKTOK_ACCESS_TOKEN", ""),
        open_id=os.getenv("TIKTOK_OPEN_ID", ""),
    )


def get_vk_config() -> VKConfig:
    return VKConfig(
        access_token=os.getenv("VK_ACCESS_TOKEN", ""),
        group_id=os.getenv("VK_GROUP_ID", ""),
        api_version=os.getenv("VK_API_VERSION", "5.199"),
    )


def get_telegram_channel_config() -> TelegramChannelConfig:
    return TelegramChannelConfig(
        channel_username=os.getenv("TELEGRAM_CHANNEL_USERNAME", ""),
        channel_id=os.getenv("TELEGRAM_CHANNEL_ID", ""),
    )


def get_redis_config() -> RedisConfig:
    return RedisConfig(
        url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    )


def get_celery_config() -> CeleryConfig:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return CeleryConfig(
        broker_url=redis_url,
        result_backend=redis_url,
        use_celery=os.getenv("USE_CELERY", "false").lower() == "true",
    )


@dataclass
class CertifierConfig:
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_model: str = field(default_factory=lambda: os.getenv("CERTIFIER_MODEL", "llama-3.3-70b-versatile"))
    knowledge_dir: str = field(default_factory=lambda: os.getenv("CERTIFIER_KNOWLEDGE_DIR", "data/certifier"))


def get_certifier_config() -> CertifierConfig:
    return CertifierConfig()


def get_backend_api_key() -> str:
    return os.getenv("BACKEND_API_KEY", "")


def get_log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").upper()
