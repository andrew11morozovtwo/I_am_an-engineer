"""
Stats service: получение статистики для админ-панели
"""
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import (
    UserRepository, BanRepository, WarnRepository, 
    BlacklistRepository, LogRepository
)

async def get_stats() -> dict:
    """Получить статистику для команды /stats"""
    async with get_async_session() as session:
        total_users = await UserRepository.count_all(session)
        banned_users = await UserRepository.count_banned(session)
        active_users_list = await UserRepository.get_active_users(session, days=7)
        active_users_count = len(active_users_list)
        warns_count = await WarnRepository.count_recent(session, days=7)
        blacklist_size = await BlacklistRepository.count_all(session)
        recent_logs = await LogRepository.get_recent(session, limit=5)
        
        return {
            "total_users": total_users,
            "active_users": active_users_count,
            "banned_users": banned_users,
            "warns_recent": warns_count,
            "blacklist_size": blacklist_size,
            "recent_logs": recent_logs
        }
