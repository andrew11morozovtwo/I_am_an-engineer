"""
Сервис модерации: проверка сообщений на соответствие черному списку
"""
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import BlacklistRepository

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
