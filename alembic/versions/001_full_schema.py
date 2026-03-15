"""Full schema — v1 + v2 tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create all enums first via raw SQL ────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contentcategory AS ENUM (
                'workout','lifestyle','motivation','outfit','nutrition',
                'behind_scenes','transformation','tutorial','collaboration'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contenttype AS ENUM ('photo','carousel','story','reel');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE poststatus AS ENUM (
                'draft','generating','generated','review','approved',
                'scheduled','publishing','published','failed','archived'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE platform AS ENUM ('instagram','vk','telegram','youtube','tiktok');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE campaignstatus AS ENUM (
                'prospect','outreach','negotiation','confirmed',
                'in_progress','completed','cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dmcategory AS ENUM (
                'fan','brand_inquiry','spam','question','uncategorized'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE addealstatus AS ENUM (
                'detected','evaluating','awaiting_approval','proposal_sent',
                'negotiating','brief_received','content_creating','published',
                'payment_pending','completed','rejected'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # ── characters ───────────────────────────────────────
    op.execute("""
        CREATE TABLE characters (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            instagram_handle VARCHAR(100) DEFAULT '',
            bio_ru TEXT DEFAULT '',
            bio_en TEXT DEFAULT '',
            age_range VARCHAR(20) DEFAULT '22-25',
            ethnicity VARCHAR(50) DEFAULT 'european',
            hair_color VARCHAR(50) DEFAULT 'brunette',
            hair_style VARCHAR(100) DEFAULT 'long wavy',
            body_type VARCHAR(50) DEFAULT 'athletic',
            height_description VARCHAR(50) DEFAULT 'tall',
            distinguishing_features TEXT,
            flux_model_version VARCHAR(200) DEFAULT 'black-forest-labs/flux-kontext-dev',
            lora_model_url VARCHAR(500),
            reference_image_urls TEXT DEFAULT '[]',
            negative_prompt TEXT DEFAULT '',
            style_preset VARCHAR(100) DEFAULT 'instagram-fitness',
            personality_traits TEXT DEFAULT '[]',
            tone_of_voice VARCHAR(100) DEFAULT 'motivational, friendly',
            favorite_topics TEXT DEFAULT '[]',
            emoji_style VARCHAR(100) DEFAULT 'moderate',
            niche VARCHAR(100) DEFAULT 'fitness',
            niche_description TEXT DEFAULT '',
            platforms TEXT DEFAULT '["instagram"]',
            growth_target INTEGER DEFAULT 70000,
            birthday DATE,
            content_categories TEXT DEFAULT '[]',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            -- v2 columns
            reference_image_base64 TEXT,
            secondary_references TEXT DEFAULT '[]',
            voice_id VARCHAR(200),
            tiktok_handle VARCHAR(100) DEFAULT ''
        );
        CREATE INDEX ix_characters_id ON characters(id);
    """)

    # ── content_templates ────────────────────────────────
    op.execute("""
        CREATE TABLE content_templates (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category contentcategory,
            content_type contenttype,
            image_prompt_template TEXT DEFAULT '',
            scene_description TEXT DEFAULT '',
            pose_description VARCHAR(500) DEFAULT '',
            outfit_description TEXT,
            lighting VARCHAR(200) DEFAULT 'natural daylight',
            camera_angle VARCHAR(100) DEFAULT 'portrait',
            aspect_ratio VARCHAR(10) DEFAULT '4:5',
            caption_prompt_template_ru TEXT DEFAULT '',
            caption_prompt_template_en TEXT DEFAULT '',
            hashtag_sets TEXT DEFAULT '[]',
            frequency_weight FLOAT DEFAULT 1.0,
            best_posting_times TEXT DEFAULT '[]',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_content_templates_id ON content_templates(id);
        CREATE INDEX ix_content_templates_category ON content_templates(category);
        CREATE INDEX ix_content_templates_content_type ON content_templates(content_type);
    """)

    # ── posts ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE posts (
            id SERIAL PRIMARY KEY,
            character_id INTEGER NOT NULL REFERENCES characters(id),
            template_id INTEGER REFERENCES content_templates(id),
            content_type contenttype,
            category contentcategory,
            status poststatus DEFAULT 'draft',
            platform platform DEFAULT 'instagram',
            image_prompt_used TEXT,
            image_path VARCHAR(500),
            video_path VARCHAR(500),
            thumbnail_path VARCHAR(500),
            carousel_paths TEXT,
            caption_ru TEXT,
            caption_en TEXT,
            hashtags TEXT,
            scheduled_at TIMESTAMP,
            published_at TIMESTAMP,
            instagram_media_id VARCHAR(100),
            instagram_permalink VARCHAR(500),
            vk_post_id VARCHAR(100),
            telegram_message_id VARCHAR(100),
            generation_cost_usd FLOAT DEFAULT 0.0,
            generation_time_seconds FLOAT DEFAULT 0.0,
            replicate_prediction_id VARCHAR(100),
            ab_group VARCHAR(10),
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            -- v2 columns
            tiktok_video_id VARCHAR(100),
            tiktok_share_url VARCHAR(500),
            ig_sound_id VARCHAR(100),
            tiktok_sound_id VARCHAR(100),
            viral_score FLOAT,
            hook_text VARCHAR(500),
            cover_text VARCHAR(500),
            audio_path VARCHAR(500),
            audio_source VARCHAR(50)
        );
        CREATE INDEX ix_posts_id ON posts(id);
        CREATE INDEX ix_posts_character_id ON posts(character_id);
        CREATE INDEX ix_posts_content_type ON posts(content_type);
        CREATE INDEX ix_posts_category ON posts(category);
        CREATE INDEX ix_posts_status ON posts(status);
        CREATE INDEX ix_posts_platform ON posts(platform);
        CREATE INDEX ix_posts_scheduled_at ON posts(scheduled_at);
    """)

    # ── stories ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE stories (
            id SERIAL PRIMARY KEY,
            character_id INTEGER NOT NULL REFERENCES characters(id),
            post_id INTEGER REFERENCES posts(id),
            status poststatus DEFAULT 'draft',
            image_path VARCHAR(500),
            video_path VARCHAR(500),
            caption_text TEXT,
            interactive_elements TEXT DEFAULT '[]',
            scheduled_at TIMESTAMP,
            published_at TIMESTAMP,
            expires_at TIMESTAMP,
            instagram_story_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_stories_id ON stories(id);
        CREATE INDEX ix_stories_character_id ON stories(character_id);
        CREATE INDEX ix_stories_status ON stories(status);
        CREATE INDEX ix_stories_scheduled_at ON stories(scheduled_at);
    """)

    # ── post_analytics ───────────────────────────────────
    op.execute("""
        CREATE TABLE post_analytics (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL UNIQUE REFERENCES posts(id),
            likes INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            engagement_rate FLOAT DEFAULT 0.0,
            video_views INTEGER DEFAULT 0,
            last_fetched_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_post_analytics_id ON post_analytics(id);
        CREATE INDEX ix_post_analytics_post_id ON post_analytics(post_id);
    """)

    # ── daily_metrics ────────────────────────────────────
    op.execute("""
        CREATE TABLE daily_metrics (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            platform platform DEFAULT 'instagram',
            character_id INTEGER REFERENCES characters(id),
            followers_count INTEGER DEFAULT 0,
            followers_gained INTEGER DEFAULT 0,
            followers_lost INTEGER DEFAULT 0,
            following_count INTEGER DEFAULT 0,
            posts_count INTEGER DEFAULT 0,
            avg_engagement_rate FLOAT DEFAULT 0.0,
            total_reach INTEGER DEFAULT 0,
            total_impressions INTEGER DEFAULT 0,
            profile_views INTEGER DEFAULT 0,
            website_clicks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_daily_metrics_id ON daily_metrics(id);
        CREATE INDEX ix_daily_metrics_date ON daily_metrics(date);
        CREATE INDEX ix_daily_metrics_platform ON daily_metrics(platform);
        CREATE INDEX ix_daily_metrics_character_id ON daily_metrics(character_id);
    """)

    # ── comments ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE comments (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL REFERENCES posts(id),
            platform platform DEFAULT 'instagram',
            platform_comment_id VARCHAR(100) NOT NULL,
            username VARCHAR(100) NOT NULL,
            text TEXT NOT NULL,
            reply_text TEXT,
            reply_sent BOOLEAN DEFAULT false,
            reply_sent_at TIMESTAMP,
            is_spam BOOLEAN DEFAULT false,
            sentiment VARCHAR(20),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_comments_id ON comments(id);
        CREATE INDEX ix_comments_post_id ON comments(post_id);
        CREATE INDEX ix_comments_platform ON comments(platform);
        CREATE INDEX ix_comments_platform_comment_id ON comments(platform_comment_id);
    """)

    # ── campaigns ────────────────────────────────────────
    op.execute("""
        CREATE TABLE campaigns (
            id SERIAL PRIMARY KEY,
            character_id INTEGER REFERENCES characters(id),
            brand_name VARCHAR(200) NOT NULL,
            contact_email VARCHAR(255),
            contact_person VARCHAR(200),
            status campaignstatus DEFAULT 'prospect',
            platform platform,
            budget FLOAT DEFAULT 0.0,
            currency VARCHAR(3) DEFAULT 'USD',
            deliverables TEXT DEFAULT '[]',
            deadline DATE,
            erid_token VARCHAR(200),
            ord_creative_id VARCHAR(200),
            notes TEXT,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_campaigns_id ON campaigns(id);
        CREATE INDEX ix_campaigns_character_id ON campaigns(character_id);
    """)

    # ── system_settings ──────────────────────────────────
    op.execute("""
        CREATE TABLE system_settings (
            id SERIAL PRIMARY KEY,
            auto_generate BOOLEAN DEFAULT false,
            auto_approve BOOLEAN DEFAULT false,
            auto_publish BOOLEAN DEFAULT false,
            auto_reply_comments BOOLEAN DEFAULT false,
            posts_per_day INTEGER DEFAULT 2,
            stories_per_day INTEGER DEFAULT 5,
            reels_per_week INTEGER DEFAULT 3,
            content_mix TEXT DEFAULT '{}',
            instagram_session_data TEXT,
            caption_language VARCHAR(10) DEFAULT 'both',
            image_quality VARCHAR(20) DEFAULT 'high',
            updated_at TIMESTAMP DEFAULT now(),
            -- v2 columns
            dm_notify_brands_immediately BOOLEAN DEFAULT true,
            dm_summary_interval_hours INTEGER DEFAULT 1,
            ad_deal_require_approval BOOLEAN DEFAULT true,
            auto_analyze_competitors BOOLEAN DEFAULT true,
            reels_percentage INTEGER DEFAULT 65,
            carousels_percentage INTEGER DEFAULT 25,
            monthly_follower_target INTEGER DEFAULT 10000,
            daily_post_budget_usd FLOAT DEFAULT 5.0
        );
    """)

    # ── generation_logs ──────────────────────────────────
    op.execute("""
        CREATE TABLE generation_logs (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT now(),
            action VARCHAR(64) NOT NULL,
            entity_type VARCHAR(32) NOT NULL,
            entity_id INTEGER,
            status VARCHAR(20) NOT NULL,
            details TEXT,
            cost_usd FLOAT DEFAULT 0.0,
            duration_seconds FLOAT DEFAULT 0.0
        );
    """)

    # ── compliance_logs ──────────────────────────────────
    op.execute("""
        CREATE TABLE compliance_logs (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL REFERENCES posts(id),
            check_level VARCHAR(20) NOT NULL,
            passed BOOLEAN NOT NULL,
            violations TEXT DEFAULT '[]',
            auto_fixed BOOLEAN DEFAULT false,
            iterations INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_compliance_logs_post_id ON compliance_logs(post_id);
    """)

    # ── v2: agent_decisions ──────────────────────────────
    op.execute("""
        CREATE TABLE agent_decisions (
            id SERIAL PRIMARY KEY,
            task_type VARCHAR(64) NOT NULL,
            input_context TEXT DEFAULT '{}',
            decision TEXT NOT NULL,
            reasoning TEXT,
            confidence_score FLOAT DEFAULT 0.0,
            outcome_metrics TEXT,
            executed BOOLEAN DEFAULT false,
            error TEXT,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_agent_decisions_task_type ON agent_decisions(task_type);
    """)

    # ── v2: audience_insights ────────────────────────────
    op.execute("""
        CREATE TABLE audience_insights (
            id SERIAL PRIMARY KEY,
            character_id INTEGER NOT NULL REFERENCES characters(id),
            snapshot_date DATE NOT NULL,
            demographics TEXT DEFAULT '{}',
            active_hours TEXT DEFAULT '[]',
            content_preferences TEXT DEFAULT '{}',
            top_locations TEXT DEFAULT '[]',
            recommendations TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_audience_insights_character_id ON audience_insights(character_id);
        CREATE INDEX ix_audience_insights_snapshot_date ON audience_insights(snapshot_date);
    """)

    # ── v2: competitor_profiles ──────────────────────────
    op.execute("""
        CREATE TABLE competitor_profiles (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            platform platform DEFAULT 'instagram',
            followers INTEGER DEFAULT 0,
            engagement_rate FLOAT DEFAULT 0.0,
            content_mix TEXT DEFAULT '{}',
            top_hashtags TEXT DEFAULT '[]',
            posting_times TEXT DEFAULT '[]',
            strengths TEXT DEFAULT '[]',
            gaps TEXT DEFAULT '[]',
            last_analyzed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_competitor_profiles_username ON competitor_profiles(username);
    """)

    # ── v2: dm_conversations ─────────────────────────────
    op.execute("""
        CREATE TABLE dm_conversations (
            id SERIAL PRIMARY KEY,
            character_id INTEGER NOT NULL REFERENCES characters(id),
            platform_thread_id VARCHAR(200) NOT NULL UNIQUE,
            user_id VARCHAR(100) NOT NULL,
            username VARCHAR(100) NOT NULL,
            category dmcategory DEFAULT 'uncategorized',
            unread_count INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 0,
            notified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_dm_conversations_character_id ON dm_conversations(character_id);
        CREATE INDEX ix_dm_conversations_platform_thread_id ON dm_conversations(platform_thread_id);
        CREATE INDEX ix_dm_conversations_user_id ON dm_conversations(user_id);
        CREATE INDEX ix_dm_conversations_category ON dm_conversations(category);
    """)

    # ── v2: dm_messages ──────────────────────────────────
    op.execute("""
        CREATE TABLE dm_messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES dm_conversations(id),
            direction VARCHAR(10) NOT NULL,
            text TEXT NOT NULL,
            categorized_as VARCHAR(50),
            platform_message_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_dm_messages_conversation_id ON dm_messages(conversation_id);
    """)

    # ── v2: ad_deals ─────────────────────────────────────
    op.execute("""
        CREATE TABLE ad_deals (
            id SERIAL PRIMARY KEY,
            character_id INTEGER NOT NULL REFERENCES characters(id),
            dm_conversation_id INTEGER REFERENCES dm_conversations(id),
            brand_name VARCHAR(200) NOT NULL,
            brand_username VARCHAR(100),
            status addealstatus DEFAULT 'detected',
            brand_fit_score FLOAT DEFAULT 0.0,
            proposed_price_usd FLOAT DEFAULT 0.0,
            market_rate_usd FLOAT DEFAULT 0.0,
            final_price_usd FLOAT,
            brief TEXT,
            deliverables TEXT DEFAULT '[]',
            proposal_draft TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_ad_deals_character_id ON ad_deals(character_id);
        CREATE INDEX ix_ad_deals_dm_conversation_id ON ad_deals(dm_conversation_id);
        CREATE INDEX ix_ad_deals_status ON ad_deals(status);
    """)

    # ── v2: trend_snapshots ──────────────────────────────
    op.execute("""
        CREATE TABLE trend_snapshots (
            id SERIAL PRIMARY KEY,
            platform platform,
            snapshot_date DATE NOT NULL,
            trending_sounds TEXT DEFAULT '[]',
            trending_hashtags TEXT DEFAULT '[]',
            trending_formats TEXT DEFAULT '[]',
            trending_themes TEXT DEFAULT '[]',
            ig_trending_sound_ids TEXT DEFAULT '[]',
            trend_summary TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_trend_snapshots_platform ON trend_snapshots(platform);
        CREATE INDEX ix_trend_snapshots_snapshot_date ON trend_snapshots(snapshot_date);
    """)

    # ── v2: viral_content_analyses ───────────────────────
    op.execute("""
        CREATE TABLE viral_content_analyses (
            id SERIAL PRIMARY KEY,
            character_id INTEGER NOT NULL REFERENCES characters(id),
            post_id INTEGER REFERENCES posts(id),
            source_url VARCHAR(500),
            source_username VARCHAR(100),
            hook_type VARCHAR(50),
            why_viral TEXT DEFAULT '',
            replication_strategy TEXT DEFAULT '',
            estimated_reach INTEGER DEFAULT 0,
            content_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX ix_viral_content_analyses_character_id ON viral_content_analyses(character_id);
        CREATE INDEX ix_viral_content_analyses_post_id ON viral_content_analyses(post_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS viral_content_analyses CASCADE")
    op.execute("DROP TABLE IF EXISTS trend_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS ad_deals CASCADE")
    op.execute("DROP TABLE IF EXISTS dm_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS dm_conversations CASCADE")
    op.execute("DROP TABLE IF EXISTS competitor_profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS audience_insights CASCADE")
    op.execute("DROP TABLE IF EXISTS agent_decisions CASCADE")
    op.execute("DROP TABLE IF EXISTS compliance_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS generation_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS system_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS campaigns CASCADE")
    op.execute("DROP TABLE IF EXISTS comments CASCADE")
    op.execute("DROP TABLE IF EXISTS daily_metrics CASCADE")
    op.execute("DROP TABLE IF EXISTS post_analytics CASCADE")
    op.execute("DROP TABLE IF EXISTS stories CASCADE")
    op.execute("DROP TABLE IF EXISTS posts CASCADE")
    op.execute("DROP TABLE IF EXISTS content_templates CASCADE")
    op.execute("DROP TABLE IF EXISTS characters CASCADE")
    op.execute("DROP TYPE IF EXISTS addealstatus")
    op.execute("DROP TYPE IF EXISTS dmcategory")
    op.execute("DROP TYPE IF EXISTS campaignstatus")
    op.execute("DROP TYPE IF EXISTS platform")
    op.execute("DROP TYPE IF EXISTS poststatus")
    op.execute("DROP TYPE IF EXISTS contenttype")
    op.execute("DROP TYPE IF EXISTS contentcategory")
