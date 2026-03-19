# Zavod-ii — Мультиагентная SaaS-платформа автоматизации бизнеса

> "Заводи бизнес с AI" — 21+ AI-агент, 291 отрасль, 9 директоров, мета-оркестратор CONDUCTOR v2

Платформа с 21+ специализированными AI-агентами для автоматизации бизнес-процессов в РФ/СНГ.
Управление через Telegram-бот, Web UI и REST API.

## Архитектура

```
[Telegram Bot (admin-панель) / Web UI / REST API]
              |
      [FastAPI Gateway + Rate Limiter]
              |
      [CONDUCTOR v2 — Pipeline 17 шагов с safeguards]
     /    |     |     |    \
  21+ специализированных агентов
  + QA-AGENT (critic) + COMPLIANCE-AGENT (152-ФЗ)
     \    |     |     |    /
  [LLM Client: Claude API (prompt caching) <-> Ollama <-> Cache]
  [Circuit Breaker: CLOSED -> OPEN (3 failures) -> HALF_OPEN]
              |
      [PostgreSQL 16 + Redis 7]
              |
      [Celery + APScheduler (автономность)]
      [Observability + Session Trace + Cost Tracking]
```

### 3-уровневая иерархия CONDUCTOR

```
CEO (мета-оркестратор)
├── CTO — Backend, Frontend, DevOps, AI/ML, QA, Security
├── CFO — Бухгалтерия, Аналитика, Фриланс, Гранты
├── CMO — Контент, Outreach, DevRel, SEO
├── COO — Процессы, Партнёры
├── CPO — Сертификация, SaaS
├── CDO — ML/Данные
├── CHRO — HR
└── CLO — Юридический
```

## Агенты (21+)

| Агент | Отдел | Уровень | Описание |
|-------|-------|---------|----------|
| CEO | Руководство | PRO | Стратегия, декомпозиция задач, 3-уровневая оркестрация |
| Certifier | Продукт | Enterprise | Сертификация ТС ЕАЭС (RAG + Claude) |
| Opportunity Scanner | Финансы | PRO | Гранты, хакатоны, конкурсы (ФАСИ, РНФ, Сколково) |
| Idea Generator | Финансы | Free | Идеи заработка, монетизация |
| Market Analyzer | Финансы | Starter | Анализ рынка, конкурентов, заявки |
| Freelance Agent | Продажи | PRO | Заказы на Kwork/Upwork, отклики |
| Pricing Agent | Продажи | Starter | Оценка проектов, КП |
| Outreach Agent | Продажи | Starter | Холодные продажи, генерация писем |
| Content Factory | Контент | Starter | Instagram, TikTok, VK |
| Lawyer | Юридический | Free | Договоры, регистрация ИП/ООО, право |
| Accountant | Бухгалтерия | Free | Налоги, отчётность, УСН/ОСН |
| Darwin | Самообучение | PRO | Self-learning, оценка качества, weekly reports |
| Guardian | Безопасность | PRO | Антифрод, антиабьюз, injection detection |
| Guardian IP | Патенты | Pro | Товарные знаки, патенты, IP-аудит |
| Scholar | Наука | Pro | Грантовые заявки, научные статьи, ГОСТ/ВАК |
| Herald | Продвижение | Starter | Open-source, Хабр, Product Hunt |
| Namer | Нейминг | Free | Названия, домены, товарные знаки |
| Voice | Голос | Pro | Скрипты звонков, TTS-оптимизация |
| Treasurer | Казначейство | PRO | Монетизация, расходы, cash flow |
| Oracle | Аналитика | Pro | ML-прогнозы, классификация, аномалии |
| **QA-AGENT** | Система | — | Critic pattern, PII detection, injection markers |
| **COMPLIANCE** | Система | — | 152-ФЗ, PII masking, AI disclaimers, approval gates |

## Safeguards — 12 решённых проблем индустрии

| Проблема | Решение | Модуль |
|----------|---------|--------|
| Deadlock между агентами | DFS cycle detection | `safeguards.py` DeadlockDetector |
| Latency cascade (15-30 сек) | 10s budget + parallel dispatch | `safeguards.py` LatencyBudget |
| Role confusion | Per-agent boundary validation | `safeguards.py` RoleBoundaryValidator |
| Agent identity lifecycle | 5 states: DRAFT→ACTIVE→DEGRADED→SUSPENDED→RETIRED | `safeguards.py` LifecycleManager |
| Agent-to-agent attack | Inter-agent firewall + context isolation | `safeguards.py` InterAgentFirewall |
| Agent sprawl | Auto-sunset 30/90 days, usage tracking | `safeguards.py` LifecycleManager |
| Coordination tax (O(n²)) | Max 5 handoffs, 7 agents per workflow | `safeguards.py` CoordinationLimiter |
| UX trust gap | Progress streaming, confidence display | `safeguards.py` UXTransparency |
| Over-permissioning | Per-agent tool allowlist, DB access control | `safeguards.py` PermissionGuard |
| Debugging cost (40% sprint) | Error taxonomy (10 types), blame assignment | `safeguards.py` ErrorTracker |
| No session observability | Correlation ID, replay, blame | `session_trace.py` SessionTracer |
| 25 industry problems total | Full documentation | `docs/PROBLEMS_SOLUTIONS.md` |

## Военные стандарты (13 стандартов)

Архитектура проверена по 8 российским + 5 западным военным стандартам:

| Стандарт | Что применяем |
|----------|--------------|
| ГОСТ РВ 0015-002-2020 | СМК, управление конфигурацией, аудиты |
| ГОСТ Р 51904-2002 | 5 уровней критичности агентов (C/D/E) |
| ГОСТ 27.310-95 | FMEA/FMECA per agent (S×O×D=RPN) |
| ГОСТ Р 56939-2024 | Безопасная разработка ПО |
| ГОСТ 19.101-2024 | 6 из 14 типов ЕСПД документов |
| MIL-STD-498 | RTM, Review Gates, 6 DID документов |
| DO-178C | V&V gate, structural coverage, independence |
| MIL-STD-882E | Hazard Analysis |

Подробнее: `docs/DEVELOPMENT_AUDIT.md`

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend | FastAPI + SQLAlchemy 2.x + Pydantic v2 |
| LLM (основной) | Claude Haiku 4.5 (prompt caching, extended thinking) |
| LLM (fallback) | Ollama + Qwen3-30B (локальный, $0/мес) |
| Telegram-бот | aiogram 3 + FSM + admin-панель |
| БД | PostgreSQL 16 + Redis 7 |
| Фоновые задачи | Celery + APScheduler |
| Инфраструктура | Docker Compose (8 контейнеров) |
| Reverse proxy | Nginx + SSL |
| Автоматизация | n8n |
| Тесты | pytest (74 теста: unit, integration, adversarial, golden) |

## Структура проекта

```
zavod-ii/
├── backend/
│   ├── main.py              # FastAPI + lifespan
│   ├── models.py            # SQLAlchemy (ConductorTask, SavedIdea, ...)
│   ├── admin_auth.py        # JWT + API Key
│   └── routes/              # 15+ API роутов
├── services/
│   ├── conductor/           # CONDUCTOR v2 (декомпозированный пакет)
│   │   ├── core.py          # Pipeline 17 шагов
│   │   ├── safeguards.py    # 10 классов, 12 проблем
│   │   ├── session_trace.py # Correlation ID, replay, blame
│   │   ├── registry.py      # 21 агент с access_level, tier
│   │   ├── hierarchy.py     # 9 директоров, 18 отделов
│   │   ├── llm_client.py    # CircuitBreaker + Ollama fallback
│   │   ├── memory.py        # Letta 3-level (Core/Recall/Archival)
│   │   ├── observability.py # Langfuse-compatible traces, cost
│   │   └── schemas.py       # Pydantic: AgentMessage, QAVerdict
│   ├── qa_agent.py          # Critic pattern, PII, injection
│   ├── compliance_agent.py  # 152-ФЗ, PII masking, approval gates
│   ├── health_monitor.py    # DEADMAN kill-switch, 6 statuses
│   ├── billing/metering.py  # Tier limits (FREE:50 - ENT:50000/day)
│   ├── testing/ab_engine.py # A/B testing (Welch's t-test)
│   └── ...                  # 30+ агентов и сервисов
├── telegram_bot/
│   ├── main.py              # aiogram 3
│   ├── handlers/            # start, conductor, opportunities, admin_panel
│   └── keyboards.py         # Inline-клавиатуры
├── tests/                   # 74 теста (unit, integration, adversarial, golden)
├── docs/
│   ├── PROBLEMS_SOLUTIONS.md    # 25 проблем + решения
│   ├── DEVELOPMENT_AUDIT.md     # 55-point аудит + 13 военных стандартов
│   └── conductor/               # CONDUCTOR hierarchy, rules, plan
├── prompts/                 # YAML промпты (5-block, directors, departments)
├── docker-compose.yml       # 8 контейнеров
└── .github/workflows/       # CI/CD deploy
```

## Уровни доступа

| Уровень | Для кого | Агенты | Тариф |
|---------|----------|--------|-------|
| SIMPLE | Публичный | Базовые (lawyer, accountant, namer, idea) | FREE / STARTER 4990р / PRO 14990р |
| PRO | Основатель | Все 21+ агент, CONDUCTOR, DARWIN, GUARDIAN | — |
| ENTERPRISE | 2027+ | White-label, кастом-агенты, SLA, MCP | 49990р+ |

## CONDUCTOR — мета-оркестратор

Два режима:
1. **Роутер** — вопрос → keyword/Claude классификация → агент → ответ
2. **Оркестратор** — задача → CEO-декомпозиция → директора → отделы → специалисты → сборка

Pipeline v2 (17 шагов):
```
Session trace → Observability → Safeguards (latency, UX)
→ Metering → Health check → Safeguards (pre-route)
→ Classify → Route → Execute
→ Safeguards (role validation, lifecycle)
→ Session trace (span) → QA-AGENT → Compliance
→ Observability (end) → Session trace (end)
→ Metering (record) → DARWIN (background eval)
→ UX (complete)
```

## API

| Эндпоинт | Метод | Описание |
|-----------|-------|----------|
| `/health` | GET | Статус сервера |
| `/api/conductor/route` | POST | Маршрутизация запроса |
| `/api/conductor/orchestrate` | POST | 3-уровневая декомпозиция |
| `/api/conductor/agents` | GET | Список агентов |
| `/api/conductor/dashboard` | GET | Статистика CONDUCTOR |
| `/api/conductor/tree/{id}` | GET | Дерево задач |
| `/api/certifier/ask` | POST | Сертификация ТС ЕАЭС |
| `/api/opportunities/scan` | POST | Сканирование грантов |
| `/docs` | GET | Swagger UI |

## Запуск

### Docker (продакшен)

```bash
git clone https://github.com/MASTER116/aizavod-platform.git
cd aizavod-platform
cp .env.example .env
# Заполнить: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, POSTGRES_PASSWORD
docker compose up -d
```

### Локально (разработка)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
python run.py
```

### Тесты

```bash
pytest tests/ -v  # 74 теста, ~0.86s
```

## Telegram Admin-панель

6 секций управления прямо из Telegram:
- Здоровье агентов (статусы, error rate, latency)
- Расходы и токены (daily spend, per-agent cost/quality)
- A/B эксперименты (winner, p-value, recommendation)
- Metering лимиты (per-user usage, tier)
- Compliance аудит (152-ФЗ, data residency, audit log)
- Kill-Switch DEADMAN (kill/revive per agent)

## Roadmap

- [x] 21+ AI-агентов с 3-уровневой иерархией CONDUCTOR
- [x] Safeguards: 12 проблем AI-агентных систем решены
- [x] 74 теста (unit, integration, adversarial, golden)
- [x] Observability + Session Trace + Cost Tracking
- [x] DARWIN self-learning + QA-AGENT + COMPLIANCE
- [x] Telegram admin-панель (6 секций)
- [x] A/B testing engine
- [x] AI SEO (llms.txt, robots.txt, JSON-LD)
- [x] Аудит по 13 военным стандартам (8 ГОСТ РВ + 5 MIL-STD)
- [ ] Миграция ПД на RU-сервер (Selectel) — 152-ФЗ
- [ ] Лендинг zavod-ii.ru
- [ ] Первый платящий клиент
- [ ] Регистрация ООО (август 2026)
- [ ] 291 отрасль, 148 агентов

## Документация

| Документ | Описание |
|----------|----------|
| `CLAUDE.md` | Полное описание проекта для AI-ассистентов |
| `docs/PROBLEMS_SOLUTIONS.md` | 25 проблем индустрии + решения |
| `docs/DEVELOPMENT_AUDIT.md` | Аудит 55 пунктов + 13 военных стандартов |
| `docs/conductor/CONDUCTOR_HIERARCHY.md` | 9 директоров, 18 отделов, 3 уровня |
| `docs/conductor/CONDUCTOR_RULES.md` | Правила декомпозиции задач |
| `docs/conductor/IMPLEMENTATION_PLAN.md` | 7-шаговый план реализации |

## Лицензия

MIT
