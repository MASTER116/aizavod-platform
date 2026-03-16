"""CONDUCTOR API — маршрутизация запросов + управление задачами."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.models import (
    ConductorTask, ConductorLog, TaskStatus, TaskPriority,
)

router = APIRouter(prefix="/api/conductor", tags=["conductor"])


class ConductorRequest(BaseModel):
    query: str


class ConductorResponse(BaseModel):
    query: str
    agent: str
    department: str
    confidence: float
    reasoning: str
    response: str
    duration_ms: float
    secondary_responses: dict[str, str] = {}


@router.post("/route", response_model=ConductorResponse)
async def route_query(req: ConductorRequest):
    """Принять запрос на естественном языке и маршрутизировать к агенту."""
    from services.conductor import get_conductor

    conductor = get_conductor()
    result = await conductor.process(req.query)

    return ConductorResponse(
        query=result.query,
        agent=result.agent_name,
        department=result.department,
        confidence=result.route.confidence,
        reasoning=result.route.reasoning,
        response=result.response,
        duration_ms=result.duration_ms,
        secondary_responses=result.secondary_responses,
    )


class OrchestrateRequest(BaseModel):
    task: str
    priority: str = "normal"
    depth: int = 3  # 2 = до отделов, 3 = до специалистов


@router.post("/orchestrate")
async def orchestrate_task(req: OrchestrateRequest, db: Session = Depends(get_db)):
    """Полная оркестрация: CEO → директора → отделы → специалисты."""
    from services.conductor import get_conductor

    conductor = get_conductor()
    tree = await conductor.orchestrate(req.task, depth=req.depth)

    if tree.get("status") == "error":
        return tree

    # Сохранить в БД: parent task + director tasks + department tasks + specialist tasks
    parent = ConductorTask(
        title=req.task,
        description=tree.get("analysis", ""),
        level="conductor",
        assigned_to="conductor",
        priority=TaskPriority(req.priority),
        status=TaskStatus.DECOMPOSED,
        created_by="founder",
    )
    db.add(parent)
    db.flush()

    total_specialists = 0

    for d in tree.get("directors", []):
        dir_task = ConductorTask(
            parent_id=parent.id,
            title=d["task"],
            level="director",
            assigned_to=d["role"],
            agent_role=d["role"],
            priority=TaskPriority(d.get("priority", "normal")),
            estimated_hours=d.get("estimated_hours", 0),
            deliverables=json.dumps(d.get("deliverables", []), ensure_ascii=False),
            dependencies=json.dumps(d.get("depends_on", []), ensure_ascii=False),
            status=TaskStatus.DECOMPOSED if d.get("departments") else TaskStatus.PENDING,
            created_by="conductor",
        )
        db.add(dir_task)
        db.flush()

        for dept in d.get("departments", []):
            has_specialists = bool(dept.get("specialists"))
            dept_task = ConductorTask(
                parent_id=dir_task.id,
                title=dept.get("task", ""),
                level="department",
                assigned_to=f"{d['role']}.{dept.get('department', '')}",
                agent_role=d["role"],
                priority=TaskPriority(d.get("priority", "normal")),
                estimated_hours=dept.get("estimated_hours", 0),
                deliverables=json.dumps(dept.get("deliverables", []), ensure_ascii=False),
                dependencies=json.dumps(dept.get("depends_on", []), ensure_ascii=False),
                status=TaskStatus.DECOMPOSED if has_specialists else TaskStatus.PENDING,
                created_by="conductor",
            )
            db.add(dept_task)
            db.flush()

            # 3-й уровень: специалисты
            for spec in dept.get("specialists", []):
                spec_task = ConductorTask(
                    parent_id=dept_task.id,
                    title=spec.get("task", ""),
                    level="specialist",
                    assigned_to=f"{d['role']}.{dept.get('department', '')}.{spec.get('specialist', '')}",
                    agent_role=d["role"],
                    priority=TaskPriority(d.get("priority", "normal")),
                    estimated_hours=spec.get("estimated_hours", 0),
                    deliverables=json.dumps(spec.get("deliverables", []), ensure_ascii=False),
                    dependencies=json.dumps(spec.get("depends_on", []), ensure_ascii=False),
                    created_by="conductor",
                )
                db.add(spec_task)
                total_specialists += 1

    db.add(ConductorLog(
        task_id=parent.id,
        action="orchestrated",
        message=f"Декомпозиция: {len(tree.get('directors', []))} директоров, {total_specialists} специалистов",
    ))
    db.commit()
    db.refresh(parent)

    tree["task_id"] = parent.id
    tree["total_specialists"] = total_specialists
    return tree


@router.post("/tasks/{task_id}/collect")
async def collect_results(task_id: int, db: Session = Depends(get_db)):
    """Собрать результаты по дереву задач."""
    task = db.get(ConductorTask, task_id)
    if not task:
        return {"error": "not found"}

    def collect_tree(t):
        children = db.execute(
            select(ConductorTask).where(ConductorTask.parent_id == t.id)
        ).scalars().all()
        node = {
            "id": t.id,
            "title": t.title,
            "level": t.level,
            "assigned_to": t.assigned_to,
            "status": t.status.value,
            "result": t.result,
        }
        if children:
            node["children"] = [collect_tree(c) for c in children]
        return node

    tree = collect_tree(task)

    # Посчитать статистику
    def count_statuses(node):
        counts = {"total": 0, "completed": 0, "pending": 0, "failed": 0, "in_progress": 0}
        if not node.get("children"):
            counts["total"] = 1
            s = node.get("status", "pending")
            counts[s] = counts.get(s, 0) + 1
            return counts
        for child in node.get("children", []):
            child_counts = count_statuses(child)
            for k, v in child_counts.items():
                counts[k] = counts.get(k, 0) + v
        return counts

    stats = count_statuses(tree)

    return {
        "task_id": task_id,
        "tree": tree,
        "stats": stats,
    }


@router.get("/tree/{task_id}")
async def get_task_tree(task_id: int, db: Session = Depends(get_db)):
    """Дерево задач с подзадачами."""
    task = db.get(ConductorTask, task_id)
    if not task:
        return {"error": "not found"}

    def build_node(t):
        children = db.execute(
            select(ConductorTask).where(ConductorTask.parent_id == t.id)
        ).scalars().all()
        node = {
            "id": t.id,
            "title": t.title,
            "level": t.level,
            "assigned_to": t.assigned_to,
            "status": t.status.value,
            "priority": t.priority.value,
            "estimated_hours": t.estimated_hours,
        }
        if children:
            node["children"] = [build_node(c) for c in children]
        return node

    return build_node(task)


@router.get("/agents")
async def list_agents():
    """Список доступных агентов."""
    from services.conductor import AGENTS

    return [
        {
            "name": a.name,
            "title": a.title,
            "department": a.department,
            "description": a.description,
        }
        for a in AGENTS
    ]


# ─── Task Management ──────────────────────────────────────────────────────


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    agent_role: str = "ceo_agent"
    priority: str = "normal"
    context: str = "{}"
    instructions: Optional[str] = None


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


class DecomposeRequest(BaseModel):
    subtasks: list[dict]


@router.post("/tasks")
async def create_task(req: TaskCreate, db: Session = Depends(get_db)):
    """Создать задачу."""
    task = ConductorTask(
        title=req.title,
        description=req.description,
        agent_role=req.agent_role,
        priority=TaskPriority(req.priority),
        context=req.context,
        instructions=req.instructions,
        created_by="founder",
    )
    db.add(task)
    db.flush()
    db.add(ConductorLog(task_id=task.id, action="created", message=req.title))
    db.commit()
    db.refresh(task)
    return {"id": task.id, "title": task.title, "status": task.status.value}


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Список задач."""
    q = select(ConductorTask).order_by(desc(ConductorTask.created_at))
    if status:
        q = q.where(ConductorTask.status == TaskStatus(status))
    if role:
        q = q.where(ConductorTask.agent_role == role)
    q = q.limit(limit)
    tasks = db.execute(q).scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "priority": t.priority.value,
            "agent_role": t.agent_role,
            "parent_id": t.parent_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """Детали задачи + подзадачи + логи."""
    task = db.get(ConductorTask, task_id)
    if not task:
        return {"error": "not found"}

    logs = db.execute(
        select(ConductorLog).where(ConductorLog.task_id == task.id)
        .order_by(ConductorLog.created_at)
    ).scalars().all()

    subtasks = db.execute(
        select(ConductorTask).where(ConductorTask.parent_id == task.id)
    ).scalars().all()

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "agent_role": task.agent_role,
        "result": task.result,
        "error": task.error,
        "context": task.context,
        "instructions": task.instructions,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "logs": [
            {"action": l.action, "message": l.message, "at": l.created_at.isoformat()}
            for l in logs
        ],
        "subtasks": [
            {"id": s.id, "title": s.title, "status": s.status.value, "role": s.agent_role}
            for s in subtasks
        ],
    }


@router.patch("/tasks/{task_id}")
async def update_task(task_id: int, req: TaskUpdate, db: Session = Depends(get_db)):
    """Обновить статус задачи."""
    task = db.get(ConductorTask, task_id)
    if not task:
        return {"error": "not found"}

    if req.status:
        task.status = TaskStatus(req.status)
        if req.status == "in_progress" and not task.started_at:
            task.started_at = datetime.utcnow()
        elif req.status == "completed":
            task.completed_at = datetime.utcnow()
    if req.result is not None:
        task.result = req.result
    if req.error is not None:
        task.error = req.error

    db.add(ConductorLog(
        task_id=task.id,
        action=f"status_changed:{req.status}" if req.status else "updated",
        message=req.result or req.error or "",
    ))
    db.commit()
    return {"id": task.id, "status": task.status.value}


@router.post("/tasks/{task_id}/decompose")
async def decompose_task(task_id: int, req: DecomposeRequest, db: Session = Depends(get_db)):
    """Разбить задачу на подзадачи."""
    task = db.get(ConductorTask, task_id)
    if not task:
        return {"error": "not found"}

    created = []
    for st in req.subtasks:
        sub = ConductorTask(
            parent_id=task.id,
            title=st.get("title", ""),
            description=st.get("description", ""),
            agent_role=st.get("role", task.agent_role),
            priority=task.priority,
            created_by="conductor",
        )
        db.add(sub)
        created.append(sub)

    task.status = TaskStatus.DECOMPOSED
    db.add(ConductorLog(
        task_id=task.id,
        action="decomposed",
        message=f"Разбита на {len(created)} подзадач",
    ))
    db.commit()
    for s in created:
        db.refresh(s)

    return {
        "parent_id": task.id,
        "subtasks": [{"id": s.id, "title": s.title, "role": s.agent_role} for s in created],
    }


@router.get("/dashboard")
async def dashboard(db: Session = Depends(get_db)):
    """Общая статистика задач."""
    counts = {}
    for status in TaskStatus:
        count = db.execute(
            select(func.count(ConductorTask.id))
            .where(ConductorTask.status == status)
        ).scalar()
        counts[status.value] = count

    recent = db.execute(
        select(ConductorTask).order_by(desc(ConductorTask.created_at)).limit(5)
    ).scalars().all()

    return {
        "total": sum(counts.values()),
        "by_status": counts,
        "recent": [
            {"id": t.id, "title": t.title, "status": t.status.value, "role": t.agent_role}
            for t in recent
        ],
    }
