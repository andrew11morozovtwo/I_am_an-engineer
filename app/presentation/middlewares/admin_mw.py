"""
Admin check middleware: проверка прав администратора
"""
from aiogram import types
from aiogram.fsm.context import FSMContext
from typing import Callable, Awaitable, Any
from app.config.settings import settings

async def admin_check_middleware(
    handler: Callable[[types.Message, dict[str, Any]], Awaitable[Any]],
    event: types.Message,
    data: dict[str, Any]
) -> Any:
    """Проверяет, является ли пользователь администратором"""
    admin_ids = settings.get_admin_ids_list()
    
    if event.from_user and event.from_user.id not in admin_ids:
        await event.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    return await handler(event, data)
