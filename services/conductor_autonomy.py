"""CONDUCTOR Autonomy — автономный режим мета-оркестратора.

Три функции:
1. Auto-execute: берёт pending задачи из БД и выполняет через агентов
2. DARWIN-цикл: оценивает качество каждого ответа, логирует, ищет паттерны
3. Scheduled tasks: автономные задачи по расписанию (фриланс, мониторинг, отчёты)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("aizavod.conductor.autonomy")


# ─── 1. Auto-execute pending tasks ──────────────────────────────────────────

async def auto_execute_cycle():
    """Взять следующую pending задачу из БД и выполнить через CONDUCTOR."""
    from backend.database import SessionLocal
    from backend.models import ConductorTask, ConductorLog, TaskStatus
    from services.conductor import get_conductor, AGENTS

    db = SessionLocal()
    try:
        # Найти задачу уровня department или specialist в статусе pending
        task = (
            db.query(ConductorTask)
            .filter(ConductorTask.status == TaskStatus.PENDING)
            .filter(ConductorTask.level.in_(["department", "specialist"]))
            .order_by(
                ConductorTask.priority.asc(),  # critical < high < normal < low
                ConductorTask.created_at.asc(),
            )
            .first()
        )

        if not task:
            return  # Нет задач

        logger.info("AUTO-EXECUTE: берём задачу #%d: %s", task.id, task.title[:80])

        # Пометить как in_progress
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        db.add(ConductorLog(
            task_id=task.id,
            action="auto_started",
            message="Автономное выполнение",
        ))
        db.commit()

        # Выполнить: hackathon_manager задачи — через pipeline, остальные — через роутер
        conductor = get_conductor()
        try:
            agent_name = task.agent_role
            if task.agent_role == "hackathon_manager":
                from services.hackathon_pipeline import execute_pipeline_stage
                response_text = await execute_pipeline_stage(
                    task.title, task.context or "{}", task.instructions or ""
                )
                response_text = response_text[:4000]
            else:
                result = await conductor.process(task.title)
                response_text = result.response[:4000]
                agent_name = result.agent_name

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = response_text
            db.add(ConductorLog(
                task_id=task.id,
                action="auto_completed",
                message=response_text[:500],
            ))

            # DARWIN: оценить качество ответа
            await _darwin_evaluate(task.title, agent_name, response_text, db, task.id)

            logger.info("AUTO-EXECUTE: задача #%d завершена (%s)", task.id, agent_name)

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)[:2000]
            db.add(ConductorLog(
                task_id=task.id,
                action="auto_failed",
                message=str(e)[:500],
            ))
            logger.error("AUTO-EXECUTE: ошибка задачи #%d: %s", task.id, e)

        db.commit()

        # Проверить: все подзадачи родителя завершены?
        if task.parent_id:
            _check_parent_completion(db, task.parent_id)
            db.commit()

    finally:
        db.close()


def _check_parent_completion(db, parent_id: int):
    """Если все подзадачи завершены — завершить родителя."""
    from backend.models import ConductorTask, ConductorLog, TaskStatus

    parent = db.get(ConductorTask, parent_id)
    if not parent or parent.status == TaskStatus.COMPLETED:
        return

    siblings = (
        db.query(ConductorTask)
        .filter(ConductorTask.parent_id == parent_id)
        .all()
    )
    if not siblings:
        return

    all_done = all(
        s.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        for s in siblings
    )

    if all_done:
        parent.status = TaskStatus.COMPLETED
        parent.completed_at = datetime.utcnow()
        parent.result = json.dumps(
            {s.title[:60]: s.status.value for s in siblings},
            ensure_ascii=False,
        )
        db.add(ConductorLog(
            task_id=parent.id,
            action="auto_completed",
            message=f"Все {len(siblings)} подзадач завершены",
        ))
        logger.info("AUTO-COMPLETE: родитель #%d завершён", parent.id)

        # Рекурсивно вверх
        if parent.parent_id:
            _check_parent_completion(db, parent.parent_id)


# ─── 2. DARWIN Quality Cycle ────────────────────────────────────────────────

async def _darwin_evaluate(query: str, agent_name: str, response: str, db, task_id: int):
    """Оценить качество ответа через DARWIN и сохранить в лог."""
    from backend.models import ConductorLog

    try:
        from services.darwin_agent import get_darwin_agent
        darwin = get_darwin_agent()
        evaluation = await darwin.analyze_response(agent_name, query, response)

        # Извлечь числовой балл из ответа
        score = _extract_score(evaluation)

        db.add(ConductorLog(
            task_id=task_id,
            action="darwin_evaluation",
            message=evaluation[:1000],
            metadata_json=json.dumps({
                "agent": agent_name,
                "score": score,
            }),
        ))

        if score < 5.0:
            logger.warning(
                "DARWIN: низкое качество (%.1f/10) от %s для '%s'",
                score, agent_name, query[:60],
            )

    except Exception as e:
        logger.error("DARWIN evaluation error: %s", e)


def _extract_score(evaluation: str) -> float:
    """Извлечь числовой балл из текста оценки DARWIN."""
    import re
    # Ищем "ИТОГО: X/10" или "средний балл: X" или просто X/10
    patterns = [
        r"итого[:\s]+(\d+(?:\.\d+)?)\s*/\s*10",
        r"средни[йя]\s*балл[:\s]+(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*/\s*10",
    ]
    for p in patterns:
        m = re.search(p, evaluation.lower())
        if m:
            return float(m.group(1))
    return 7.0  # дефолт если не нашли


async def darwin_weekly_report():
    """Еженедельный отчёт DARWIN: анализ всех ответов за неделю."""
    from backend.database import SessionLocal
    from backend.models import ConductorLog

    db = SessionLocal()
    try:
        week_ago = datetime.utcnow() - timedelta(days=7)
        evaluations = (
            db.query(ConductorLog)
            .filter(ConductorLog.action == "darwin_evaluation")
            .filter(ConductorLog.created_at >= week_ago)
            .all()
        )

        if not evaluations:
            return "Нет данных для отчёта"

        # Собрать статистику по агентам
        agent_scores: dict[str, list[float]] = {}
        for ev in evaluations:
            try:
                meta = json.loads(ev.metadata_json)
                agent = meta.get("agent", "unknown")
                score = meta.get("score", 0)
                agent_scores.setdefault(agent, []).append(score)
            except (json.JSONDecodeError, KeyError):
                pass

        stats_lines = []
        for agent, scores in sorted(agent_scores.items()):
            avg = sum(scores) / len(scores) if scores else 0
            stats_lines.append(
                f"- {agent}: {avg:.1f}/10 ({len(scores)} ответов, "
                f"min={min(scores):.1f}, max={max(scores):.1f})"
            )

        stats_text = "\n".join(stats_lines) or "Нет данных"

        from services.darwin_agent import get_darwin_agent
        darwin = get_darwin_agent()
        report = await darwin.weekly_report(
            f"Период: {week_ago.date()} — {datetime.utcnow().date()}\n"
            f"Всего оценок: {len(evaluations)}\n\n"
            f"По агентам:\n{stats_text}"
        )
        return report

    finally:
        db.close()


# ─── 3. Scheduled Autonomous Tasks ─────────────────────────────────────────

async def scheduled_freelance_scan():
    """Автономный поиск заказов на фрилансе."""
    from services.conductor import get_conductor

    conductor = get_conductor()
    result = await conductor.process("Найди новые заказы на Kwork по нашим услугам")
    logger.info("AUTONOMOUS: freelance scan done, %d chars", len(result.response))


async def scheduled_opportunity_scan():
    """Автономный поиск грантов и конкурсов."""
    from services.conductor import get_conductor

    conductor = get_conductor()
    result = await conductor.process("Найди новые гранты и хакатоны для AI-стартапа")
    logger.info("AUTONOMOUS: opportunity scan done, %d chars", len(result.response))


async def scheduled_health_check():
    """Проверка здоровья системы."""
    import os

    checks = []

    # API key
    if os.getenv("ANTHROPIC_API_KEY"):
        checks.append("Anthropic API: OK")
    else:
        checks.append("Anthropic API: MISSING")

    # БД
    try:
        from backend.database import SessionLocal
        from backend.models import ConductorTask
        db = SessionLocal()
        count = db.query(ConductorTask).count()
        db.close()
        checks.append(f"DB: OK ({count} tasks)")
    except Exception as e:
        checks.append(f"DB: ERROR ({e})")

    logger.info("HEALTH CHECK: %s", " | ".join(checks))


# ─── Регистрация в scheduler ────────────────────────────────────────────────

def register_autonomy_jobs(scheduler) -> None:
    """Зарегистрировать автономные задачи в APScheduler."""

    # Auto-execute pending tasks (every 10 min)
    scheduler.add_job(
        auto_execute_cycle,
        "interval",
        minutes=10,
        id="conductor_auto_execute",
        replace_existing=True,
    )

    # DARWIN weekly report (Sunday 21:00)
    scheduler.add_job(
        darwin_weekly_report,
        "cron",
        day_of_week="sun",
        hour=21,
        id="darwin_weekly_report",
        replace_existing=True,
    )

    # Freelance scan (3x/day: 9:00, 14:00, 18:00)
    for hour in [9, 14, 18]:
        scheduler.add_job(
            scheduled_freelance_scan,
            "cron",
            hour=hour,
            minute=10,
            id=f"freelance_scan_{hour}",
            replace_existing=True,
        )

    # Opportunity scan (daily 10:30)
    scheduler.add_job(
        scheduled_opportunity_scan,
        "cron",
        hour=10,
        minute=30,
        id="opportunity_scan",
        replace_existing=True,
    )

    # Health check (every 1 hour)
    scheduler.add_job(
        scheduled_health_check,
        "interval",
        hours=1,
        id="conductor_health_check",
        replace_existing=True,
    )

    logger.info("AUTONOMY: зарегистрировано 7 автономных задач")
