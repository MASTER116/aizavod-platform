"""Agent Orchestrator — the autonomous 'brain' of AIZAVOD.

Runs every 15 minutes, gathers system state, asks Claude to prioritize tasks,
and dispatches actions to sub-services (viral_engine, dm_manager, ad_manager, etc.).

Every decision is logged to AgentDecision for full transparency and learning.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_agent_config, get_anthropic_config
from backend.database import SessionLocal
from backend.models import (
    AgentDecision,
    AudienceInsight,
    Character,
    CompetitorProfile,
    DailyMetrics,
    DMConversation,
    AdDeal,
    Post,
    PostAnalytics,
    PostStatus,
    SystemSettings,
)

logger = logging.getLogger("aizavod.agent_orchestrator")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


ORCHESTRATOR_PROMPT = """Ты — автономный агент-менеджер аккаунта @nika_flexx.
Твоя цель: вырастить аккаунт с {current_followers} до {target_followers} подписчиков.

=== ТЕКУЩЕЕ СОСТОЯНИЕ ===

Подписчики: {current_followers}
Средний ER за 7 дней: {avg_er:.2f}%
Постов за 7 дней: {posts_last_7d}
Непрочитанных DM: {unread_dms}
Активных рекламных сделок: {active_deals}
Постов в очереди (draft/generating/scheduled): {pipeline_count}
Бюджет на генерацию в день: ${daily_budget:.2f}
Потрачено сегодня: ${spent_today:.2f}

Лучшие посты за 7 дней (по ER):
{top_posts}

Последний анализ аудитории: {audience_summary}
Последний анализ конкурентов: {competitor_summary}
Тренды (TikTok + IG): {trend_summary}

=== ДОСТУПНЫЕ ДЕЙСТВИЯ ===

1. generate_content — создать новый контент (reel/carousel/photo/story)
2. analyze_audience — запустить анализ аудитории
3. analyze_competitors — запустить анализ конкурентов
4. analyze_viral_patterns — проанализировать вирусные паттерны
5. process_dms — обработать входящие DM (чтение + категоризация)
6. evaluate_deal — оценить рекламную сделку
7. adjust_strategy — скорректировать контент-стратегию
8. engagement_loop — запустить цикл engagement (лайки, комменты в нише)
9. analyze_trends — анализ трендов TikTok + IG (каждые 4ч автоматически, но можно запустить вручную)
10. generate_long_video — запустить генерацию 65-секундного видео ($5.18/видео, бюджет-гейт)
11. skip — нет срочных задач, пропустить цикл

=== ПРАВИЛА ===

- Максимум {max_decisions} решений в день (осталось: {decisions_remaining})
- Приоритеты: контент > engagement > DM > аналитика > реклама
- Reels = 65% контента, Carousels = 25%, Photo = 10%
- Всегда объясняй reasoning
- Если бюджет исчерпан — не генерировать контент, сосредоточиться на engagement

Выбери 1-3 приоритетных действия и объясни почему.

Ответь ТОЛЬКО в формате JSON:
{{
  "priorities": [
    {{
      "action": "generate_content",
      "params": {{"content_type": "reel", "category": "workout", "description": "..."}},
      "reasoning": "...",
      "confidence": 0.0-1.0
    }}
  ]
}}"""


async def run_cycle() -> list[dict]:
    """Execute one orchestrator cycle: gather state → prioritize → execute.

    Returns list of executed decisions.
    """
    agent_cfg = get_agent_config()
    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings:
            logger.warning("No SystemSettings found, skipping agent cycle")
            return []

        character = _get_active_character(db)
        if not character:
            logger.warning("No active character, skipping agent cycle")
            return []

        # Check daily decision budget
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        decisions_today = (
            db.query(AgentDecision)
            .filter(AgentDecision.created_at >= today_start)
            .count()
        )
        remaining = agent_cfg.max_daily_decisions - decisions_today
        if remaining <= 0:
            logger.info("Daily decision limit reached (%d), skipping cycle", agent_cfg.max_daily_decisions)
            return []

        # Gather state
        state = await _gather_state(db, character, settings)
        state["max_decisions"] = agent_cfg.max_daily_decisions
        state["decisions_remaining"] = remaining

        # Ask Claude for priorities
        priorities = await _get_priorities(state, agent_cfg.orchestrator_model)

        # Execute each priority
        results = []
        for priority in priorities:
            action = priority.get("action", "skip")
            if action == "skip":
                continue

            decision = AgentDecision(
                task_type=action,
                input_context=json.dumps(state, ensure_ascii=False, default=str)[:4000],
                decision=json.dumps(priority, ensure_ascii=False),
                reasoning=priority.get("reasoning", ""),
                confidence_score=priority.get("confidence", 0.5),
            )
            db.add(decision)
            db.flush()

            try:
                result = await _execute_action(action, priority.get("params", {}), character, db, settings)
                decision.executed = True
                decision.outcome_metrics = json.dumps(result, ensure_ascii=False, default=str)[:2000]
                results.append({"action": action, "result": result})
                logger.info("Agent executed: %s (confidence=%.2f)", action, priority.get("confidence", 0))
            except Exception as e:
                decision.error = str(e)[:1000]
                logger.error("Agent action %s failed: %s", action, e)

            db.commit()

        return results

    finally:
        db.close()


async def _gather_state(db, character: Character, settings: SystemSettings) -> dict:
    """Collect current system state for the orchestrator prompt."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Posts in last 7 days
    posts_7d = (
        db.query(Post)
        .filter(Post.character_id == character.id)
        .filter(Post.status == PostStatus.PUBLISHED)
        .filter(Post.published_at >= week_ago)
        .all()
    )

    # Average ER from PostAnalytics
    avg_er = 0.0
    top_posts_text = "No published posts yet"
    if posts_7d:
        ers = []
        post_summaries = []
        for p in posts_7d:
            analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == p.id).first()
            if analytics and analytics.engagement_rate:
                ers.append(analytics.engagement_rate)
                post_summaries.append(
                    f"- {p.content_type.value} ({p.category.value}): ER={analytics.engagement_rate:.2f}%, "
                    f"likes={analytics.likes}, saves={analytics.saves}"
                )
        if ers:
            avg_er = sum(ers) / len(ers)
        if post_summaries:
            post_summaries.sort(reverse=True)
            top_posts_text = "\n".join(post_summaries[:5])

    # Pipeline count
    pipeline = (
        db.query(Post)
        .filter(Post.character_id == character.id)
        .filter(Post.status.in_([PostStatus.DRAFT, PostStatus.GENERATING, PostStatus.SCHEDULED]))
        .count()
    )

    # Unread DMs
    unread_dms = (
        db.query(DMConversation)
        .filter(DMConversation.character_id == character.id)
        .filter(DMConversation.unread_count > 0)
        .count()
    )

    # Active deals
    active_deals = (
        db.query(AdDeal)
        .filter(AdDeal.character_id == character.id)
        .filter(AdDeal.status.notin_(["completed", "cancelled"]))
        .count()
    )

    # Current followers from latest DailyMetrics
    latest_metrics = (
        db.query(DailyMetrics)
        .order_by(DailyMetrics.date.desc())
        .first()
    )
    current_followers = latest_metrics.followers_count if latest_metrics else 0

    # Audience summary
    latest_insight = (
        db.query(AudienceInsight)
        .filter(AudienceInsight.character_id == character.id)
        .order_by(AudienceInsight.snapshot_date.desc())
        .first()
    )
    audience_summary = "No audience analysis yet"
    if latest_insight and latest_insight.recommendations:
        audience_summary = latest_insight.recommendations[:300]

    # Competitor summary
    competitors = (
        db.query(CompetitorProfile)
        .filter(CompetitorProfile.character_id == character.id)
        .order_by(CompetitorProfile.last_analyzed_at.desc())
        .limit(3)
        .all()
    )
    competitor_summary = "No competitor analysis yet"
    if competitors:
        comp_parts = [f"@{c.username} ({c.followers_count} followers)" for c in competitors]
        competitor_summary = ", ".join(comp_parts)

    # Spent today — sum of generation costs
    from backend.models import GenerationLog
    spent_today = 0.0
    today_logs = (
        db.query(GenerationLog)
        .filter(GenerationLog.created_at >= today_start)
        .filter(GenerationLog.action == "generate")
        .all()
    )
    for log in today_logs:
        try:
            details = json.loads(log.details or "{}")
            spent_today += details.get("cost_usd", 0.0)
        except (json.JSONDecodeError, TypeError):
            pass

    # Trend summary
    trend_summary = "No trend data yet"
    try:
        from services.trend_analyzer import get_latest_trend_summary
        trend_summary = await get_latest_trend_summary()
    except Exception:
        pass

    return {
        "current_followers": current_followers,
        "target_followers": settings.monthly_follower_target,
        "avg_er": avg_er,
        "posts_last_7d": len(posts_7d),
        "unread_dms": unread_dms,
        "active_deals": active_deals,
        "pipeline_count": pipeline,
        "daily_budget": settings.daily_post_budget_usd,
        "spent_today": spent_today,
        "top_posts": top_posts_text,
        "audience_summary": audience_summary,
        "competitor_summary": competitor_summary,
        "trend_summary": trend_summary,
    }


async def _get_priorities(state: dict, model: str) -> list[dict]:
    """Ask Claude Opus to prioritize actions based on current state."""
    client = _get_client()

    prompt = ORCHESTRATOR_PROMPT.format(**state)

    message = await client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        data = json.loads(response_text)
        return data.get("priorities", [])
    except json.JSONDecodeError:
        logger.error("Failed to parse orchestrator JSON: %s", response_text[:200])
        return []


async def _execute_action(
    action: str,
    params: dict,
    character: Character,
    db,
    settings: SystemSettings,
) -> dict:
    """Route an action to the appropriate sub-service."""
    if action == "generate_content":
        return await _action_generate_content(params, character, db)
    elif action == "analyze_audience":
        return await _action_analyze_audience(character)
    elif action == "analyze_competitors":
        return await _action_analyze_competitors(character)
    elif action == "analyze_viral_patterns":
        return await _action_analyze_viral(character)
    elif action == "process_dms":
        return await _action_process_dms(character)
    elif action == "evaluate_deal":
        return await _action_evaluate_deal(params, character, db)
    elif action == "adjust_strategy":
        return await _action_adjust_strategy(character, db, settings)
    elif action == "engagement_loop":
        return await _action_engagement_loop(character)
    elif action == "analyze_trends":
        return await _action_analyze_trends()
    elif action == "generate_long_video":
        return await _action_generate_long_video(params, character, db, settings)
    else:
        logger.warning("Unknown agent action: %s", action)
        return {"status": "skipped", "reason": f"unknown action: {action}"}


async def _action_generate_content(params: dict, character: Character, db) -> dict:
    """Generate a piece of content based on agent parameters."""
    from backend.models import ContentCategory, ContentType

    content_type_str = params.get("content_type", "reel")
    category_str = params.get("category", "workout")
    description = params.get("description", "")

    try:
        content_type = ContentType(content_type_str)
    except ValueError:
        content_type = ContentType.REEL

    try:
        category = ContentCategory(category_str)
    except ValueError:
        category = ContentCategory.WORKOUT

    # Create a draft post
    post = Post(
        character_id=character.id,
        content_type=content_type,
        category=category,
        status=PostStatus.DRAFT,
        image_prompt_used=description,
    )
    db.add(post)
    db.commit()

    return {
        "status": "draft_created",
        "post_id": post.id,
        "content_type": content_type.value,
        "category": category.value,
    }


async def _action_analyze_audience(character: Character) -> dict:
    """Trigger audience analysis."""
    try:
        from services.audience_analyzer import analyze_audience
        result = await analyze_audience(character)
        return {"status": "completed", "insight_id": result.get("id")}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _action_analyze_competitors(character: Character) -> dict:
    """Trigger competitor analysis."""
    try:
        from services.audience_analyzer import analyze_competitors
        result = await analyze_competitors(character)
        return {"status": "completed", "competitors_analyzed": result.get("count", 0)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _action_analyze_viral(character: Character) -> dict:
    """Trigger viral pattern analysis."""
    try:
        from services.viral_engine import analyze_viral_patterns
        result = await analyze_viral_patterns(character)
        return {"status": "completed", "patterns_found": result.get("count", 0)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _action_process_dms(character: Character) -> dict:
    """Trigger DM processing (read + categorize + notify)."""
    try:
        from services.dm_manager import process_dm_inbox
        result = await process_dm_inbox(character)
        return {"status": "completed", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _action_evaluate_deal(params: dict, character: Character, db) -> dict:
    """Evaluate a potential ad deal."""
    deal_id = params.get("deal_id")
    if not deal_id:
        return {"status": "skipped", "reason": "no deal_id provided"}

    try:
        from services.ad_manager import evaluate_brand_fit
        result = await evaluate_brand_fit(deal_id, character, db)
        return {"status": "completed", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _action_adjust_strategy(character: Character, db, settings: SystemSettings) -> dict:
    """Adjust content strategy based on recent data."""
    try:
        from services.content_strategy import analyze_weekly_performance
        result = await analyze_weekly_performance()

        if result.get("content_mix"):
            settings.content_mix = json.dumps(result["content_mix"])
            db.commit()

        return {"status": "completed", "recommendations": result.get("recommendations", [])}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _action_engagement_loop(character: Character) -> dict:
    """Run engagement loop (like/comment niche posts)."""
    try:
        from services.ig_algorithm import execute_engagement_loop
        result = await execute_engagement_loop(character)
        return {"status": "completed", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _action_analyze_trends() -> dict:
    """Manually trigger trend analysis (TikTok + IG)."""
    try:
        from services.trend_analyzer import fetch_and_analyze_trends
        snapshot = await fetch_and_analyze_trends(niche="fitness")
        return {"status": "completed", "snapshot_id": snapshot.id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _action_generate_long_video(
    params: dict, character: Character, db, settings: SystemSettings,
) -> dict:
    """Generate a 65-second video ($5.18/video, budget-gated)."""
    from backend.models import GenerationLog

    # Budget gate
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_logs = (
        db.query(GenerationLog)
        .filter(GenerationLog.created_at >= today_start)
        .filter(GenerationLog.action == "generate")
        .all()
    )
    spent_today = 0.0
    for log in today_logs:
        try:
            details = json.loads(log.details or "{}")
            spent_today += details.get("cost_usd", 0.0)
        except (json.JSONDecodeError, TypeError):
            pass

    if spent_today + 5.18 > settings.daily_post_budget_usd:
        return {"status": "skipped", "reason": f"Budget exceeded (${spent_today:.2f}/${settings.daily_post_budget_usd:.2f})"}

    try:
        from services.viral_engine import generate_viral_reel_concept
        from services.long_video_pipeline import generate_long_video
        from services.trend_analyzer import get_trending_camera_angles

        category = params.get("category", "workout")
        concept = await generate_viral_reel_concept(character=character, category=category)
        camera_angles = await get_trending_camera_angles()
        trend_context = {
            "trending_formats": [{"camera_angle": a.get("camera_angle", "medium shot"), "format": a.get("format", "")} for a in camera_angles],
        }

        result = await generate_long_video(
            character=character,
            concept=concept,
            trend_context=trend_context,
        )

        db.add(GenerationLog(
            action="generate",
            entity_type="long_video",
            entity_id=0,
            status="success",
            details=f'{{"cost_usd": {result.total_cost_usd:.2f}, "clips": {len(result.clip_paths)}}}',
        ))
        db.commit()

        return {
            "status": "completed",
            "tiktok_video": result.tiktok_video_path,
            "ig_part1": result.ig_part1_path,
            "ig_part2": result.ig_part2_path,
            "cost_usd": result.total_cost_usd,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_active_character(db):
    """Get active character from database."""
    from services.character_manager import get_active_character
    return get_active_character(db)


async def get_agent_status() -> dict:
    """Get current agent status for admin dashboard."""
    agent_cfg = get_agent_config()
    db = SessionLocal()
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        decisions_today = (
            db.query(AgentDecision)
            .filter(AgentDecision.created_at >= today_start)
            .count()
        )

        last_decision = (
            db.query(AgentDecision)
            .order_by(AgentDecision.created_at.desc())
            .first()
        )

        recent_errors = (
            db.query(AgentDecision)
            .filter(AgentDecision.error.isnot(None))
            .filter(AgentDecision.created_at >= today_start)
            .count()
        )

        return {
            "decisions_today": decisions_today,
            "max_daily_decisions": agent_cfg.max_daily_decisions,
            "decisions_remaining": agent_cfg.max_daily_decisions - decisions_today,
            "last_decision_at": last_decision.created_at.isoformat() if last_decision else None,
            "last_action": last_decision.task_type if last_decision else None,
            "errors_today": recent_errors,
            "model": agent_cfg.orchestrator_model,
        }

    finally:
        db.close()
