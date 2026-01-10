"""
Запуск: python -m app.scripts.init_db
Создаёт все нужные таблицы с помощью async и SQLAlchemy.
"""
import asyncio
from app.infrastructure.db.session import async_init_db

if __name__ == "__main__":
    asyncio.run(async_init_db())
