"""
Скрипт для миграции базы данных.
Добавляет отсутствующие колонки и обновляет структуру.
Запуск: python -m app.scripts.migrate_db
"""
import asyncio
from app.infrastructure.db.session import async_init_db

async def main():
    print("🔄 Начинаем миграцию базы данных...")
    try:
        await async_init_db()
        print("✅ Миграция завершена успешно!")
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
