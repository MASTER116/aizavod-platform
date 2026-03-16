# AI ZAVOD — Мультиагентная SaaS-платформа

## Обзор проекта
AI Zavod — платформа из 19+ AI-агентов, управляемая через Telegram-бот и мета-оркестратор CONDUCTOR.
Основатель — инженер 32 года, Татарстан/Москва, доход 200К. ООО планируется август 2026.
Цель: автоматизировать все бизнес-процессы — от поиска грантов до продаж на фрилансе.

## Архитектура
```
Telegram Bot (aiogram 3) → CONDUCTOR (мета-оркестратор) → 19 агентов
                         → FastAPI Backend → PostgreSQL
                         → Celery + Redis (фоновые задачи)
                         → APScheduler (автономные циклы)
```

### Docker Compose сервисы
- `telegram-bot` — aiogram 3 бот, точка входа пользователя
- `backend` — FastAPI (REST API, модели, маршруты)
- `postgres` — PostgreSQL (conductor_tasks, saved_ideas, agent_decisions)
- `redis` — кеш и очереди Celery
- `celery` — фоновые задачи
- `nginx` — reverse proxy
- `n8n` — визуальная автоматизация

## Структура файлов
- `services/` — бизнес-логика всех агентов
  - `conductor.py` — CONDUCTOR мета-оркестратор (роутер + CEO-декомпозиция)
  - `conductor_autonomy.py` — автономный режим (auto_execute_cycle каждые 10 мин)
  - `opportunity_scanner.py` — поиск грантов/конкурсов, DevPost API, deep_analyze
  - `hackathon_pipeline.py` — полный цикл хакатонов (7 этапов)
  - `freelance_agent.py` — поиск заказов на фрилансе
  - `market_analyzer.py` — анализ рынка и конкурентов
  - `pdf_generator.py` — генерация PDF (fpdf2, DejaVu)
  - `excel_generator.py` — генерация Excel-смет (openpyxl)
  - Остальные: ceo_agent, lawyer_agent, accountant_agent, scholar_agent, etc.
- `telegram_bot/` — aiogram 3 бот
  - `handlers/` — обработчики по разделам (opportunities, conductor, sales, legal, content, status)
  - `keyboards.py` — все inline-клавиатуры
- `backend/` — FastAPI
  - `models.py` — SQLAlchemy модели (ConductorTask, SavedIdea, etc.)
  - `routes/` — API эндпоинты (conductor, planning, etc.)
- `prompts/` — YAML шаблоны промптов

## CONDUCTOR — мета-оркестратор
Два режима:
1. **Роутер**: вопрос → keyword/Claude классификация → агент → ответ
2. **Оркестратор**: задача → CEO-декомпозиция → директора → отделы → специалисты

### 8 директоров: CTO, CFO, CMO, COO, CPO, CDO, CHRO, CLO
### 19 агентов: ceo, certifier, opportunity_scanner, hackathon_manager, idea_generator, market_analyzer, freelance_agent, pricing_agent, outreach_agent, content_factory, lawyer_agent, accountant_agent, darwin_agent, guardian_agent, scholar_agent, herald_agent, namer_agent, guardian_ip_agent, voice_agent, treasurer_agent

## Правила разработки

### Telegram бот
- Уведомления КОРОТКИЕ: "🔍 Ищу...", "🔬 Анализ...", "💡 Генерирую идеи..."
- Никаких длинных описаний в уведомлениях
- `_safe_send()` — fallback на parse_mode=None при TelegramBadRequest
- Кнопки: полные названия, без обрезки
- Ссылки: HTML-формат `<a href="">Ссылка</a>`

### Анализ грантов/конкурсов
- Анализ ТОЛЬКО по официальным сайтам, НЕ по статьям/новостям
- Фильтр доменов-статей: tadviser, habr, vc.ru, rbc.ru, etc.
- НЕ показывать: просроченные, студенческие, НКО-only
- Вузовские гранты — ок, если можно участвовать по ГПХ
- Формат: чеклист ✅/❌, цифры, даты — без воды
- НЕ писать инструкции пользователю ("перейдите", "скачайте") — агент делает сам
- Идеи генерируются ТОЛЬКО по кнопке, не автоматически
- Хакатоны — отдельная кнопка "Хакатоны — полный цикл" (DevPost API)
- Документы на подачу — PDF (не текст/JSON)

### Профиль участника (PARTICIPANT_CONTEXT)
- 32 года, доход 200К, Татарстан/Москва
- Инженер, нет PhD, нет публикаций, нет аффилиации с вузом
- ООО нет (планируется август 2026), бюджет 0 руб
- Варианты: напрямую (физлицо/ИП/ООО) или через вуз по ГПХ

### Hackathon Pipeline (7 этапов)
1. Discovery → 2. Analysis → 3. Ideation → 4. Planning → 5. Documents → 6. Development → 7. Submission
- Автоматическое создание задач в conductor_tasks
- auto_execute_cycle выполняет последовательно

### Фриланс (в разработке)
- Kwork: автопоиск заказов >1000₽, анализ ТЗ, цена -10% от средней
- Перед откликом — справка в Telegram (проект, бюджет, цена, маржа, сроки)
- Отклик только после одобрения кнопкой
- Нужен Playwright для авторизации на Kwork

## Команды
- `docker compose build telegram-bot && docker compose up -d telegram-bot` — пересборка бота
- `docker logs aizavod-telegram-bot-1 --tail 20` — логи бота
- `docker exec aizavod-telegram-bot-1 python3 -c "..."` — выполнить в контейнере

## RAG — векторная память (ChromaDB + ONNX)
Хранит полную историю разговоров. Используй при потере контекста после компакта.
- БД: `/root/.claude/rag/chroma_db`
- Скрипт: `/root/.claude/rag/memory_rag.py`
- Модель: `all-MiniLM-L6-v2` (ONNX, ~80MB)

### Команды
```bash
# Дампнуть все сессии в RAG
python3 /root/.claude/rag/memory_rag.py dump_all_sessions
# Поиск по истории
python3 /root/.claude/rag/memory_rag.py search "запрос"
# Статистика
python3 /root/.claude/rag/memory_rag.py stats
```

### Когда использовать
- После компакта контекста — дампить текущую сессию и искать потерянный контекст
- При ссылке пользователя на предыдущие разговоры
- Для восстановления решений и правил из прошлых сессий

## .env переменные
- `ANTHROPIC_API_KEY` — ключ Claude API
- `TELEGRAM_BOT_TOKEN` — токен бота
- `SCANNER_MODEL` — модель для сканера (claude-haiku-4-5-20251001)
- `CONDUCTOR_MODEL` — модель для CONDUCTOR (claude-haiku-4-5-20251001)
- `KWORK_LOGIN` / `KWORK_PASSWORD` — логин Kwork (в .env, НЕ в коде)
