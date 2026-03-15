from __future__ import annotations

import enum
from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .database import Base


# ─── Enums ──────────────────────────────────────────────────────────────────


class ContentCategory(str, enum.Enum):
    WORKOUT = "workout"
    LIFESTYLE = "lifestyle"
    MOTIVATION = "motivation"
    OUTFIT = "outfit"
    NUTRITION = "nutrition"
    BEHIND_SCENES = "behind_scenes"
    TRANSFORMATION = "transformation"
    TUTORIAL = "tutorial"
    COLLABORATION = "collaboration"


class ContentType(str, enum.Enum):
    PHOTO = "photo"
    CAROUSEL = "carousel"
    STORY = "story"
    REEL = "reel"


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    GENERATED = "generated"
    REVIEW = "review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class CampaignStatus(str, enum.Enum):
    PROSPECT = "prospect"
    OUTREACH = "outreach"
    NEGOTIATION = "negotiation"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DMCategory(str, enum.Enum):
    FAN = "fan"
    BRAND_INQUIRY = "brand_inquiry"
    SPAM = "spam"
    QUESTION = "question"
    UNCATEGORIZED = "uncategorized"


class AdDealStatus(str, enum.Enum):
    DETECTED = "detected"
    EVALUATING = "evaluating"
    AWAITING_APPROVAL = "awaiting_approval"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    BRIEF_RECEIVED = "brief_received"
    CONTENT_CREATING = "content_creating"
    PUBLISHED = "published"
    PAYMENT_PENDING = "payment_pending"
    COMPLETED = "completed"
    REJECTED = "rejected"


class HookType(str, enum.Enum):
    CURIOSITY_GAP = "curiosity_gap"
    BEFORE_AFTER = "before_after"
    CONTROVERSIAL_OPINION = "controversial_opinion"
    RELATABLE_STRUGGLE = "relatable_struggle"
    TUTORIAL_TEASER = "tutorial_teaser"
    TREND_REMIX = "trend_remix"


class Platform(str, enum.Enum):
    INSTAGRAM = "instagram"
    VK = "vk"
    TELEGRAM = "telegram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class TaskPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    DECOMPOSED = "decomposed"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkPlanStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class WorkPlanCategory(str, enum.Enum):
    DEVELOPMENT = "development"
    BUSINESS = "business"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    FINANCE = "finance"
    LEGAL = "legal"
    CONTENT = "content"
    SALES = "sales"
    OTHER = "other"


# ─── Character ──────────────────────────────────────────────────────────────


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    instagram_handle: Mapped[str] = mapped_column(String(100), default="")
    bio_ru: Mapped[str] = mapped_column(Text, default="")
    bio_en: Mapped[str] = mapped_column(Text, default="")

    # Visual characteristics
    age_range: Mapped[str] = mapped_column(String(20), default="22-25")
    ethnicity: Mapped[str] = mapped_column(String(50), default="european")
    hair_color: Mapped[str] = mapped_column(String(50), default="brunette")
    hair_style: Mapped[str] = mapped_column(String(100), default="long wavy")
    body_type: Mapped[str] = mapped_column(String(50), default="athletic")
    height_description: Mapped[str] = mapped_column(String(50), default="tall")
    distinguishing_features: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI model settings
    flux_model_version: Mapped[str] = mapped_column(
        String(200), default="black-forest-labs/flux-kontext-dev"
    )
    lora_model_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_image_urls: Mapped[str] = mapped_column(Text, default="[]")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    style_preset: Mapped[str] = mapped_column(String(100), default="instagram-fitness")

    # Personality for caption generation
    personality_traits: Mapped[str] = mapped_column(Text, default="[]")
    tone_of_voice: Mapped[str] = mapped_column(String(100), default="motivational, friendly")
    favorite_topics: Mapped[str] = mapped_column(Text, default="[]")
    emoji_style: Mapped[str] = mapped_column(String(100), default="moderate")

    # Character consistency (reference images for FLUX Kontext Pro)
    reference_image_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    secondary_references: Mapped[str] = mapped_column(Text, default="[]")

    # Voice (Fish Audio S1 voice clone)
    voice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Engagement style
    comment_reply_style: Mapped[str] = mapped_column(
        String(200), default="friendly, motivational, with emoji"
    )
    engagement_cta_templates: Mapped[str] = mapped_column(Text, default="[]")

    # TikTok
    tiktok_handle: Mapped[str] = mapped_column(String(100), default="")

    # Niche & platform settings
    niche: Mapped[str] = mapped_column(String(100), default="fitness")
    niche_description: Mapped[str] = mapped_column(
        Text, default="Женский фитнес, растяжка, шпагат, йога, гибкость"
    )
    platforms: Mapped[str] = mapped_column(Text, default='["instagram"]')
    growth_target: Mapped[int] = mapped_column(Integer, default=70000)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    content_categories: Mapped[str] = mapped_column(
        Text,
        default='["workout","lifestyle","motivation","outfit","nutrition","behind_scenes","transformation","tutorial"]',
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="character")
    campaigns: Mapped[list["Campaign"]] = relationship("Campaign", back_populates="character")


# ─── ContentTemplate ────────────────────────────────────────────────────────


class ContentTemplate(Base):
    __tablename__ = "content_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[ContentCategory] = mapped_column(Enum(ContentCategory), index=True)
    content_type: Mapped[ContentType] = mapped_column(Enum(ContentType), index=True)

    # Image generation
    image_prompt_template: Mapped[str] = mapped_column(Text, default="")
    scene_description: Mapped[str] = mapped_column(Text, default="")
    pose_description: Mapped[str] = mapped_column(String(500), default="")
    outfit_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lighting: Mapped[str] = mapped_column(String(200), default="natural daylight")
    camera_angle: Mapped[str] = mapped_column(String(100), default="portrait")
    aspect_ratio: Mapped[str] = mapped_column(String(10), default="4:5")

    # Caption generation
    caption_prompt_template_ru: Mapped[str] = mapped_column(Text, default="")
    caption_prompt_template_en: Mapped[str] = mapped_column(Text, default="")

    # Hashtags
    hashtag_sets: Mapped[str] = mapped_column(Text, default="[]")

    # Scheduling
    frequency_weight: Mapped[float] = mapped_column(Float, default=1.0)
    best_posting_times: Mapped[str] = mapped_column(Text, default="[]")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Post ───────────────────────────────────────────────────────────────────


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_templates.id"), nullable=True
    )

    content_type: Mapped[ContentType] = mapped_column(Enum(ContentType), index=True)
    category: Mapped[ContentCategory] = mapped_column(Enum(ContentCategory), index=True)
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus), default=PostStatus.DRAFT, index=True
    )
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform), default=Platform.INSTAGRAM, index=True
    )

    # Generated content
    image_prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    carousel_paths: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Captions
    caption_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Platform-specific IDs
    instagram_media_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instagram_permalink: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vk_post_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tiktok_video_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tiktok_share_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Audio/music metadata for publishing
    ig_sound_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tiktok_sound_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Generation metadata
    generation_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    generation_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    replicate_prediction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Viral content fields
    viral_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    hook_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # A/B test group
    ab_group: Mapped[str | None] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    character: Mapped["Character"] = relationship("Character", back_populates="posts")
    template: Mapped["ContentTemplate | None"] = relationship("ContentTemplate")
    analytics: Mapped["PostAnalytics | None"] = relationship(
        "PostAnalytics", back_populates="post", uselist=False
    )
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="post")


# ─── Story ──────────────────────────────────────────────────────────────────


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), nullable=True)

    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus), default=PostStatus.DRAFT, index=True
    )

    # Content
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Interactive elements (JSON array)
    interactive_elements: Mapped[str] = mapped_column(Text, default="[]")

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    instagram_story_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    character: Mapped["Character"] = relationship("Character")


# ─── PostAnalytics ──────────────────────────────────────────────────────────


class PostAnalytics(Base):
    __tablename__ = "post_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), unique=True, index=True)

    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    video_views: Mapped[int] = mapped_column(Integer, default=0)

    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post: Mapped["Post"] = relationship("Post", back_populates="analytics")


# ─── DailyMetrics ───────────────────────────────────────────────────────────


class DailyMetrics(Base):
    __tablename__ = "daily_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform), default=Platform.INSTAGRAM, index=True
    )
    character_id: Mapped[int | None] = mapped_column(
        ForeignKey("characters.id"), nullable=True, index=True
    )

    followers_count: Mapped[int] = mapped_column(Integer, default=0)
    followers_gained: Mapped[int] = mapped_column(Integer, default=0)
    followers_lost: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    posts_count: Mapped[int] = mapped_column(Integer, default=0)

    avg_engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_reach: Mapped[int] = mapped_column(Integer, default=0)
    total_impressions: Mapped[int] = mapped_column(Integer, default=0)
    profile_views: Mapped[int] = mapped_column(Integer, default=0)
    website_clicks: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Comment ────────────────────────────────────────────────────────────────


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform), default=Platform.INSTAGRAM, index=True
    )

    platform_comment_id: Mapped[str] = mapped_column(String(100), index=True)
    username: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)

    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_spam: Mapped[bool] = mapped_column(Boolean, default=False)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post: Mapped["Post"] = relationship("Post", back_populates="comments")


# ─── Campaign ───────────────────────────────────────────────────────────────


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    character_id: Mapped[int | None] = mapped_column(
        ForeignKey("characters.id"), nullable=True, index=True
    )
    brand_name: Mapped[str] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)

    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.PROSPECT
    )
    platform: Mapped[Platform | None] = mapped_column(Enum(Platform), nullable=True)

    budget: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    deliverables: Mapped[str] = mapped_column(Text, default="[]")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ОРД / ERID compliance
    erid_token: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ord_creative_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    character: Mapped["Character | None"] = relationship("Character", back_populates="campaigns")


# ─── SystemSettings ────────────────────────────────────────────────────────


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Autonomy toggles
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_reply_comments: Mapped[bool] = mapped_column(Boolean, default=False)

    # Posting schedule
    posts_per_day: Mapped[int] = mapped_column(Integer, default=2)
    stories_per_day: Mapped[int] = mapped_column(Integer, default=5)
    reels_per_week: Mapped[int] = mapped_column(Integer, default=3)

    # Content mix weights (JSON)
    content_mix: Mapped[str] = mapped_column(Text, default="{}")

    # Instagram session data (avoid re-login)
    instagram_session_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agent DM settings
    dm_notify_brands_immediately: Mapped[bool] = mapped_column(Boolean, default=True)
    dm_summary_interval_hours: Mapped[int] = mapped_column(Integer, default=1)
    ad_deal_require_approval: Mapped[bool] = mapped_column(Boolean, default=True)

    # Agent content strategy
    auto_analyze_competitors: Mapped[bool] = mapped_column(Boolean, default=True)
    reels_percentage: Mapped[int] = mapped_column(Integer, default=65)
    carousels_percentage: Mapped[int] = mapped_column(Integer, default=25)
    monthly_follower_target: Mapped[int] = mapped_column(Integer, default=10000)
    daily_post_budget_usd: Mapped[float] = mapped_column(Float, default=5.0)

    # Language mode
    caption_language: Mapped[str] = mapped_column(String(10), default="both")

    # Generation quality
    image_quality: Mapped[str] = mapped_column(String(20), default="high")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ─── GenerationLog ──────────────────────────────────────────────────────────


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)


# ─── ComplianceLog ─────────────────────────────────────────────────────────


class ComplianceLog(Base):
    __tablename__ = "compliance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    check_level: Mapped[str] = mapped_column(String(20))
    passed: Mapped[bool] = mapped_column(Boolean)
    violations: Mapped[str] = mapped_column(Text, default="[]")
    auto_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    iterations: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post: Mapped["Post"] = relationship("Post")


# ─── AgentDecision ─────────────────────────────────────────────────────────


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_type: Mapped[str] = mapped_column(String(100), index=True)
    input_context: Mapped[str] = mapped_column(Text, default="{}")
    decision: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    outcome_metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── AudienceInsight ───────────────────────────────────────────────────────


class AudienceInsight(Base):
    __tablename__ = "audience_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)

    demographics: Mapped[str] = mapped_column(Text, default="{}")
    active_hours: Mapped[str] = mapped_column(Text, default="[]")
    content_preferences: Mapped[str] = mapped_column(Text, default="{}")
    top_locations: Mapped[str] = mapped_column(Text, default="[]")
    recommendations: Mapped[str] = mapped_column(Text, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── CompetitorProfile ─────────────────────────────────────────────────────


class CompetitorProfile(Base):
    __tablename__ = "competitor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform), default=Platform.INSTAGRAM
    )

    followers: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    content_mix: Mapped[str] = mapped_column(Text, default="{}")
    top_hashtags: Mapped[str] = mapped_column(Text, default="[]")
    posting_times: Mapped[str] = mapped_column(Text, default="[]")
    strengths: Mapped[str] = mapped_column(Text, default="[]")
    gaps: Mapped[str] = mapped_column(Text, default="[]")

    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ─── DMConversation ────────────────────────────────────────────────────────


class DMConversation(Base):
    __tablename__ = "dm_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    platform_thread_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(200), index=True)
    username: Mapped[str] = mapped_column(String(200), default="")
    category: Mapped[DMCategory] = mapped_column(
        Enum(DMCategory), default=DMCategory.UNCATEGORIZED, index=True
    )
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[list["DMMessage"]] = relationship(
        "DMMessage", back_populates="conversation"
    )


# ─── DMMessage ─────────────────────────────────────────────────────────────


class DMMessage(Base):
    __tablename__ = "dm_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("dm_conversations.id"), index=True
    )
    direction: Mapped[str] = mapped_column(String(10))  # "inbound" / "outbound"
    text: Mapped[str] = mapped_column(Text)
    categorized_as: Mapped[str | None] = mapped_column(String(50), nullable=True)
    platform_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped["DMConversation"] = relationship(
        "DMConversation", back_populates="messages"
    )


# ─── AdDeal ────────────────────────────────────────────────────────────────


class AdDeal(Base):
    __tablename__ = "ad_deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    dm_conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("dm_conversations.id"), nullable=True, index=True
    )
    brand_name: Mapped[str] = mapped_column(String(200))
    brand_username: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[AdDealStatus] = mapped_column(
        Enum(AdDealStatus), default=AdDealStatus.DETECTED, index=True
    )

    brand_fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    proposed_price_usd: Mapped[float] = mapped_column(Float, default=0.0)
    market_rate_usd: Mapped[float] = mapped_column(Float, default=0.0)
    final_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    deliverables: Mapped[str] = mapped_column(Text, default="[]")
    proposal_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ─── TrendSnapshot ───────────────────────────────────────────────────────


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)

    # Trending sounds (JSON list)
    trending_sounds: Mapped[str] = mapped_column(Text, default="[]")
    # Trending hashtags (JSON list)
    trending_hashtags: Mapped[str] = mapped_column(Text, default="[]")
    # Trending video formats / camera techniques (Claude-extracted)
    trending_formats: Mapped[str] = mapped_column(Text, default="[]")
    # Trending content themes
    trending_themes: Mapped[str] = mapped_column(Text, default="[]")
    # Recommended music for IG (sound IDs from IG trending library)
    ig_trending_sound_ids: Mapped[str] = mapped_column(Text, default="[]")
    # Summary for prompts (pre-rendered by Claude)
    trend_summary: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── ConductorTask ────────────────────────────────────────────────────────


class ConductorTask(Base):
    __tablename__ = "conductor_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("conductor_tasks.id"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    agent_role: Mapped[str] = mapped_column(String(100), default="ceo_agent", index=True)

    # Иерархия: conductor → director → department → specialist
    level: Mapped[str] = mapped_column(String(20), default="conductor", index=True)
    assigned_to: Mapped[str] = mapped_column(String(100), default="", index=True)
    execution_order: Mapped[str] = mapped_column(String(20), default="parallel")
    dependencies: Mapped[str] = mapped_column(Text, default="[]")
    estimated_hours: Mapped[float] = mapped_column(Float, default=0.0)
    deliverables: Mapped[str] = mapped_column(Text, default="[]")

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), default=TaskPriority.NORMAL, index=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    context: Mapped[str] = mapped_column(Text, default="{}")
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[str] = mapped_column(String(100), default="founder")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    subtasks: Mapped[list["ConductorTask"]] = relationship(
        "ConductorTask", back_populates="parent"
    )
    parent: Mapped["ConductorTask | None"] = relationship(
        "ConductorTask", remote_side=[id], back_populates="subtasks"
    )
    logs: Mapped[list["ConductorLog"]] = relationship(
        "ConductorLog", back_populates="task"
    )


class ConductorLog(Base):
    __tablename__ = "conductor_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("conductor_tasks.id"), index=True
    )
    action: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["ConductorTask"] = relationship(
        "ConductorTask", back_populates="logs"
    )


# ─── Гранты и сохранённые идеи ──────────────────────────────────────────


class IdeaStatus(str, enum.Enum):
    DRAFT = "draft"
    SAVED = "saved"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    WON = "won"
    REJECTED = "rejected"


class GrantAnalysis(Base):
    """Анализ конкурса/гранта — правила, требования, сроки."""
    __tablename__ = "grant_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    grant_type: Mapped[str] = mapped_column(String(100), default="grant")
    fund_name: Mapped[str] = mapped_column(String(300), default="")
    deadline: Mapped[str] = mapped_column(String(200), default="")
    prize_amount: Mapped[str] = mapped_column(String(200), default="")
    requirements: Mapped[str] = mapped_column(Text, default="")
    reporting_rules: Mapped[str] = mapped_column(Text, default="")
    eligibility: Mapped[str] = mapped_column(Text, default="")
    timeline: Mapped[str] = mapped_column(Text, default="")
    full_analysis: Mapped[str] = mapped_column(Text, default="")
    ai_fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ideas: Mapped[list["SavedIdea"]] = relationship("SavedIdea", back_populates="grant")


class SavedIdea(Base):
    """Сохранённая идея для конкурса/гранта."""
    __tablename__ = "saved_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    grant_id: Mapped[int | None] = mapped_column(
        ForeignKey("grant_analyses.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    budget_json: Mapped[str] = mapped_column(Text, default="{}")
    timeline_plan: Mapped[str] = mapped_column(Text, default="")
    risks: Mapped[str] = mapped_column(Text, default="")
    expected_result: Mapped[str] = mapped_column(Text, default="")
    documents_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[IdeaStatus] = mapped_column(
        Enum(IdeaStatus), default=IdeaStatus.DRAFT
    )
    excel_path: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="telegram")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    grant: Mapped["GrantAnalysis | None"] = relationship(
        "GrantAnalysis", back_populates="ideas"
    )


# ─── ViralContentAnalysis ──────────────────────────────────────────────────


class ViralContentAnalysis(Base):
    __tablename__ = "viral_content_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    post_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id"), nullable=True, index=True
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_username: Mapped[str | None] = mapped_column(String(200), nullable=True)

    hook_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    why_viral: Mapped[str] = mapped_column(Text, default="")
    replication_strategy: Mapped[str] = mapped_column(Text, default="")
    estimated_reach: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── WorkPlan (планирование работ) ───────────────────────────────────────


class WorkPlan(Base):
    """Задача/план работы — личная или делегированная агенту."""
    __tablename__ = "work_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[WorkPlanCategory] = mapped_column(
        Enum(WorkPlanCategory), default=WorkPlanCategory.DEVELOPMENT, index=True
    )
    status: Mapped[WorkPlanStatus] = mapped_column(
        Enum(WorkPlanStatus), default=WorkPlanStatus.BACKLOG, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), default=TaskPriority.NORMAL, index=True
    )

    # Назначение: "founder" или имя агента ("ceo_agent", "certifier" и т.д.)
    assignee: Mapped[str] = mapped_column(String(100), default="founder", index=True)

    # Связь с ConductorTask
    conductor_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("conductor_tasks.id"), nullable=True, index=True
    )

    # Сроки
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_hours: Mapped[float] = mapped_column(Float, default=0.0)
    actual_hours: Mapped[float] = mapped_column(Float, default=0.0)

    # Прогресс 0-100
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # Результат
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    conductor_task: Mapped["ConductorTask | None"] = relationship("ConductorTask")
