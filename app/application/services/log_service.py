"""
Сервис для работы с логами: добавление, получение, очистка старых логов
"""
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import LogRepository
from app.infrastructure.db.models import Log
from typing import List, Optional

async def add_log(event_type: str, user_id: int = None, message: str = None) -> Log:
    """Добавить запись в лог"""
    async with get_async_session() as session:
        log = Log(
            event_type=event_type,
            user_id=user_id,
            message=message
        )
        return await LogRepository.add(session, log)

async def get_logs_by_type(event_type: str, limit: int = 50) -> List[Log]:
    """Получить логи по типу события"""
    async with get_async_session() as session:
        return await LogRepository.get_by_type(session, event_type, limit)

async def get_logs_by_user(user_id: int, limit: int = 50) -> List[Log]:
    """Получить логи по пользователю"""
    async with get_async_session() as session:
        return await LogRepository.get_by_user(session, user_id, limit)

async def get_recent_logs(limit: int = 100) -> List[Log]:
    """Получить последние логи"""
    async with get_async_session() as session:
        return await LogRepository.get_recent(session, limit)

async def cleanup_old_logs(days: int = 30):
    """Удалить логи старше указанного количества дней"""
    async with get_async_session() as session:
        await LogRepository.delete_old_logs(session, days)
