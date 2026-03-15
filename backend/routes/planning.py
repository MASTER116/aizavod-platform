"""PLANNING API — планирование работ и загрузка агентов."""
from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, and_, or_, case
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.models import (
    WorkPlan, WorkPlanStatus, WorkPlanCategory,
    ConductorTask, TaskStatus, TaskPriority,
)

router = APIRouter(prefix="/api/planning", tags=["planning"])


# ─── Schemas ──────────────────────────────────────────────────────────────


class WorkPlanCreate(BaseModel):
    title: str
    description: str = ""
    category: str = "development"
    priority: str = "normal"
    assignee: str = "founder"
    planned_date: Optional[str] = None  # YYYY-MM-DD
    deadline: Optional[str] = None
    estimated_hours: float = 0.0
    notes: Optional[str] = None


class WorkPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    planned_date: Optional[str] = None
    deadline: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    progress: Optional[int] = None
    result: Optional[str] = None
    notes: Optional[str] = None


def _parse_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    return date.fromisoformat(val)


def _plan_to_dict(p: WorkPlan) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "category": p.category.value,
        "status": p.status.value,
        "priority": p.priority.value,
        "assignee": p.assignee,
        "planned_date": p.planned_date.isoformat() if p.planned_date else None,
        "deadline": p.deadline.isoformat() if p.deadline else None,
        "estimated_hours": p.estimated_hours,
        "actual_hours": p.actual_hours,
        "progress": p.progress,
        "result": p.result,
        "notes": p.notes,
        "conductor_task_id": p.conductor_task_id,
        "started_at": p.started_at.isoformat() if p.started_at else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


# ─── CRUD ─────────────────────────────────────────────────────────────────


@router.post("/plans")
async def create_plan(req: WorkPlanCreate, db: Session = Depends(get_db)):
    """Создать план/задачу."""
    plan = WorkPlan(
        title=req.title,
        description=req.description,
        category=WorkPlanCategory(req.category),
        priority=TaskPriority(req.priority),
        assignee=req.assignee,
        planned_date=_parse_date(req.planned_date),
        deadline=_parse_date(req.deadline),
        estimated_hours=req.estimated_hours,
        notes=req.notes,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_to_dict(plan)


@router.get("/plans")
async def list_plans(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Список планов с фильтрацией."""
    q = select(WorkPlan).order_by(
        case(
            (WorkPlan.priority == TaskPriority.CRITICAL, 0),
            (WorkPlan.priority == TaskPriority.HIGH, 1),
            (WorkPlan.priority == TaskPriority.NORMAL, 2),
            (WorkPlan.priority == TaskPriority.LOW, 3),
        ),
        WorkPlan.planned_date.asc().nulls_last(),
    )
    if status:
        q = q.where(WorkPlan.status == WorkPlanStatus(status))
    if assignee:
        q = q.where(WorkPlan.assignee == assignee)
    if category:
        q = q.where(WorkPlan.category == WorkPlanCategory(category))
    if date_from:
        q = q.where(WorkPlan.planned_date >= date.fromisoformat(date_from))
    if date_to:
        q = q.where(WorkPlan.planned_date <= date.fromisoformat(date_to))
    q = q.limit(limit)

    plans = db.execute(q).scalars().all()
    return [_plan_to_dict(p) for p in plans]


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Детали плана."""
    plan = db.get(WorkPlan, plan_id)
    if not plan:
        return {"error": "not found"}
    return _plan_to_dict(plan)


@router.patch("/plans/{plan_id}")
async def update_plan(plan_id: int, req: WorkPlanUpdate, db: Session = Depends(get_db)):
    """Обновить план."""
    plan = db.get(WorkPlan, plan_id)
    if not plan:
        return {"error": "not found"}

    if req.title is not None:
        plan.title = req.title
    if req.description is not None:
        plan.description = req.description
    if req.category is not None:
        plan.category = WorkPlanCategory(req.category)
    if req.status is not None:
        plan.status = WorkPlanStatus(req.status)
        if req.status == "in_progress" and not plan.started_at:
            plan.started_at = datetime.utcnow()
        elif req.status == "done":
            plan.completed_at = datetime.utcnow()
            plan.progress = 100
    if req.priority is not None:
        plan.priority = TaskPriority(req.priority)
    if req.assignee is not None:
        plan.assignee = req.assignee
    if req.planned_date is not None:
        plan.planned_date = _parse_date(req.planned_date)
    if req.deadline is not None:
        plan.deadline = _parse_date(req.deadline)
    if req.estimated_hours is not None:
        plan.estimated_hours = req.estimated_hours
    if req.actual_hours is not None:
        plan.actual_hours = req.actual_hours
    if req.progress is not None:
        plan.progress = req.progress
    if req.result is not None:
        plan.result = req.result
    if req.notes is not None:
        plan.notes = req.notes

    db.commit()
    db.refresh(plan)
    return _plan_to_dict(plan)


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    """Удалить план."""
    plan = db.get(WorkPlan, plan_id)
    if not plan:
        return {"error": "not found"}
    db.delete(plan)
    db.commit()
    return {"ok": True}


# ─── Workload Dashboard ──────────────────────────────────────────────────


@router.get("/workload")
async def workload_dashboard(db: Session = Depends(get_db)):
    """Общая загрузка: сводка по агентам и основателю."""

    # --- WorkPlan stats по assignee ---
    active_statuses = [
        WorkPlanStatus.TODO,
        WorkPlanStatus.IN_PROGRESS,
        WorkPlanStatus.REVIEW,
    ]
    plan_stats = db.execute(
        select(
            WorkPlan.assignee,
            func.count(WorkPlan.id).label("total_tasks"),
            func.sum(WorkPlan.estimated_hours).label("estimated_hours"),
            func.sum(WorkPlan.actual_hours).label("actual_hours"),
            func.avg(WorkPlan.progress).label("avg_progress"),
        )
        .where(WorkPlan.status.in_(active_statuses))
        .group_by(WorkPlan.assignee)
    ).all()

    # --- ConductorTask stats по agent_role (активные) ---
    active_task_statuses = [
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.DECOMPOSED,
    ]
    conductor_stats = db.execute(
        select(
            ConductorTask.agent_role,
            func.count(ConductorTask.id).label("total"),
            func.sum(ConductorTask.estimated_hours).label("est_hours"),
        )
        .where(ConductorTask.status.in_(active_task_statuses))
        .group_by(ConductorTask.agent_role)
    ).all()

    # Объединяем в единую картину
    agents = {}

    for row in plan_stats:
        name = row.assignee or "unassigned"
        agents[name] = {
            "assignee": name,
            "work_plans": row.total_tasks or 0,
            "estimated_hours": round(row.estimated_hours or 0, 1),
            "actual_hours": round(row.actual_hours or 0, 1),
            "avg_progress": round(row.avg_progress or 0),
            "conductor_tasks": 0,
            "conductor_est_hours": 0,
        }

    for row in conductor_stats:
        name = row.agent_role or "unassigned"
        if name not in agents:
            agents[name] = {
                "assignee": name,
                "work_plans": 0,
                "estimated_hours": 0,
                "actual_hours": 0,
                "avg_progress": 0,
                "conductor_tasks": 0,
                "conductor_est_hours": 0,
            }
        agents[name]["conductor_tasks"] = row.total or 0
        agents[name]["conductor_est_hours"] = round(row.est_hours or 0, 1)

    # --- Общие counters ---
    total_plans = db.execute(select(func.count(WorkPlan.id))).scalar()
    done_plans = db.execute(
        select(func.count(WorkPlan.id))
        .where(WorkPlan.status == WorkPlanStatus.DONE)
    ).scalar()
    overdue = db.execute(
        select(func.count(WorkPlan.id))
        .where(
            and_(
                WorkPlan.deadline < date.today(),
                WorkPlan.status.not_in([WorkPlanStatus.DONE, WorkPlanStatus.CANCELLED]),
            )
        )
    ).scalar()

    return {
        "agents": list(agents.values()),
        "summary": {
            "total_plans": total_plans or 0,
            "done_plans": done_plans or 0,
            "overdue": overdue or 0,
            "completion_rate": round((done_plans / total_plans * 100) if total_plans else 0),
        },
    }


@router.get("/timeline")
async def timeline(
    days: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Временная шкала планов на N дней вперёд."""
    today = date.today()
    end = today + timedelta(days=days)

    plans = db.execute(
        select(WorkPlan)
        .where(
            and_(
                WorkPlan.planned_date >= today,
                WorkPlan.planned_date <= end,
                WorkPlan.status.not_in([WorkPlanStatus.DONE, WorkPlanStatus.CANCELLED]),
            )
        )
        .order_by(WorkPlan.planned_date, WorkPlan.priority)
    ).scalars().all()

    # Группировка по дате
    timeline_data: dict[str, list] = {}
    for p in plans:
        key = p.planned_date.isoformat()
        if key not in timeline_data:
            timeline_data[key] = []
        timeline_data[key].append(_plan_to_dict(p))

    return {
        "from": today.isoformat(),
        "to": end.isoformat(),
        "days": timeline_data,
    }


@router.get("/my-day")
async def my_day(db: Session = Depends(get_db)):
    """Задачи основателя на сегодня + просроченные."""
    today = date.today()

    # Задачи на сегодня
    today_plans = db.execute(
        select(WorkPlan)
        .where(
            and_(
                WorkPlan.assignee == "founder",
                WorkPlan.planned_date == today,
                WorkPlan.status.not_in([WorkPlanStatus.DONE, WorkPlanStatus.CANCELLED]),
            )
        )
        .order_by(WorkPlan.priority)
    ).scalars().all()

    # Просроченные
    overdue_plans = db.execute(
        select(WorkPlan)
        .where(
            and_(
                WorkPlan.assignee == "founder",
                WorkPlan.deadline < today,
                WorkPlan.status.not_in([WorkPlanStatus.DONE, WorkPlanStatus.CANCELLED]),
            )
        )
        .order_by(WorkPlan.priority)
    ).scalars().all()

    # В работе (без даты, но in_progress)
    in_progress = db.execute(
        select(WorkPlan)
        .where(
            and_(
                WorkPlan.assignee == "founder",
                WorkPlan.status == WorkPlanStatus.IN_PROGRESS,
            )
        )
    ).scalars().all()

    # Суммарная загрузка на сегодня
    total_est = sum(p.estimated_hours for p in today_plans)
    total_actual = sum(p.actual_hours for p in today_plans)

    return {
        "date": today.isoformat(),
        "today": [_plan_to_dict(p) for p in today_plans],
        "overdue": [_plan_to_dict(p) for p in overdue_plans],
        "in_progress": [_plan_to_dict(p) for p in in_progress],
        "workload": {
            "planned_hours": round(total_est, 1),
            "actual_hours": round(total_actual, 1),
            "tasks_count": len(today_plans),
        },
    }
