"""
Скрипт для полной очистки всех данных из базы данных.
Удаляет все данные из всех таблиц, но сохраняет структуру БД.
Запуск: python -m app.scripts.clear_all_data
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import delete, func
from sqlalchemy.future import select
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.models import (
    User, Admin, Ban, Warn, BlacklistItem, Log, 
    ScheduledPost, AiUsage
)


async def clear_all_data():
    """Очистить все данные из всех таблиц"""
    print("[INFO] Начинаем полную очистку базы данных...")
    print("[WARNING] Это удалит ВСЕ данные из всех таблиц!")
    
    async with get_async_session() as session:
        try:
            # Подсчитываем данные перед удалением
            counts = {}
            
            tables = [
                ("users", User),
                ("admins", Admin),
                ("bans", Ban),
                ("warns", Warn),
                ("blacklist", BlacklistItem),
                ("logs", Log),
                ("scheduled_posts", ScheduledPost),
                ("ai_usage", AiUsage),
            ]
            
            print("\n[INFO] Подсчитываем данные в таблицах...")
            for table_name, model in tables:
                try:
                    count = await session.execute(select(func.count(model.id)))
                    counts[table_name] = count.scalar() or 0
                    print(f"   - {table_name}: {counts[table_name]} записей")
                except Exception as e:
                    print(f"   - {table_name}: ошибка при подсчете ({e})")
                    counts[table_name] = 0
            
            total_records = sum(counts.values())
            if total_records == 0:
                print("\n[SUCCESS] База данных уже пуста, нечего удалять.")
                return
            
            print(f"\n[INFO] Всего найдено записей: {total_records}")
            print("[INFO] Начинаем удаление...")
            
            # Удаляем данные из всех таблиц (в правильном порядке из-за внешних ключей)
            # Сначала удаляем зависимые таблицы
            deletion_order = [
                ("ai_usage", AiUsage),
                ("logs", Log),
                ("scheduled_posts", ScheduledPost),
                ("bans", Ban),
                ("warns", Warn),
                ("blacklist", BlacklistItem),
                ("admins", Admin),
                ("users", User),
            ]
            
            deleted_counts = {}
            for table_name, model in deletion_order:
                try:
                    if counts.get(table_name, 0) > 0:
                        result = await session.execute(delete(model))
                        deleted_counts[table_name] = result.rowcount if hasattr(result, 'rowcount') else counts[table_name]
                        print(f"[SUCCESS] Удалено из {table_name}: {deleted_counts[table_name]} записей")
                    else:
                        print(f"[INFO] Таблица {table_name} уже пуста")
                except Exception as e:
                    print(f"[ERROR] Ошибка при удалении из {table_name}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Сохраняем изменения
            await session.commit()
            
            print("\n[SUCCESS] Полная очистка базы данных завершена!")
            print("[INFO] Удалено записей:")
            for table_name, count in deleted_counts.items():
                print(f"   - {table_name}: {count}")
            
            print("\n[INFO] Структура базы данных сохранена.")
            print("[INFO] Таблицы будут пересозданы при следующем запуске бота.")
            
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] Ошибка при очистке: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(clear_all_data())
