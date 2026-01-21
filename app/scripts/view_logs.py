"""
Скрипт для просмотра логов из базы данных в консоли.
Запуск: python -m app.scripts.view_logs [--limit N] [--type TYPE] [--user USER_ID]
"""
import sys
import asyncio
import os
from pathlib import Path
from datetime import datetime

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.infrastructure.db.session import get_async_session, async_init_db
from app.infrastructure.db.repositories import LogRepository
from app.infrastructure.db.models import Log
from sqlalchemy import select, func, desc
from sqlalchemy.future import select as future_select
from typing import Optional


async def view_logs(limit: int = 50, event_type: Optional[str] = None, user_id: Optional[int] = None):
    """
    Просмотр логов из базы данных.
    
    Args:
        limit: Количество последних логов для отображения (по умолчанию 50)
        event_type: Фильтр по типу события (опционально)
        user_id: Фильтр по ID пользователя (опционально)
    """
    await async_init_db()
    
    async with get_async_session() as session:
        # Формируем запрос
        query = select(Log)
        
        if event_type:
            query = query.where(Log.event_type == event_type)
        
        if user_id:
            query = query.where(Log.user_id == user_id)
        
        query = query.order_by(desc(Log.created_at)).limit(limit)
        
        result = await session.execute(query)
        logs = result.scalars().all()
        
        if not logs:
            print("[INFO] Логи не найдены в базе данных.")
            return
        
        # Получаем общее количество логов
        count_query = select(func.count(Log.id))
        if event_type:
            count_query = count_query.where(Log.event_type == event_type)
        if user_id:
            count_query = count_query.where(Log.user_id == user_id)
        
        total_result = await session.execute(count_query)
        total_count = total_result.scalar() or 0
        
        print(f"\n{'='*80}")
        print(f"[LOGS] ЛОГИ БОТА (показано {len(logs)} из {total_count})")
        print(f"{'='*80}\n")
        
        for log in logs:
            # Форматируем дату
            date_str = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "N/A"
            
            # Форматируем вывод
            print(f"[{date_str}] {log.event_type or 'N/A'}")
            if log.user_id:
                print(f"  [USER] User ID: {log.user_id}")
            if log.message:
                # Обрезаем длинные сообщения
                message = log.message[:200] + "..." if len(log.message) > 200 else log.message
                print(f"  [MSG] {message}")
            print("-" * 80)


async def view_logs_summary():
    """Показывает сводку по логам"""
    await async_init_db()
    
    async with get_async_session() as session:
        # Общее количество логов
        total_count = await LogRepository.get_logs_count(session)
        
        # Количество по типам событий
        result = await session.execute(
            select(Log.event_type, func.count(Log.id))
            .group_by(Log.event_type)
            .order_by(desc(func.count(Log.id)))
        )
        type_counts = result.all()
        
        print(f"\n{'='*80}")
        print(f"[SUMMARY] СВОДКА ПО ЛОГАМ")
        print(f"{'='*80}\n")
        print(f"Всего логов: {total_count}\n")
        
        if type_counts:
            print("По типам событий:")
            for event_type, count in type_counts:
                print(f"  - {event_type}: {count}")
        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Просмотр логов бота")
    parser.add_argument("--limit", type=int, default=50, help="Количество логов для отображения (по умолчанию 50)")
    parser.add_argument("--type", type=str, help="Фильтр по типу события")
    parser.add_argument("--user", type=int, help="Фильтр по ID пользователя")
    parser.add_argument("--summary", action="store_true", help="Показать только сводку")
    
    args = parser.parse_args()
    
    if args.summary:
        asyncio.run(view_logs_summary())
    else:
        asyncio.run(view_logs(limit=args.limit, event_type=args.type, user_id=args.user))
