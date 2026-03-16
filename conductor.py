#!/usr/bin/env python3
"""CONDUCTOR CLI — интерфейс для Claude Code на сервере.

Команды:
  submit   — создать задачу
  next     — получить следующую задачу
  complete — завершить задачу
  fail     — пометить задачу как проваленную
  decompose— разбить задачу на подзадачи
  list     — список задач
  log      — добавить запись в лог задачи
  status   — статус задачи
  dashboard— общая статистика
"""
import argparse
import json
import os
import sys
from datetime import datetime

# Добавить корень проекта в путь
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, select, func, desc
from sqlalchemy.orm import Session

from backend.models import ConductorTask, ConductorLog, TaskStatus, TaskPriority


def get_db_url() -> str:
    """Получить DATABASE_URL из .env или переменных окружения."""
    url = os.getenv("DATABASE_URL", "")
    if not url:
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not url:
        url = "sqlite:///conductor.db"
    return url


engine = create_engine(get_db_url())


def get_session() -> Session:
    return Session(engine)


# ─── Команды ────────────────────────────────────────────────────────────────


def cmd_submit(args):
    """Создать новую задачу."""
    with get_session() as db:
        task = ConductorTask(
            title=args.title,
            description=args.description or "",
            agent_role=args.role or "ceo_agent",
            priority=TaskPriority(args.priority) if args.priority else TaskPriority.NORMAL,
            created_by=args.created_by or "founder",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        log = ConductorLog(
            task_id=task.id,
            action="created",
            message=f"Задача создана: {task.title}",
        )
        db.add(log)
        db.commit()

        print(json.dumps({
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
            "agent_role": task.agent_role,
        }, ensure_ascii=False, indent=2))


def cmd_next(args):
    """Получить следующую задачу для выполнения."""
    priority_order = {
        TaskPriority.CRITICAL: 0,
        TaskPriority.HIGH: 1,
        TaskPriority.NORMAL: 2,
        TaskPriority.LOW: 3,
    }

    with get_session() as db:
        tasks = db.execute(
            select(ConductorTask)
            .where(ConductorTask.status == TaskStatus.PENDING)
            .order_by(ConductorTask.created_at)
        ).scalars().all()

        if not tasks:
            print(json.dumps({"message": "Нет задач в очереди"}, ensure_ascii=False))
            return

        # Сортировка по приоритету
        tasks.sort(key=lambda t: priority_order.get(t.priority, 99))
        task = tasks[0]

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()

        log = ConductorLog(
            task_id=task.id,
            action="picked_up",
            message="Задача взята в работу",
        )
        db.add(log)
        db.commit()
        db.refresh(task)

        result = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "agent_role": task.agent_role,
            "priority": task.priority.value,
            "context": task.context,
            "instructions": task.instructions,
            "parent_id": task.parent_id,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_complete(args):
    """Завершить задачу."""
    with get_session() as db:
        task = db.get(ConductorTask, args.task_id)
        if not task:
            print(json.dumps({"error": f"Задача {args.task_id} не найдена"}, ensure_ascii=False))
            return

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.result = args.result or ""

        log = ConductorLog(
            task_id=task.id,
            action="completed",
            message=args.result or "Задача завершена",
        )
        db.add(log)

        # Если все подзадачи родителя завершены — завершить родителя
        if task.parent_id:
            siblings = db.execute(
                select(ConductorTask)
                .where(ConductorTask.parent_id == task.parent_id)
            ).scalars().all()
            all_done = all(
                s.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
                for s in siblings
            )
            if all_done:
                parent = db.get(ConductorTask, task.parent_id)
                if parent and parent.status != TaskStatus.COMPLETED:
                    parent.status = TaskStatus.COMPLETED
                    parent.completed_at = datetime.utcnow()
                    parent.result = json.dumps(
                        {s.title: s.status.value for s in siblings},
                        ensure_ascii=False,
                    )
                    db.add(ConductorLog(
                        task_id=parent.id,
                        action="auto_completed",
                        message="Все подзадачи завершены",
                    ))

        db.commit()
        print(json.dumps({"id": task.id, "status": "completed"}, ensure_ascii=False))


def cmd_fail(args):
    """Пометить задачу как проваленную."""
    with get_session() as db:
        task = db.get(ConductorTask, args.task_id)
        if not task:
            print(json.dumps({"error": f"Задача {args.task_id} не найдена"}, ensure_ascii=False))
            return

        task.status = TaskStatus.FAILED
        task.error = args.error or "Неизвестная ошибка"

        log = ConductorLog(
            task_id=task.id,
            action="failed",
            message=args.error or "Задача провалена",
        )
        db.add(log)
        db.commit()
        print(json.dumps({"id": task.id, "status": "failed"}, ensure_ascii=False))


def cmd_decompose(args):
    """Разбить задачу на подзадачи."""
    with get_session() as db:
        task = db.get(ConductorTask, args.task_id)
        if not task:
            print(json.dumps({"error": f"Задача {args.task_id} не найдена"}, ensure_ascii=False))
            return

        subtasks_data = json.loads(args.subtasks)
        created = []

        for st in subtasks_data:
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

        result = {
            "parent_id": task.id,
            "subtasks": [{"id": s.id, "title": s.title, "role": s.agent_role} for s in created],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_list(args):
    """Список задач с фильтрами."""
    with get_session() as db:
        q = select(ConductorTask).order_by(desc(ConductorTask.created_at))

        if args.status:
            q = q.where(ConductorTask.status == TaskStatus(args.status))
        if args.role:
            q = q.where(ConductorTask.agent_role == args.role)
        if args.limit:
            q = q.limit(args.limit)

        tasks = db.execute(q).scalars().all()

        result = []
        for t in tasks:
            result.append({
                "id": t.id,
                "title": t.title[:80],
                "status": t.status.value,
                "priority": t.priority.value,
                "agent_role": t.agent_role,
                "parent_id": t.parent_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_log(args):
    """Добавить запись в лог задачи."""
    with get_session() as db:
        task = db.get(ConductorTask, args.task_id)
        if not task:
            print(json.dumps({"error": f"Задача {args.task_id} не найдена"}, ensure_ascii=False))
            return

        log = ConductorLog(
            task_id=task.id,
            action="progress_update",
            message=args.message,
        )
        db.add(log)
        db.commit()
        print(json.dumps({"id": log.id, "task_id": task.id, "action": "logged"}, ensure_ascii=False))


def cmd_status(args):
    """Статус задачи с логами."""
    with get_session() as db:
        task = db.get(ConductorTask, args.task_id)
        if not task:
            print(json.dumps({"error": f"Задача {args.task_id} не найдена"}, ensure_ascii=False))
            return

        logs = db.execute(
            select(ConductorLog)
            .where(ConductorLog.task_id == task.id)
            .order_by(ConductorLog.created_at)
        ).scalars().all()

        subtasks = db.execute(
            select(ConductorTask)
            .where(ConductorTask.parent_id == task.id)
        ).scalars().all()

        result = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "agent_role": task.agent_role,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "logs": [
                {"action": l.action, "message": l.message[:200], "at": l.created_at.isoformat()}
                for l in logs
            ],
            "subtasks": [
                {"id": s.id, "title": s.title[:80], "status": s.status.value}
                for s in subtasks
            ],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_dashboard(args):
    """Общая статистика."""
    with get_session() as db:
        counts = {}
        for status in TaskStatus:
            count = db.execute(
                select(func.count(ConductorTask.id))
                .where(ConductorTask.status == status)
            ).scalar()
            counts[status.value] = count

        total = sum(counts.values())
        recent = db.execute(
            select(ConductorTask)
            .order_by(desc(ConductorTask.created_at))
            .limit(5)
        ).scalars().all()

        result = {
            "total": total,
            "by_status": counts,
            "recent": [
                {"id": t.id, "title": t.title[:60], "status": t.status.value}
                for t in recent
            ],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_orchestrate(args):
    """Запустить полную оркестрацию задачи (CEO → директора → отделы → специалисты)."""
    import asyncio

    async def run():
        # Загрузить .env
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

        from services.conductor import get_conductor
        conductor = get_conductor()
        depth = args.depth if hasattr(args, "depth") and args.depth else 3
        tree = await conductor.orchestrate(args.task, depth=depth)

        if tree.get("status") == "error":
            print(json.dumps(tree, ensure_ascii=False, indent=2))
            return

        # Сохранить в БД
        with get_session() as db:
            parent = ConductorTask(
                title=args.task,
                description=tree.get("analysis", ""),
                level="conductor",
                assigned_to="conductor",
                priority=TaskPriority(args.priority) if args.priority else TaskPriority.NORMAL,
                status=TaskStatus.DECOMPOSED,
                created_by="founder",
            )
            db.add(parent)
            db.flush()

            total_tasks = 0
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
                    status=TaskStatus.DECOMPOSED,
                    created_by="conductor",
                )
                db.add(dir_task)
                db.flush()

                for dept in d.get("departments", []):
                    has_specs = bool(dept.get("specialists"))
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
                        status=TaskStatus.DECOMPOSED if has_specs else TaskStatus.PENDING,
                        created_by="conductor",
                    )
                    db.add(dept_task)
                    db.flush()

                    for spec in dept.get("specialists", []):
                        spec_task = ConductorTask(
                            parent_id=dept_task.id,
                            title=spec.get("task", ""),
                            level="specialist",
                            assigned_to=f"{d['role']}.{dept.get('department', '')}.{spec.get('specialist', '')}",
                            agent_role=d["role"],
                            estimated_hours=spec.get("estimated_hours", 0),
                            deliverables=json.dumps(spec.get("deliverables", []), ensure_ascii=False),
                            created_by="conductor",
                        )
                        db.add(spec_task)
                        total_tasks += 1

            db.add(ConductorLog(
                task_id=parent.id,
                action="orchestrated",
                message=f"Полная декомпозиция: {len(tree.get('directors', []))} директоров, {total_tasks} специалистов",
            ))
            db.commit()
            db.refresh(parent)

        tree["task_id"] = parent.id
        tree["total_specialists"] = total_tasks
        print(json.dumps(tree, ensure_ascii=False, indent=2))

    asyncio.run(run())


def cmd_tree(args):
    """Показать дерево задач в виде иерархии."""
    with get_session() as db:
        task = db.get(ConductorTask, args.task_id)
        if not task:
            print(json.dumps({"error": f"Задача {args.task_id} не найдена"}, ensure_ascii=False))
            return

        def print_tree(t, indent=0):
            prefix = "  " * indent
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌",
                "decomposed": "📋",
                "blocked": "🚫",
                "cancelled": "⛔",
            }.get(t.status.value, "?")

            level_tag = {
                "conductor": "CONDUCTOR",
                "director": "ДИРЕКТОР",
                "department": "ОТДЕЛ",
                "specialist": "СПЕЦ",
            }.get(t.level, t.level)

            line = f"{prefix}{status_icon} [{level_tag}] {t.title[:70]}"
            if t.assigned_to:
                line += f" ({t.assigned_to})"
            print(line)

            children = db.execute(
                select(ConductorTask)
                .where(ConductorTask.parent_id == t.id)
                .order_by(ConductorTask.created_at)
            ).scalars().all()

            for child in children:
                print_tree(child, indent + 1)

        print_tree(task)


# ─── CLI ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="CONDUCTOR CLI")
    sub = parser.add_subparsers(dest="command")

    # submit
    p_submit = sub.add_parser("submit", help="Создать задачу")
    p_submit.add_argument("title", help="Название задачи")
    p_submit.add_argument("--description", "-d", default="")
    p_submit.add_argument("--priority", "-p", choices=["critical", "high", "normal", "low"])
    p_submit.add_argument("--role", "-r", default="ceo_agent")
    p_submit.add_argument("--created-by", default="founder")

    # next
    sub.add_parser("next", help="Получить следующую задачу")

    # complete
    p_complete = sub.add_parser("complete", help="Завершить задачу")
    p_complete.add_argument("task_id", type=int)
    p_complete.add_argument("--result", "-r", default="")

    # fail
    p_fail = sub.add_parser("fail", help="Пометить задачу как проваленную")
    p_fail.add_argument("task_id", type=int)
    p_fail.add_argument("--error", "-e", default="")

    # decompose
    p_decompose = sub.add_parser("decompose", help="Разбить на подзадачи")
    p_decompose.add_argument("task_id", type=int)
    p_decompose.add_argument("--subtasks", "-s", required=True, help="JSON массив подзадач")

    # list
    p_list = sub.add_parser("list", help="Список задач")
    p_list.add_argument("--status", choices=[s.value for s in TaskStatus])
    p_list.add_argument("--role")
    p_list.add_argument("--limit", type=int, default=20)

    # log
    p_log = sub.add_parser("log", help="Добавить лог")
    p_log.add_argument("task_id", type=int)
    p_log.add_argument("message")

    # status
    p_status = sub.add_parser("status", help="Статус задачи")
    p_status.add_argument("task_id", type=int)

    # dashboard
    sub.add_parser("dashboard", help="Общая статистика")

    # orchestrate
    p_orchestrate = sub.add_parser("orchestrate", help="Полная оркестрация задачи")
    p_orchestrate.add_argument("task", help="Задача для декомпозиции")
    p_orchestrate.add_argument("--priority", "-p", choices=["critical", "high", "normal", "low"])
    p_orchestrate.add_argument("--depth", type=int, default=3, help="Глубина: 2=отделы, 3=специалисты")

    # tree
    p_tree = sub.add_parser("tree", help="Дерево задач")
    p_tree.add_argument("task_id", type=int)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "submit": cmd_submit,
        "next": cmd_next,
        "complete": cmd_complete,
        "fail": cmd_fail,
        "decompose": cmd_decompose,
        "list": cmd_list,
        "log": cmd_log,
        "status": cmd_status,
        "dashboard": cmd_dashboard,
        "orchestrate": cmd_orchestrate,
        "tree": cmd_tree,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
