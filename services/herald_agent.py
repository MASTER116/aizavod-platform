"""HERALD-OSS — DevRel и open-source продвижение Zavod-ii.

Open-source как маркетинговый канал: GitHub, Habr, Telegram,
Product Hunt. Построение бренда через создание ценности.
"""
from __future__ import annotations

import logging

from services.base_agent import BaseAgent

logger = logging.getLogger("aizavod.herald")


class HeraldAgent(BaseAgent):
    agent_name = "herald"
    model_env_var = "HERALD_MODEL"
    default_temperature = 0.6
    default_max_tokens = 2500

    system_prompt = (
        "Ты — HERALD, DevRel-агент платформы Zavod-ii. "
        "Твоя задача — продвижение через open-source и контент: "
        "GitHub README, статьи на Habr, посты в Telegram-канал, "
        "Product Hunt запуски. Пишешь технический контент, который "
        "привлекает разработчиков и бизнес. Стиль: профессиональный, "
        "но живой. Не рекламный — ценностный."
    )

    async def write_readme(self, project_name: str, description: str) -> str:
        """Написать README.md для open-source проекта."""
        prompt = f"""Напиши README.md для open-source проекта.

ПРОЕКТ: {project_name}
ОПИСАНИЕ: {description}

Структура README:
1. **Заголовок** с бейджами (Python, License, Stars)
2. **Одна строка** — что делает проект
3. **Ключевые фичи** — буллеты, 4-6 штук
4. **Quick Start** — установка и первый запуск (3-5 команд)
5. **Примеры использования** — код
6. **Документация** — ссылка
7. **Contributing** — как помочь
8. **License** — MIT/Apache
9. **Made by Zavod-ii** — ссылка на основной продукт

Пиши на английском. Стиль: чистый, профессиональный, как у stripe/vercel."""
        return await self._call_llm(prompt, max_tokens=3000)

    async def write_habr_article(self, topic: str, context: str = "") -> str:
        """Написать статью для Habr."""
        prompt = f"""Напиши статью для Habr.

ТЕМА: {topic}
КОНТЕКСТ: {context or 'Zavod-ii — мультиагентная платформа'}

Требования:
1. Заголовок — цепляющий, но не кликбейт
2. Введение — зачем читать (боль/проблема)
3. Основная часть — решение с примерами кода
4. Результаты — метрики, скриншоты, бенчмарки
5. Выводы — что читатель может применить сегодня
6. Упоминание Zavod-ii — органично, не рекламно

Стиль Habr: технический, с юмором, без воды.
Хабы: Python, Искусственный интеллект, Автоматизация."""
        return await self._call_llm(prompt, max_tokens=4000)

    async def telegram_post(self, topic: str, style: str = "dev") -> str:
        """Пост для Telegram-канала."""
        prompt = f"""Напиши пост для Telegram-канала Zavod-ii.

ТЕМА: {topic}
СТИЛЬ: {style} (dev — для разработчиков, biz — для бизнеса)

Формат:
- До 300 слов
- Эмодзи в начале абзацев
- Ключевой инсайт в первых 2 строках
- CTA в конце (подписка / GitHub / бот)
- Хэштеги: 3-5 штук"""
        return await self._call_llm(prompt, max_tokens=1000)

    async def product_hunt_launch(self, product_name: str, description: str) -> str:
        """Подготовить материалы для запуска на Product Hunt."""
        prompt = f"""Подготовь материалы для запуска на Product Hunt.

ПРОДУКТ: {product_name}
ОПИСАНИЕ: {description}

Нужно:
1. **Tagline** — до 60 символов
2. **Description** — до 260 символов
3. **First Comment** — от создателя (история, мотивация, просьба о фидбэке)
4. **Ключевые фичи** — 3-5 буллетов
5. **Topics** — категории на PH
6. **Стратегия запуска** — день, время, где просить апвоуты"""
        return await self._call_llm(prompt)

    async def oss_strategy(self, resources: str) -> str:
        """Стратегия open-source для текущих ресурсов."""
        prompt = f"""Разработай open-source стратегию.

РЕСУРСЫ: {resources}

Определи:
1. **Какой проект выложить** — что нужно разработчикам + мало конкурентов
2. **Почему именно этот** — анализ ниш на GitHub
3. **MVP** — минимальный набор фич для запуска
4. **Маркетинг** — где продвигать (Habr, HN, Reddit, Twitter)
5. **Воронка** — бесплатное → платное
6. **Метрики успеха** — звёзды, клоны, issues"""
        return await self._call_llm(prompt)


_agent: HeraldAgent | None = None


def get_herald_agent() -> HeraldAgent:
    global _agent
    if _agent is None:
        _agent = HeraldAgent()
    return _agent
