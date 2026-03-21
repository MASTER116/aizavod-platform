# ZAVOD-II — Мультиагентная SaaS-платформа

## Обзор проекта
Zavod-ii (AI-Завод / "Заводи бизнес с AI") — единая платформа из 21+ AI-агентов с 3 уровнями доступа, управляемая через Telegram-бот, Web UI и мета-оркестратор CONDUCTOR.
Этап 1: Zavod-ii (zavod-ii.ru) — публичный продукт для РФ/СНГ.
Этап 2: Aialtyn — холдинг/юрлицо + международный бренд (aialtyn.ru/com).

### Уровни доступа
1. **SIMPLE** (публичный) — 291 отрасль, базовые агенты. FREE/STARTER/PRO тарифы.
2. **PRO** (только основатель) — полный CONDUCTOR, все агенты, CEO-декомпозиция, автономность.
3. **ENTERPRISE** (2027+) — white-label, кастом-агенты, SLA, MCP-совместимость.

## Архитектура
```
[Telegram Bot / Web UI / REST API]
              |
      [FastAPI Gateway + Rate Limiter]
              |
      [CONDUCTOR v2 — Meta-Orchestrator]
     /    |     |     |    \
  21+ специализированных агентов
  + QA-AGENT (critic) + COMPLIANCE-AGENT
     \    |     |     |    /
  [LLM Client: Claude API ←→ Ollama ←→ Cache]
  [Circuit Breaker + Fallback Chain]
              |
      [PostgreSQL + Redis]
              |
      [Celery + APScheduler (автономность)]
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
- `services/conductor/` — **CONDUCTOR пакет (декомпозированный)**
  - `__init__.py` — экспорты
  - `schemas.py` — Pydantic-модели (AgentMessage, AgentResponse, AccessLevel, QAVerdict, MemoryEntry)
  - `registry.py` — реестр агентов (AgentInfo, AGENTS, access_level, tier)
  - `hierarchy.py` — директора, отделы, специалисты
  - `prompts.py` — все промпты CONDUCTOR
  - `routes.py` — обработчики маршрутов + ROUTE_HANDLERS dict
  - `llm_client.py` — LLM-клиент с CircuitBreaker и Ollama fallback
  - `core.py` — класс Conductor (основная логика)
- `services/conductor.py` — обратная совместимость (re-export из пакета)
- `services/qa_agent.py` — QA-AGENT (Critic pattern, PII-детекция, injection-маркеры)
- `services/compliance_agent.py` — COMPLIANCE-AGENT (152-ФЗ, PII masking, audit log)
- `services/` — бизнес-логика агентов
  - `conductor_autonomy.py` — автономный режим (auto_execute_cycle каждые 10 мин)
  - `opportunity_scanner.py` — поиск грантов/конкурсов, DevPost API, deep_analyze
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
### 20+ агентов: ceo, certifier, opportunity_scanner, idea_generator, market_analyzer, freelance_agent, pricing_agent, outreach_agent, content_factory, lawyer_agent, accountant_agent, darwin_agent, guardian_agent, scholar_agent, herald_agent, namer_agent, guardian_ip_agent, voice_agent, treasurer_agent, oracle_agent
### Новые системные агенты: qa_agent (critic), compliance_agent (152-ФЗ)

### Circuit Breaker (LLM Client)
- 3 состояния: CLOSED (норма) → OPEN (после 3 отказов, 60с timeout) → HALF_OPEN (пробный)
- Fallback chain: Claude API → Ollama/Qwen3 → cached response → error
- Файл: `services/conductor/llm_client.py`

### Pydantic Schemas (межагентные сообщения)
- `AgentMessage` — типизированное сообщение между агентами
- `AgentResponse` — типизированный ответ с metadata, cost, tokens
- `QAVerdict` — результат проверки QA-AGENT (APPROVE/IMPROVE/REJECT)
- `AccessLevel` — simple/pro/enterprise
- Файл: `services/conductor/schemas.py`

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
