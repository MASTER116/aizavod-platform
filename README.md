# AI ZAVOD — Мультиагентная платформа автоматизации бизнеса

Платформа с 9 AI-агентами для поиска заработка, продаж, контента и управления бизнесом.
Управление через Telegram-бот с интеллектуальным маршрутизатором запросов (CONDUCTOR).

## Архитектура

```
Основатель (Telegram) → CONDUCTOR → Классификация → Агент → Ответ
                              ↓
                    CEO-агент (оркестратор)
                    ├── Финансовый директор
                    │   ├── OpportunityScanner (гранты, конкурсы)
                    │   ├── IdeaGenerator (идеи заработка)
                    │   └── MarketAnalyzer (рынок, конкуренты)
                    ├── Директор по продажам
                    │   ├── FreelanceAgent (заказы, отклики)
                    │   ├── PricingAgent (оценка, КП)
                    │   └── OutreachAgent (холодные продажи)
                    ├── Директор по контенту
                    │   └── ContentFactory (Instagram, TikTok)
                    └── Директор по продукту
                        └── CertifierService (сертификация ТС ЕАЭС)
```

## Агенты

| Агент | Отдел | Функции |
|-------|-------|---------|
| CEO-агент | CEO | Стратегия, декомпозиция задач, распределение по директорам |
| OpportunityScanner | Финансы | Поиск грантов, хакатонов, конкурсов (ФАСИ, РНФ, Сколково) |
| IdeaGenerator | Финансы | Генерация идей заработка, монетизация |
| MarketAnalyzer | Финансы | Анализ рынка, конкурентов, подготовка заявок |
| FreelanceAgent | Продажи | Поиск заказов на Kwork/Upwork, генерация откликов |
| PricingAgent | Продажи | Оценка стоимости проектов, коммерческие предложения |
| OutreachAgent | Продажи | Холодные продажи, генерация писем, поиск лидов |
| ContentFactory | Контент | Генерация контента для Instagram/TikTok/VK |
| CertifierService | Продукт | Консультации по сертификации ТС, ТР ТС ЕАЭС (RAG + Claude) |

## CONDUCTOR — маршрутизатор запросов

Принимает произвольный запрос на естественном языке и автоматически направляет нужному агенту:

1. **Быстрая классификация** — по ключевым словам (< 1ms)
2. **Claude-классификация** — для сложных случаев (Claude Haiku 4.5)
3. **Multi-agent** — если запрос затрагивает несколько агентов

```
POST /api/conductor/route
{"query": "найди гранты для IT-стартапа"}
→ opportunity_scanner (confidence: 0.85)
```

В Telegram-боте: просто напиши текст — CONDUCTOR сам определит агента.

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend | FastAPI + SQLAlchemy 2.x + Pydantic v2 |
| LLM | Claude Haiku 4.5 (Anthropic API) |
| Telegram-бот | aiogram 3 + FSM |
| БД | PostgreSQL 16 + Redis 7 |
| Инфраструктура | Docker Compose (8 контейнеров) |
| Сервер | Hetzner, Ubuntu 22.04 |
| RAG (CERTIFIER) | BM25 + Claude API |
| Веб-поиск | DuckDuckGo HTML |

## Структура проекта

```
aizavod-platform/
├── backend/
│   ├── main.py              # FastAPI + lifespan
│   ├── config.py            # Конфигурация из .env
│   ├── database.py          # SQLAlchemy + PostgreSQL
│   ├── models.py            # 28+ ORM-моделей
│   ├── schemas.py           # Pydantic v2 схемы
│   ├── admin_auth.py        # JWT + API Key авторизация
│   └── routes/
│       ├── conductor.py     # CONDUCTOR API
│       ├── certifier.py     # CERTIFIER API
│       ├── opportunities.py # Гранты/конкурсы API
│       ├── agent.py         # Оркестратор контента
│       └── ...              # 15+ модулей роутов
├── services/
│   ├── conductor.py         # CONDUCTOR — маршрутизатор
│   ├── ceo_agent.py         # CEO-агент (оркестратор)
│   ├── certifier_service.py # CERTIFIER (RAG + Claude)
│   ├── opportunity_scanner.py # Сканер грантов
│   ├── market_analyzer.py   # Анализ рынка
│   ├── freelance_agent.py   # Фриланс-агент
│   ├── pricing_agent.py     # Ценообразование
│   ├── outreach_agent.py    # Холодные продажи
│   ├── agent_orchestrator.py # Оркестратор контента (IG)
│   └── ...                  # 30+ сервисов
├── telegram_bot/
│   ├── main.py              # Бот + Dispatcher
│   ├── handlers/
│   │   ├── start.py         # Главное меню (5 разделов)
│   │   ├── conductor.py     # Свободный ввод → CONDUCTOR
│   │   ├── ceo.py           # CEO-агент (задачи, стратегия)
│   │   ├── opportunities.py # Инвестиции
│   │   ├── money.py         # Продажи и фриланс
│   │   ├── system_status.py # Мониторинг системы
│   │   └── ...
│   ├── keyboards.py         # 6 inline-клавиатур
│   └── middlewares.py       # Admin-only фильтр
├── data/certifier/          # База знаний ТР ТС ЕАЭС (7 документов)
├── docker-compose.yml       # 8 контейнеров
└── .env                     # Конфигурация
```

## Telegram-бот

Меню бота:
- **Привлечь инвестиции** — гранты, идеи, анализ рынка, заявки
- **Продажи и фриланс** — заказы, отклики, КП, холодные продажи
- **Фабрика контента** — Instagram Factory
- **Задача / Запрос** — CEO-агент (вопрос, задача, стратегия)
- **Статус системы** — сервер, Docker, БД, агенты

Или просто напиши текст — CONDUCTOR автоматически направит нужному агенту.

## Запуск

### Docker (продакшен)

```bash
git clone https://github.com/MASTER116/aizavod-platform.git
cd aizavod-platform
cp .env.example .env
# Заполнить .env (ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, POSTGRES_PASSWORD)
docker compose up -d
```

### Локально (разработка)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
python run.py
```

## API

| Эндпоинт | Метод | Описание |
|-----------|-------|----------|
| `/health` | GET | Статус сервера |
| `/api/conductor/route` | POST | Маршрутизация запроса к агенту |
| `/api/conductor/agents` | GET | Список доступных агентов |
| `/api/certifier/ask` | POST | Вопрос по сертификации |
| `/api/opportunities/scan` | POST | Сканирование грантов |
| `/docs` | GET | Swagger UI |

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `ANTHROPIC_API_KEY` | Ключ Anthropic API (обязательно) |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота |
| `TELEGRAM_ADMIN_IDS` | ID админов через запятую |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `BACKEND_API_KEY` | Ключ для API бэкенда |
| `CONDUCTOR_MODEL` | Модель для CONDUCTOR (по умолчанию claude-haiku-4-5-20251001) |
| `CEO_MODEL` | Модель для CEO-агента |

## Roadmap

- [x] Инфраструктура: Docker Compose, PostgreSQL, Redis
- [x] CERTIFIER MVP (RAG + Claude API)
- [x] 9 AI-агентов (CEO, финансы, продажи, контент, продукт)
- [x] CONDUCTOR — интеллектуальный маршрутизатор
- [x] Telegram-бот с 5 разделами управления
- [ ] Первый платящий клиент
- [ ] Регистрация ООО (август 2026)
- [ ] Масштабирование: 37 категорий, 262 отрасли, 148 агентов
