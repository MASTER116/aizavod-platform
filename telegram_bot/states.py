"""FSM state groups for Telegram bot."""
from aiogram.fsm.state import State, StatesGroup


class ManualPostStates(StatesGroup):
    choosing_category = State()
    entering_prompt = State()
    reviewing_generated = State()
    editing_caption = State()
    confirming_publish = State()


class SettingsStates(StatesGroup):
    choosing_setting = State()
    entering_value = State()
