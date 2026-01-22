"""
Скрипт для миграции базы данных.
Добавляет отсутствующие колонки и обновляет структуру.
Создает новые таблицы (например, post_comments).
Запуск: python -m app.scripts.migrate_db
"""
import asyncio
import sys
import io

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.infrastructure.db.session import async_init_db, get_async_session
from sqlalchemy import inspect, text

async def main():
    print("🔄 Начинаем миграцию базы данных...")
    try:
        await async_init_db()
        
        # Проверяем, что таблица post_comments создана
        from app.infrastructure.db.session import engine
        async with engine.begin() as conn:
            def check_table(sync_conn):
                inspector = inspect(sync_conn)
                table_names = inspector.get_table_names()
                
                if 'post_comments' in table_names:
                    print("✅ Таблица 'post_comments' успешно создана")
                    # Показываем структуру таблицы
                    columns = inspector.get_columns('post_comments')
                    print(f"   Колонки: {', '.join([col['name'] for col in columns])}")
                else:
                    print("⚠️ Таблица 'post_comments' не найдена (возможно, нужно пересоздать БД)")
            
            await conn.run_sync(check_table)
        
        print("✅ Миграция завершена успешно!")
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
