"""BaseAgent — базовый класс для всех AI-агентов AI Zavod.

Устраняет дублирование: инициализация клиента, вызов Claude API,
обработка ошибок, валидация ключа.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("aizavod.base_agent")


class BaseAgent:
    """Базовый класс для агентов, использующих Anthropic Claude API."""

    agent_name: str = "base"
    default_model: str = "claude-haiku-4-5-20251001"
    model_env_var: str = ""
    default_temperature: float = 0.5
    default_max_tokens: int = 500
    system_prompt: str = ""
    # Правило краткости — добавляется ко всем промптам
    BREVITY_RULE: str = (
        "\n\nПРАВИЛО: Отвечай КРАТКО, максимум 5-7 строк. "
        "Формат: "
        "1) Какие агенты/специалисты нужны (2-4 штуки). "
        "2) Цена подключения. "
        "3) Экономия в год. "
        "4) Ссылка: https://aizavod.ru/build. "
        "НЕ пиши длинные описания, технические детали, оценки сложности. "
        "Только суть."
    )

    def __init__(self) -> None:
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")
        model_env = self.model_env_var or f"{self.agent_name.upper()}_MODEL"
        self._model = os.getenv(model_env, self.default_model)

    async def _call_llm(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system: str | None = None,
    ) -> str:
        """Вызвать Claude API. Возвращает текст ответа или сообщение об ошибке."""
        if not self._api_key:
            return "ANTHROPIC_API_KEY не настроен"

        import anthropic

        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens or self.default_max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature if temperature is not None else self.default_temperature,
        }

        sys_prompt = system or self.system_prompt
        # Добавляем правило краткости ко всем промптам
        if sys_prompt:
            kwargs["system"] = sys_prompt + self.BREVITY_RULE
        else:
            kwargs["system"] = self.BREVITY_RULE.strip()

        try:
            client = anthropic.AsyncAnthropic(api_key=self._api_key)
            response = await client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            logger.error("Ошибка API в %s: %s", self.agent_name, e)
            return f"Ошибка при обработке запроса: {e}"
