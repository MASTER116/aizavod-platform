from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel

from .models import ContentCategory, ContentType, PostStatus, CampaignStatus, Platform, AdDealStatus, DMCategory


# ─── Auth ───────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Character ──────────────────────────────────────────────────────────────


class CharacterCreate(BaseModel):
    name: str
    instagram_handle: str = ""
    bio_ru: str = ""
    bio_en: str = ""
    age_range: str = "22-25"
    ethnicity: str = "european"
    hair_color: str = "brunette"
    hair_style: str = "long wavy"
    body_type: str = "athletic"
    height_description: str = "tall"
    distinguishing_features: Optional[str] = None
    flux_model_version: str = "black-forest-labs/flux-kontext-dev"
    lora_model_url: Optional[str] = None
    negative_prompt: str = ""
    style_preset: str = "instagram-fitness"
    personality_traits: str = "[]"
    tone_of_voice: str = "motivational, friendly"
    favorite_topics: str = "[]"
    emoji_style: str = "moderate"
    niche: str = "fitness"
    niche_description: str = "Женский фитнес, растяжка, шпагат, йога, гибкость"
    platforms: str = '["instagram"]'
    growth_target: int = 70000
    birthday: Optional[date] = None
    content_categories: str = '["workout","lifestyle","motivation","outfit","nutrition","behind_scenes","transformation","tutorial"]'


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    instagram_handle: Optional[str] = None
    bio_ru: Optional[str] = None
    bio_en: Optional[str] = None
    age_range: Optional[str] = None
    ethnicity: Optional[str] = None
    hair_color: Optional[str] = None
    hair_style: Optional[str] = None
    body_type: Optional[str] = None
    height_description: Optional[str] = None
    distinguishing_features: Optional[str] = None
    flux_model_version: Optional[str] = None
    lora_model_url: Optional[str] = None
    negative_prompt: Optional[str] = None
    style_preset: Optional[str] = None
    personality_traits: Optional[str] = None
    tone_of_voice: Optional[str] = None
    favorite_topics: Optional[str] = None
    emoji_style: Optional[str] = None
    niche: Optional[str] = None
    niche_description: Optional[str] = None
    platforms: Optional[str] = None
    growth_target: Optional[int] = None
    birthday: Optional[date] = None
    content_categories: Optional[str] = None


class CharacterRead(BaseModel):
    id: int
    name: str
    instagram_handle: str
    bio_ru: str
    bio_en: str
    age_range: str
    ethnicity: str
    hair_color: str
    hair_style: str
    body_type: str
    height_description: str
    distinguishing_features: Optional[str]
    flux_model_version: str
    lora_model_url: Optional[str]
    reference_image_urls: str
    negative_prompt: str
    style_preset: str
    personality_traits: str
    tone_of_voice: str
    favorite_topics: str
    emoji_style: str
    niche: str
    niche_description: str
    platforms: str
    growth_target: int
    birthday: Optional[date]
    content_categories: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── ContentTemplate ────────────────────────────────────────────────────────


class ContentTemplateCreate(BaseModel):
    name: str
    category: ContentCategory
    content_type: ContentType
    image_prompt_template: str = ""
    scene_description: str = ""
    pose_description: str = ""
    outfit_description: Optional[str] = None
    lighting: str = "natural daylight"
    camera_angle: str = "portrait"
    aspect_ratio: str = "4:5"
    caption_prompt_template_ru: str = ""
    caption_prompt_template_en: str = ""
    hashtag_sets: str = "[]"
    frequency_weight: float = 1.0
    best_posting_times: str = "[]"


class ContentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[ContentCategory] = None
    content_type: Optional[ContentType] = None
    image_prompt_template: Optional[str] = None
    scene_description: Optional[str] = None
    pose_description: Optional[str] = None
    outfit_description: Optional[str] = None
    lighting: Optional[str] = None
    camera_angle: Optional[str] = None
    aspect_ratio: Optional[str] = None
    caption_prompt_template_ru: Optional[str] = None
    caption_prompt_template_en: Optional[str] = None
    hashtag_sets: Optional[str] = None
    frequency_weight: Optional[float] = None
    best_posting_times: Optional[str] = None


class ContentTemplateRead(BaseModel):
    id: int
    name: str
    category: ContentCategory
    content_type: ContentType
    image_prompt_template: str
    scene_description: str
    pose_description: str
    outfit_description: Optional[str]
    lighting: str
    camera_angle: str
    aspect_ratio: str
    caption_prompt_template_ru: str
    caption_prompt_template_en: str
    hashtag_sets: str
    frequency_weight: float
    best_posting_times: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Post ───────────────────────────────────────────────────────────────────


class PostCreate(BaseModel):
    character_id: int
    template_id: Optional[int] = None
    content_type: ContentType = ContentType.PHOTO
    category: ContentCategory = ContentCategory.WORKOUT
    platform: Platform = Platform.INSTAGRAM
    caption_ru: Optional[str] = None
    caption_en: Optional[str] = None
    hashtags: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class PostUpdate(BaseModel):
    caption_ru: Optional[str] = None
    caption_en: Optional[str] = None
    hashtags: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[PostStatus] = None


class PostRead(BaseModel):
    id: int
    character_id: int
    template_id: Optional[int]
    content_type: ContentType
    category: ContentCategory
    status: PostStatus
    platform: Platform
    image_prompt_used: Optional[str]
    image_path: Optional[str]
    video_path: Optional[str]
    thumbnail_path: Optional[str]
    carousel_paths: Optional[str]
    caption_ru: Optional[str]
    caption_en: Optional[str]
    hashtags: Optional[str]
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    instagram_media_id: Optional[str]
    instagram_permalink: Optional[str]
    vk_post_id: Optional[str]
    telegram_message_id: Optional[str]
    generation_cost_usd: float
    generation_time_seconds: float
    ab_group: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Story ──────────────────────────────────────────────────────────────────


class StoryCreate(BaseModel):
    character_id: int
    post_id: Optional[int] = None
    caption_text: Optional[str] = None
    interactive_elements: str = "[]"
    scheduled_at: Optional[datetime] = None


class StoryUpdate(BaseModel):
    caption_text: Optional[str] = None
    interactive_elements: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[PostStatus] = None


class StoryRead(BaseModel):
    id: int
    character_id: int
    post_id: Optional[int]
    status: PostStatus
    image_path: Optional[str]
    video_path: Optional[str]
    caption_text: Optional[str]
    interactive_elements: str
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    expires_at: Optional[datetime]
    instagram_story_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── PostAnalytics ──────────────────────────────────────────────────────────


class PostAnalyticsRead(BaseModel):
    id: int
    post_id: int
    likes: int
    comments_count: int
    shares: int
    saves: int
    reach: int
    impressions: int
    engagement_rate: float
    video_views: int
    last_fetched_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── DailyMetrics ───────────────────────────────────────────────────────────


class DailyMetricsRead(BaseModel):
    id: int
    date: date
    platform: Platform
    character_id: Optional[int]
    followers_count: int
    followers_gained: int
    followers_lost: int
    following_count: int
    posts_count: int
    avg_engagement_rate: float
    total_reach: int
    total_impressions: int
    profile_views: int
    website_clicks: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Comment ────────────────────────────────────────────────────────────────


class CommentRead(BaseModel):
    id: int
    post_id: int
    platform: Platform
    platform_comment_id: str
    username: str
    text: str
    reply_text: Optional[str]
    reply_sent: bool
    reply_sent_at: Optional[datetime]
    is_spam: bool
    sentiment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Campaign ───────────────────────────────────────────────────────────────


class CampaignCreate(BaseModel):
    character_id: Optional[int] = None
    brand_name: str
    contact_email: Optional[str] = None
    contact_person: Optional[str] = None
    status: CampaignStatus = CampaignStatus.PROSPECT
    platform: Optional[Platform] = None
    budget: float = 0.0
    currency: str = "USD"
    deliverables: str = "[]"
    deadline: Optional[date] = None
    erid_token: Optional[str] = None
    notes: Optional[str] = None


class CampaignUpdate(BaseModel):
    character_id: Optional[int] = None
    brand_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_person: Optional[str] = None
    status: Optional[CampaignStatus] = None
    platform: Optional[Platform] = None
    budget: Optional[float] = None
    currency: Optional[str] = None
    deliverables: Optional[str] = None
    deadline: Optional[date] = None
    erid_token: Optional[str] = None
    ord_creative_id: Optional[str] = None
    notes: Optional[str] = None


class CampaignRead(BaseModel):
    id: int
    character_id: Optional[int]
    brand_name: str
    contact_email: Optional[str]
    contact_person: Optional[str]
    status: CampaignStatus
    platform: Optional[Platform]
    budget: float
    currency: str
    deliverables: str
    deadline: Optional[date]
    erid_token: Optional[str]
    ord_creative_id: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── SystemSettings ────────────────────────────────────────────────────────


class SystemSettingsRead(BaseModel):
    id: int
    auto_generate: bool
    auto_approve: bool
    auto_publish: bool
    auto_reply_comments: bool
    posts_per_day: int
    stories_per_day: int
    reels_per_week: int
    content_mix: str
    caption_language: str
    image_quality: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemSettingsUpdate(BaseModel):
    auto_generate: Optional[bool] = None
    auto_approve: Optional[bool] = None
    auto_publish: Optional[bool] = None
    auto_reply_comments: Optional[bool] = None
    posts_per_day: Optional[int] = None
    stories_per_day: Optional[int] = None
    reels_per_week: Optional[int] = None
    content_mix: Optional[str] = None
    caption_language: Optional[str] = None
    image_quality: Optional[str] = None


# ─── GenerationLog ──────────────────────────────────────────────────────────


class GenerationLogRead(BaseModel):
    id: int
    created_at: datetime
    action: str
    entity_type: str
    entity_id: Optional[int]
    status: str
    details: Optional[str]
    cost_usd: float
    duration_seconds: float

    model_config = {"from_attributes": True}


# ─── Image Generation ──────────────────────────────────────────────────────


class GenerateImageRequest(BaseModel):
    character_id: int
    prompt: str
    aspect_ratio: str = "4:5"
    use_lora: bool = False


class GenerateImageResponse(BaseModel):
    image_path: str
    prediction_id: str
    cost_usd: float
    duration_seconds: float


# ─── Analytics Overview ─────────────────────────────────────────────────────


class AnalyticsOverview(BaseModel):
    total_followers: int = 0
    followers_today: int = 0
    total_posts: int = 0
    avg_engagement_rate: float = 0.0
    total_reach_today: int = 0
    pending_posts: int = 0
    scheduled_posts: int = 0
    total_cost_usd: float = 0.0


# ─── ComplianceLog ─────────────────────────────────────────────────────────


class ComplianceLogRead(BaseModel):
    id: int
    post_id: int
    check_level: str
    passed: bool
    violations: str
    auto_fixed: bool
    iterations: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Agent ─────────────────────────────────────────────────────────────────


class AgentStatusResponse(BaseModel):
    decisions_today: int
    max_daily_decisions: int
    decisions_remaining: int
    last_decision_at: Optional[str] = None
    last_action: Optional[str] = None
    errors_today: int
    model: str


class AgentDecisionRead(BaseModel):
    id: int
    task_type: str
    decision: str
    reasoning: Optional[str] = None
    confidence_score: float
    executed: bool
    error: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentTriggerRequest(BaseModel):
    task_type: str


# ─── DMs ───────────────────────────────────────────────────────────────────


class DMConversationRead(BaseModel):
    id: int
    platform_thread_id: str
    user_id: str
    username: str
    category: DMCategory
    unread_count: int
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DMMessageRead(BaseModel):
    id: int
    conversation_id: int
    direction: str
    text: str
    categorized_as: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DMSummaryResponse(BaseModel):
    total_conversations: int
    total_unread: int
    by_category: dict


# ─── Ad Deals ──────────────────────────────────────────────────────────────


class AdDealRead(BaseModel):
    id: int
    character_id: int
    brand_name: str
    brand_username: Optional[str] = None
    status: AdDealStatus
    brand_fit_score: float
    proposed_price_usd: float
    market_rate_usd: float
    final_price_usd: Optional[float] = None
    brief: Optional[str] = None
    deliverables: str
    proposal_draft: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealApproveRequest(BaseModel):
    deal_id: int


class DealRejectRequest(BaseModel):
    deal_id: int
    reason: str = ""
