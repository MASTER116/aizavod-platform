"""Hackathon Pipeline — полный конвейер участия в хакатонах.

Этапы:
1. DISCOVERY  — поиск хакатонов на DevPost (AI/ML, с призами)
2. ANALYSIS   — глубокий анализ правил, критериев, дедлайнов
3. IDEATION   — генерация идеи проекта под конкретный хакатон
4. PLANNING   — план работ, архитектура, стек
5. DOCUMENTS  — регистрация, README, описание проекта
6. DEVELOPMENT — создание MVP (таск-трекер)
7. SUBMISSION — финальная сборка и подача на сайте хакатона

CONDUCTOR ставит задачу → pipeline декомпозирует на этапы →
каждый этап создаёт подзадачи в БД → auto_execute_cycle выполняет.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime

logger = logging.getLogger("aizavod.hackathon_pipeline")

PIPELINE_STAGES = [
    "discovery",
    "analysis",
    "ideation",
    "planning",
    "documents",
    "development",
    "submission",
]


async def launch_hackathon_pipeline(
    query: str = "",
    min_prize: int = 0,
    max_hackathons: int = 5,
) -> str:
    """Запуск полного конвейера: поиск → анализ → план → подача.

    Создаёт иерархию задач в БД и возвращает сводку.
    """
    from backend.database import SessionLocal
    from backend.models import ConductorTask, ConductorLog, TaskStatus, TaskPriority

    # ── 1. Поиск хакатонов ──
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    hackathons = await scanner._fetch_devpost_hackathons()

    if not hackathons:
        return "Не найдено открытых хакатонов на DevPost."

    # Фильтрация: только с призами > min_prize, релевантные AI/ML/IT
    relevant = []
    for h in hackathons:
        desc = f"{h.title} {h.description}".lower()
        # Пропускаем если менее 1 дня до дедлайна
        if "hour" in (h.deadline or "") and "about" in (h.deadline or ""):
            # "about X hours left" — если < 24 часов, рискованно
            pass  # всё равно добавляем, пользователь решит
        # Фильтр по призу
        prize_val = _parse_prize(h.prize)
        if min_prize and prize_val < min_prize:
            continue
        relevant.append({
            "title": h.title,
            "url": h.url,
            "prize": h.prize,
            "prize_value": prize_val,
            "deadline": h.deadline,
            "description": h.description,
        })

    # Сортируем по призу (больше → выше)
    relevant.sort(key=lambda x: x["prize_value"], reverse=True)
    selected = relevant[:max_hackathons]

    if not selected:
        return "Нет подходящих хакатонов с указанными фильтрами."

    # ── 2. Создаём корневую задачу ──
    db = SessionLocal()
    try:
        root_task = ConductorTask(
            title=f"Hackathon Pipeline: подать заявки на {len(selected)} хакатонов",
            description=query or "Автоматический конвейер участия в хакатонах",
            agent_role="hackathon_manager",
            level="conductor",
            status=TaskStatus.DECOMPOSED,
            priority=TaskPriority.HIGH,
            context=json.dumps({"hackathons": selected}, ensure_ascii=False),
            created_by="founder",
        )
        db.add(root_task)
        db.flush()

        db.add(ConductorLog(
            task_id=root_task.id,
            action="pipeline_created",
            message=f"Конвейер запущен: {len(selected)} хакатонов",
        ))

        # ── 3. Для каждого хакатона — создаём ветку задач ──
        summary_lines = [
            f"🚀 **Hackathon Pipeline запущен**\n",
            f"Найдено хакатонов: {len(hackathons)}",
            f"Отобрано для участия: {len(selected)}\n",
        ]

        for i, hack in enumerate(selected, 1):
            summary_lines.append(
                f"**{i}. {hack['title']}**\n"
                f"   Приз: {hack['prize'] or 'N/A'} | {hack['deadline']}\n"
                f"   {hack['url']}\n"
            )

            # Создаём задачу-группу для хакатона
            hack_task = ConductorTask(
                parent_id=root_task.id,
                title=f"Хакатон: {hack['title'][:200]}",
                description=f"Приз: {hack['prize']} | Дедлайн: {hack['deadline']}",
                agent_role="hackathon_manager",
                level="director",
                status=TaskStatus.DECOMPOSED,
                priority=TaskPriority.HIGH,
                context=json.dumps(hack, ensure_ascii=False),
                created_by="conductor",
            )
            db.add(hack_task)
            db.flush()

            # Создаём подзадачи для каждого этапа
            prev_task_id = None
            for stage_idx, stage in enumerate(PIPELINE_STAGES):
                stage_info = _stage_config(stage, hack)
                subtask = ConductorTask(
                    parent_id=hack_task.id,
                    title=stage_info["title"],
                    description=stage_info["description"],
                    agent_role=stage_info["agent"],
                    level="department",
                    status=TaskStatus.PENDING,
                    priority=TaskPriority.HIGH,
                    execution_order="sequential",
                    dependencies=json.dumps(
                        [prev_task_id] if prev_task_id else []
                    ),
                    estimated_hours=stage_info["hours"],
                    deliverables=json.dumps(
                        stage_info["deliverables"], ensure_ascii=False
                    ),
                    instructions=stage_info["instructions"],
                    context=json.dumps(hack, ensure_ascii=False),
                    created_by="conductor",
                )
                db.add(subtask)
                db.flush()
                prev_task_id = subtask.id

                db.add(ConductorLog(
                    task_id=subtask.id,
                    action="created",
                    message=f"Этап: {stage} для {hack['title'][:60]}",
                ))

        db.commit()

        summary_lines.append(
            f"\n📋 Создано задач: {len(selected) * len(PIPELINE_STAGES)} "
            f"({len(PIPELINE_STAGES)} этапов × {len(selected)} хакатонов)\n"
            f"ID корневой задачи: #{root_task.id}\n"
            f"\nЭтапы: discovery → analysis → ideation → planning → "
            f"documents → development → submission\n"
            f"\nАвтономное выполнение запущено. Используй /status для отслеживания."
        )

        return "\n".join(summary_lines)

    except Exception as e:
        db.rollback()
        logger.error("Pipeline creation failed: %s", e)
        return f"Ошибка создания конвейера: {e}"
    finally:
        db.close()


async def execute_pipeline_stage(task_title: str, task_context: str,
                                  task_instructions: str) -> str:
    """Выполнение одного этапа конвейера. Вызывается из auto_execute_cycle."""
    ctx = {}
    try:
        ctx = json.loads(task_context)
    except (json.JSONDecodeError, TypeError):
        pass

    title_lower = task_title.lower()

    if "поиск и отбор" in title_lower or "discovery" in title_lower:
        return await _stage_discovery(ctx)
    elif "анализ правил" in title_lower or "analysis" in title_lower:
        return await _stage_analysis(ctx)
    elif "генерация идеи" in title_lower or "ideation" in title_lower:
        return await _stage_ideation(ctx, task_instructions)
    elif "план работ" in title_lower or "planning" in title_lower:
        return await _stage_planning(ctx, task_instructions)
    elif "документы" in title_lower or "documents" in title_lower:
        return await _stage_documents(ctx, task_instructions)
    elif "разработка" in title_lower or "development" in title_lower:
        return await _stage_development(ctx, task_instructions)
    elif "подача" in title_lower or "submission" in title_lower:
        return await _stage_submission(ctx, task_instructions)
    else:
        return f"Неизвестный этап: {task_title}"


# ─── Этапы конвейера ──────────────────────────────────────────────────────────


async def _stage_discovery(ctx: dict) -> str:
    """Этап 1: Подробная информация о хакатоне."""
    title = ctx.get("title", "")
    url = ctx.get("url", "")
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    page_text = await scanner._fetch_page_text(url)
    if len(page_text) < 100:
        return f"Не удалось загрузить страницу {url}. Проверь вручную."
    return (
        f"Хакатон: {title}\nURL: {url}\n"
        f"Приз: {ctx.get('prize', 'N/A')}\n"
        f"Дедлайн: {ctx.get('deadline', 'N/A')}\n\n"
        f"Содержимое страницы (первые 3000 символов):\n{page_text[:3000]}"
    )


async def _stage_analysis(ctx: dict) -> str:
    """Этап 2: Глубокий анализ правил и требований хакатона."""
    from services.opportunity_scanner import get_scanner, PARTICIPANT_CONTEXT
    scanner = get_scanner()
    title = ctx.get("title", "")
    url = ctx.get("url", "")

    page_text = await scanner._fetch_page_text(url)

    prompt = f"""Проанализируй хакатон для участия.

ХАКАТОН: {title}
URL: {url}
ПРИЗ: {ctx.get('prize', 'N/A')}
ДЕДЛАЙН: {ctx.get('deadline', 'N/A')}

СОДЕРЖИМОЕ СТРАНИЦЫ:
{page_text[:4000]}

{PARTICIPANT_CONTEXT}

Формат КРАТКО:

## Суть хакатона
Тема | Формат (онлайн/офлайн) | Приз | Дедлайн подачи

## Требования к проекту
- Что нужно создать
- Технологии / API которые нужно использовать
- Критерии оценки (если указаны)

## Правила участия
- Кто может участвовать
- Команда: мин/макс размер
- Что нужно для регистрации

## Чеклист
✅ — соответствуем
❌ — не соответствуем (что нужно)

## Вердикт
Участвовать? Да/Нет и почему."""

    return await scanner._call_llm(prompt, max_tokens=3000)


async def _stage_ideation(ctx: dict, instructions: str = "") -> str:
    """Этап 3: Генерация идеи проекта для хакатона."""
    from services.opportunity_scanner import get_scanner, PARTICIPANT_CONTEXT
    scanner = get_scanner()

    prompt = f"""Сгенерируй 3 идеи проекта для хакатона.

ХАКАТОН: {ctx.get('title', '')}
URL: {ctx.get('url', '')}
ПРИЗ: {ctx.get('prize', 'N/A')}
ОПИСАНИЕ: {ctx.get('description', '')}

{PARTICIPANT_CONTEXT}

{f'ДОПОЛНИТЕЛЬНЫЕ ИНСТРУКЦИИ: {instructions}' if instructions else ''}

Для каждой идеи:
## Идея [N]: [Название]
- Суть: 2-3 предложения
- Технический стек: конкретные технологии
- MVP за сколько дней/часов
- Почему победит: уникальность, критерии оценки
- Риски и как их снять

Выбери ЛУЧШУЮ идею и обоснуй выбор в конце."""

    return await scanner._call_llm(prompt, max_tokens=3000, temperature=0.6)


async def _stage_planning(ctx: dict, instructions: str = "") -> str:
    """Этап 4: План работ и архитектура проекта."""
    from services.opportunity_scanner import get_scanner, PARTICIPANT_CONTEXT
    scanner = get_scanner()

    prompt = f"""Составь детальный план работ для проекта на хакатон.

ХАКАТОН: {ctx.get('title', '')}
ДЕДЛАЙН: {ctx.get('deadline', 'N/A')}

{PARTICIPANT_CONTEXT}

{f'КОНТЕКСТ ЭТАПА: {instructions}' if instructions else ''}

Формат:

## Архитектура
- Компоненты системы
- Стек технологий
- Схема взаимодействия

## План работ (по дням/часам)
День 1: [задачи]
День 2: [задачи]
...

## Критический путь
Что делать в первую очередь, чтобы точно успеть

## Риски
- Риск → митигация

## Ресурсы
- Что нужно (API ключи, серверы, данные)
- Что уже есть
- Что нужно получить"""

    return await scanner._call_llm(prompt, max_tokens=3000)


async def _stage_documents(ctx: dict, instructions: str = "") -> str:
    """Этап 5: Регистрация и подготовка документов для подачи."""
    from services.opportunity_scanner import get_scanner, PARTICIPANT_CONTEXT
    scanner = get_scanner()

    prompt = f"""Подготовь все документы для подачи на хакатон.

ХАКАТОН: {ctx.get('title', '')}
URL: {ctx.get('url', '')}

{PARTICIPANT_CONTEXT}

{f'КОНТЕКСТ: {instructions}' if instructions else ''}

Подготовь:

## 1. README.md проекта
Полный текст README для GitHub репозитория:
- Название и описание
- Скриншоты/демо (placeholder)
- Установка и запуск
- Технический стек
- Архитектура
- Команда

## 2. Описание проекта для DevPost
- Inspiration
- What it does
- How we built it
- Challenges we ran into
- Accomplishments that we're proud of
- What we learned
- What's next

## 3. Pitch (30 секунд)
Краткий текст для видео-питча

## 4. Чеклист подачи
☐ Каждый пункт что нужно для подачи"""

    return await scanner._call_llm(prompt, max_tokens=4000)


async def _stage_development(ctx: dict, instructions: str = "") -> str:
    """Этап 6: Трекинг разработки — генерирует список задач для создания MVP."""
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()

    prompt = f"""Составь детальный таск-лист для разработки MVP проекта на хакатон.

ХАКАТОН: {ctx.get('title', '')}
ДЕДЛАЙН: {ctx.get('deadline', 'N/A')}

{f'КОНТЕКСТ: {instructions}' if instructions else ''}

Формат — список задач для разработчика:

## Backend
- [ ] Задача 1 (X часов)
- [ ] Задача 2 (X часов)

## Frontend
- [ ] Задача 1 (X часов)

## AI/ML
- [ ] Задача 1 (X часов)

## Интеграции
- [ ] Задача 1 (X часов)

## Тестирование и деплой
- [ ] Задача 1 (X часов)

## Демо и видео
- [ ] Запись демо (X часов)
- [ ] Монтаж видео (X часов)

ИТОГО: X часов

Приоритет: сначала то, что видно в демо."""

    return await scanner._call_llm(prompt, max_tokens=3000)


async def _stage_submission(ctx: dict, instructions: str = "") -> str:
    """Этап 7: Финальная сборка и инструкция по подаче."""
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()

    prompt = f"""Подготовь финальный чеклист для подачи проекта на хакатон.

ХАКАТОН: {ctx.get('title', '')}
URL: {ctx.get('url', '')}
ДЕДЛАЙН: {ctx.get('deadline', 'N/A')}

{f'КОНТЕКСТ: {instructions}' if instructions else ''}

## Финальный чеклист подачи

### Код
☐ Репозиторий публичный на GitHub
☐ README.md заполнен
☐ Демо доступно по ссылке
☐ Код работает (npm start / docker-compose up)

### DevPost
☐ Проект создан на {ctx.get('url', 'devpost')}
☐ Описание заполнено (все секции)
☐ Скриншоты загружены (мин. 3)
☐ Видео-демо загружено (макс. 3 мин)
☐ Технологии отмечены
☐ Ссылка на GitHub указана
☐ Ссылка на демо указана

### Команда
☐ Все участники добавлены в проект на DevPost
☐ Роли указаны

### Перед отправкой
☐ Проверить что демо работает
☐ Проверить что видео воспроизводится
☐ Убедиться что все поля заполнены
☐ Нажать Submit до дедлайна: {ctx.get('deadline', 'N/A')}

## Ссылки для подачи
- DevPost: {ctx.get('url', '')}
- Нажать "Start a Submission" / "Enter a Submission"
"""

    return await scanner._call_llm(prompt, max_tokens=2000)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _parse_prize(prize_str: str) -> int:
    """Извлечь числовое значение приза в долларах."""
    if not prize_str:
        return 0
    clean = re.sub(r"[^\d,.]", "", prize_str.replace(",", ""))
    try:
        return int(float(clean))
    except (ValueError, TypeError):
        return 0


def _stage_config(stage: str, hack: dict) -> dict:
    """Конфигурация подзадачи для каждого этапа конвейера."""
    title = hack.get("title", "")[:120]
    configs = {
        "discovery": {
            "title": f"Поиск и отбор: {title}",
            "description": f"Загрузить страницу хакатона, собрать информацию",
            "agent": "hackathon_manager",
            "hours": 0.5,
            "deliverables": ["Полная информация о хакатоне"],
            "instructions": "Загрузи страницу хакатона и извлеки ключевую информацию",
        },
        "analysis": {
            "title": f"Анализ правил: {title}",
            "description": f"Глубокий анализ правил, требований, критериев оценки",
            "agent": "hackathon_manager",
            "hours": 1.0,
            "deliverables": ["Анализ правил", "Чеклист требований", "Вердикт"],
            "instructions": "Проанализируй правила, требования к участникам и проекту, критерии оценки",
        },
        "ideation": {
            "title": f"Генерация идеи: {title}",
            "description": f"Генерация и выбор лучшей идеи проекта",
            "agent": "hackathon_manager",
            "hours": 1.0,
            "deliverables": ["3 идеи проекта", "Выбор лучшей с обоснованием"],
            "instructions": "Сгенерируй идеи проектов, учитывая критерии оценки хакатона",
        },
        "planning": {
            "title": f"План работ: {title}",
            "description": f"Архитектура, стек, план по дням",
            "agent": "hackathon_manager",
            "hours": 1.5,
            "deliverables": ["Архитектура", "План по дням", "Список ресурсов"],
            "instructions": "Составь план разработки MVP с учётом дедлайна",
        },
        "documents": {
            "title": f"Документы: {title}",
            "description": f"README, описание для DevPost, питч",
            "agent": "hackathon_manager",
            "hours": 2.0,
            "deliverables": ["README.md", "DevPost описание", "Питч 30 сек"],
            "instructions": "Подготовь все тексты для подачи проекта",
        },
        "development": {
            "title": f"Разработка MVP: {title}",
            "description": f"Таск-лист для создания рабочего MVP",
            "agent": "hackathon_manager",
            "hours": 20.0,
            "deliverables": ["Таск-лист разработки", "Оценка трудозатрат"],
            "instructions": "Составь детальный таск-лист для разработки рабочего MVP",
        },
        "submission": {
            "title": f"Подача проекта: {title}",
            "description": f"Финальная сборка и подача на DevPost",
            "agent": "hackathon_manager",
            "hours": 1.0,
            "deliverables": ["Чеклист подачи", "Ссылки"],
            "instructions": "Подготовь финальный чеклист и инструкцию по подаче",
        },
    }
    return configs.get(stage, configs["discovery"])


async def get_pipeline_status(root_task_id: int | None = None) -> str:
    """Получить статус конвейера хакатонов."""
    from backend.database import SessionLocal
    from backend.models import ConductorTask, TaskStatus

    db = SessionLocal()
    try:
        if root_task_id:
            root = db.get(ConductorTask, root_task_id)
            if not root:
                return f"Задача #{root_task_id} не найдена."
            roots = [root]
        else:
            roots = (
                db.query(ConductorTask)
                .filter(ConductorTask.agent_role == "hackathon_manager")
                .filter(ConductorTask.level == "conductor")
                .order_by(ConductorTask.created_at.desc())
                .limit(3)
                .all()
            )

        if not roots:
            return "Нет запущенных конвейеров хакатонов."

        lines = ["**Hackathon Pipeline — статус**\n"]
        for root in roots:
            lines.append(f"📦 #{root.id}: {root.title[:80]}")
            lines.append(f"   Статус: {root.status.value}\n")

            # Подзадачи (хакатоны)
            hack_tasks = (
                db.query(ConductorTask)
                .filter(ConductorTask.parent_id == root.id)
                .all()
            )
            for ht in hack_tasks:
                stages = (
                    db.query(ConductorTask)
                    .filter(ConductorTask.parent_id == ht.id)
                    .order_by(ConductorTask.id)
                    .all()
                )
                done = sum(1 for s in stages if s.status == TaskStatus.COMPLETED)
                total = len(stages)
                progress = f"{done}/{total}"
                current = next(
                    (s for s in stages if s.status in (
                        TaskStatus.PENDING, TaskStatus.IN_PROGRESS
                    )), None
                )
                current_stage = current.title[:40] if current else "завершено"
                status_icon = "✅" if done == total else "🔄"
                lines.append(
                    f"  {status_icon} {ht.title[:60]} [{progress}]"
                    f"\n     → {current_stage}"
                )

        return "\n".join(lines)
    finally:
        db.close()
