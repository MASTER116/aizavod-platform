# CONDUCTOR -- План реализации мета-оркестратора

## Версия 1.0 | 2026-03-16

---

## Что уже реализовано

- [x] CONDUCTOR роутер (keyword + Claude Haiku классификация)
- [x] 11 агентов (ceo, certifier, opportunity, ideas, market, freelance, pricing, outreach, content, lawyer, accountant)
- [x] REST API: /api/conductor/route, /agents, /tasks, /dashboard
- [x] ConductorTask + ConductorLog модели в БД
- [x] CLI conductor.py (submit, next, complete, decompose, list, status, dashboard)
- [x] Telegram интеграция (catch-all handler)
- [x] Деплой на Hetzner, все контейнеры работают

---

## Что нужно реализовать

### Этап 1: Директорские промпты (prompts/directors/)

Создать YAML файлы для каждого директора:

```
prompts/directors/
├── ceo.yaml
├── cto.yaml
├── cfo.yaml
├── cmo.yaml
├── coo.yaml
├── cpo.yaml
├── cdo.yaml
├── chro.yaml
└── clo.yaml
```

Каждый файл содержит:
- role, description
- departments[] — список подчинённых отделов
- decomposition_prompt — как разбивать задачи
- constraints — ограничения

### Этап 2: Отдельские промпты (prompts/departments/)

```
prompts/departments/
├── cto_backend.yaml
├── cto_frontend.yaml
├── cto_devops.yaml
├── cto_ai.yaml
├── cto_security.yaml
├── cfo_accounting.yaml
├── cfo_grants.yaml
├── cfo_freelance.yaml
├── cmo_content.yaml
├── cmo_outreach.yaml
├── cmo_devrel.yaml
├── cpo_certifier.yaml
├── cpo_saas.yaml
├── cdo_uiux.yaml
├── cdo_brand.yaml
├── clo_ip.yaml
├── clo_contracts.yaml
└── clo_registration.yaml
```

### Этап 3: Логика декомпозиции (services/conductor.py)

Добавить в Conductor:

1. `_detect_mode(query)` — определить роутер или оркестратор
2. `_ceo_decompose(query)` — CEO разбивает на задачи для директоров
3. `_director_decompose(task, director)` — директор разбивает на задачи для отделов
4. `_department_decompose(task, department)` — отдел разбивает на задачи для специалистов
5. `_execute_specialist(task)` — исполнение конкретной задачи
6. `_collect_results(parent_task)` — сборка результатов снизу вверх

### Этап 4: Обновление моделей БД

Добавить в ConductorTask:
- `level` (str): "conductor", "director", "department", "specialist"
- `assigned_to` (str): "cto", "cto.frontend", "cto.frontend.web_developer"
- `execution_order` (str): "parallel", "sequential", "blocked"
- `dependencies` (JSON str): [task_id, task_id]
- `estimated_hours` (float): оценка времени
- `deliverables` (JSON str): ["файл1.py", "описание"]

### Этап 5: Обновление CLI и API

conductor.py:
- `orchestrate <задача>` — запустить полный цикл декомпозиции
- `tree <task_id>` — показать дерево задач

REST API:
- `POST /api/conductor/orchestrate` — полная декомпозиция + исполнение
- `GET /api/conductor/tree/{task_id}` — дерево задач

### Этап 6: Telegram

- `/orchestrate <задача>` — запустить мета-оркестрацию
- Уведомления по уровням: "CTO завершил свою часть", "Все директора готовы"

### Этап 7: Deploy + тест

Полный тест: "Сделай лендинг Zavod-ii" → декомпозиция → исполнение → сборка → отчёт

---

## Порядок реализации

1. Директорские YAML промпты (30 мин)
2. Отдельские YAML промпты (30 мин)
3. Обновление моделей БД + миграция (15 мин)
4. Логика _detect_mode + _ceo_decompose (45 мин)
5. Логика _director_decompose + _department_decompose (45 мин)
6. Сборка результатов _collect_results (20 мин)
7. CLI + API обновление (20 мин)
8. Telegram handler (15 мин)
9. Deploy + тест (15 мин)

---

## Файлы для изменения

| Файл | Изменение |
|------|-----------|
| services/conductor.py | +detect_mode, +ceo_decompose, +director/department decompose, +collect_results |
| backend/models.py | +level, +assigned_to, +execution_order, +dependencies, +estimated_hours, +deliverables в ConductorTask |
| backend/routes/conductor.py | +POST /orchestrate, +GET /tree/{id} |
| conductor.py (CLI) | +orchestrate, +tree |
| telegram_bot/handlers/conductor.py | +/orchestrate команда |
| prompts/directors/*.yaml | 9 новых файлов |
| prompts/departments/*.yaml | 18 новых файлов |
