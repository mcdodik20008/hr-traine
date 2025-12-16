"""
Алиас для онбординг-обработчиков.
Основная реализация находится в labs.py, но здесь экспортируем
те же сущности, чтобы перейти на новое имя модуля.
"""
from app.bot.handlers.labs import (
    router,
    cmd_onboarding,
    process_step_action,
    show_step,
    get_next_step,
    get_session,
)

__all__ = [
    "router",
    "cmd_onboarding",
    "process_step_action",
    "show_step",
    "get_next_step",
    "get_session",
]

