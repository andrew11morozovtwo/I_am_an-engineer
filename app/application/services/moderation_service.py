"""
Сервис модерации: проверка сообщений на соответствие черному списку
"""
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import BlacklistRepository
from typing import List

async def check_message_for_blacklist(text: str) -> bool:
    """Проверяет, содержит ли текст запрещённые выражения из blacklist. True если найдено."""
    if not text:
        return False
    async with get_async_session() as session:
        blacklist = await BlacklistRepository.get_all(session)
        text_lower = text.lower()
        for item in blacklist:
            if item.phrase.lower() in text_lower:
                return True
        return False

async def add_to_blacklist(phrase: str, admin_id: int = None) -> bool:
    """Добавить фразу в черный список"""
    async with get_async_session() as session:
        existing = await BlacklistRepository.get_by_phrase(session, phrase)
        if existing:
            return False
        
        from app.infrastructure.db.models import BlacklistItem
        item = BlacklistItem(phrase=phrase, added_by=admin_id)
        await BlacklistRepository.add(session, item)
        
        from app.infrastructure.db.repositories import LogRepository
        from app.infrastructure.db.models import Log
        await LogRepository.add(session, Log(
            event_type="blacklist_added",
            user_id=admin_id,
            message=f"Добавлено в blacklist: {phrase}"
        ))
        return True

async def remove_from_blacklist(phrase: str, admin_id: int = None) -> bool:
    """Удалить фразу из черного списка"""
    async with get_async_session() as session:
        await BlacklistRepository.delete_by_phrase(session, phrase)
        
        from app.infrastructure.db.repositories import LogRepository
        from app.infrastructure.db.models import Log
        await LogRepository.add(session, Log(
            event_type="blacklist_removed",
            user_id=admin_id,
            message=f"Удалено из blacklist: {phrase}"
        ))
        return True

async def get_all_blacklist() -> List:
    """Получить весь черный список"""
    async with get_async_session() as session:
        return await BlacklistRepository.get_all(session)
