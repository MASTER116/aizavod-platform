# AIZAVOD — AI Content Factory

Автономная система генерации и публикации контента в Instagram от лица AI-персонажа.

## Возможности

- Генерация фотореалистичных изображений (FLUX 2 Pro)
- Генерация видео для Reels (Kling 3.0, 4K/60fps)
- Озвучка (Fish Audio S1)
- Фоновая музыка (Suno)
- Билингвальные подписи и хештеги (Claude AI)
- Автопубликация: фото, Stories, Reels, карусели
- Автоответы на комментарии
- Контент-стратегия на неделю одной командой
- Управление через Telegram-бот и Web-панель
- Аналитика, мониторинг, трекинг рекламных кампаний

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend | FastAPI + SQLAlchemy 2.x + Pydantic v2 |
| Telegram-бот | aiogram 3 |
| Web-панель | React 18 + Vite + Tailwind CSS |
| Фото | FLUX 2 Pro (Replicate) |
| Видео | Kling 3.0 (Replicate) |
| Голос | Fish Audio S1 |
| Музыка | Suno |
| Тексты | Claude (Anthropic) |
| Instagram | instagrapi |
| Планировщик | APScheduler |
| БД | SQLite (dev) / PostgreSQL (prod) |

## Быстрый старт

### Локально (разработка)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Заполнить .env ключами API
python run.py
```

Backend: http://localhost:8000
Документация API: http://localhost:8000/docs

### На сервере

```bash
# Первоначальная установка
bash deploy/setup.sh

# Заполнить .env
nano /opt/aizavod/.env

# Запуск
systemctl start aizavod

# Логи
journalctl -u aizavod -f
```

## Структура проекта

```
aizavod/
├── backend/
│   ├── main.py            # FastAPI app + lifespan
│   ├── config.py          # Конфигурация из .env
│   ├── database.py        # SQLAlchemy engine
│   ├── models.py          # 10 ORM-моделей
│   ├── schemas.py         # Pydantic v2 схемы
│   ├── admin_auth.py      # JWT авторизация
│   └── routes/            # 9 модулей роутов (47 эндпоинтов)
├── services/
│   ├── image_generator.py     # FLUX 2 Pro
│   ├── video_generator.py     # Kling 3.0
│   ├── voice_generator.py     # Fish Audio S1
│   ├── music_generator.py     # Suno
│   ├── caption_generator.py   # Claude AI
│   ├── content_strategy.py    # Контент-планирование
│   ├── hashtag_optimizer.py   # Хештеги по категориям
│   ├── post_processor.py      # Обработка изображений (Pillow)
│   ├── instagram_client.py    # Публикация в Instagram
│   ├── instagram_analytics.py # Сбор метрик
│   ├── scheduler.py           # 6 фоновых задач
│   ├── monetization.py        # Rate card, media kit
│   └── character_manager.py   # Управление персонажем
├── telegram_bot/
│   ├── main.py            # Бот + Dispatcher
│   ├── handlers/          # Обработчики команд
│   ├── keyboards.py       # Inline-клавиатуры
│   └── middlewares.py     # Admin-only фильтр
├── web-ui/
│   └── src/pages/         # React: Dashboard, Posts, Analytics...
├── prompts/               # YAML-шаблоны промптов
├── deploy/                # systemd, nginx, скрипты деплоя
├── requirements.txt
├── run.py                 # Точка входа
└── .env.example           # Шаблон конфигурации
```

## API-ключи

| Сервис | Где получить |
|--------|-------------|
| Replicate | https://replicate.com/account/api-tokens |
| Anthropic | https://console.anthropic.com/settings/keys |
| Fish Audio | https://fish.audio |
| Suno | https://suno.com |
| Telegram Bot | https://t.me/BotFather |

## Roadmap

- [x] Этап 1: Контент-завод для 1 персонажа
- [ ] Этап 2: Мульти-завод (несколько персонажей, PostgreSQL, Celery)
- [ ] Этап 3: SaaS-платформа с подписками

## Стоимость работы

~$57/мес при 2 поста + 5 Stories + 1 Reel в день (средний пакет).
