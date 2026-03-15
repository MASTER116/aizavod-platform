# AIZAVOD - AI Instagram Factory

## Project Structure
- `backend/` - FastAPI backend (config, models, routes, auth)
- `services/` - Shared business logic (image generation, captions, Instagram client, scheduler)
- `telegram_bot/` - aiogram 3 Telegram bot for control
- `web-ui/` - React + Vite + Tailwind admin panel
- `prompts/` - YAML prompt templates for Flux and Claude
- `media/` - Generated images/videos (gitignored)

## Tech Stack
- Python 3.11+, FastAPI, SQLAlchemy 2.x (Mapped), Pydantic v2
- aiogram 3 for Telegram, instagrapi for Instagram
- Replicate API (Flux Kontext Dev) for image generation
- Anthropic Claude API for text generation
- APScheduler for background tasks
- React 18 + Vite + Tailwind CSS for admin panel

## Conventions
- Follow AZAT Platform patterns (see autopark, kwork_bot, sharing116)
- SQLAlchemy models use `Mapped` type annotations
- Config via environment variables / .env
- JWT auth for admin panel (PyJWT)
- Bot communicates with backend via httpx (X-API-Key header)

## Commands
- `python run.py` - start backend + bot
- `cd web-ui && npm run dev` - start admin panel dev server
