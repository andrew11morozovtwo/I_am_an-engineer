"""
Async SQLAlchemy engine/session setup for AdminBot (using SQLite).
Include table init util.
"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import inspect, text
from app.config.settings import settings
from app.infrastructure.db.models import Base, UserStatus, Admin

DATABASE_URL = settings.DB_URL

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

@asynccontextmanager
async def get_async_session():
    """Async context manager для получения сессии БД"""
    async with async_session_factory() as session:
        yield session

async def async_init_db():
    """
    Создает все нужные таблицы по моделям ORM, если они отсутствуют в базе.
    Также добавляет отсутствующие колонки для миграции схемы.
    Запустить 1 раз при старте проекта, миграций или сбросе БД.
    """
    async with engine.begin() as conn:
        # Создаем все таблицы, если их нет
        await conn.run_sync(Base.metadata.create_all)
        
        # Проверяем и добавляем отсутствующие колонки
        await _migrate_users_table(conn)
    
    print("[DB INIT] Все нужные таблицы созданы (если отсутствовали).")

async def _migrate_users_table(conn):
    """
    Миграция: добавляет отсутствующие колонки в таблицу users (status, warn_count).
    """
    def check_and_add_columns(sync_conn):
        try:
            inspector = inspect(sync_conn)
            # Проверяем, существует ли таблица users
            if 'users' not in inspector.get_table_names():
                return
            
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            # Добавляем колонку status, если её нет
            if 'status' not in columns:
                print("[DB MIGRATION] Добавляем колонку 'status' в таблицу 'users'...")
                sync_conn.execute(text(
                    "ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active'"
                ))
                sync_conn.execute(text(
                    "UPDATE users SET status = 'active' WHERE status IS NULL"
                ))
                print("[DB MIGRATION] Колонка 'status' успешно добавлена.")
            
            # Добавляем колонку warn_count, если её нет
            if 'warn_count' not in columns:
                print("[DB MIGRATION] Добавляем колонку 'warn_count' в таблицу 'users'...")
                sync_conn.execute(text(
                    "ALTER TABLE users ADD COLUMN warn_count INTEGER DEFAULT 0"
                ))
                sync_conn.execute(text(
                    "UPDATE users SET warn_count = 0 WHERE warn_count IS NULL"
                ))
                print("[DB MIGRATION] Колонка 'warn_count' успешно добавлена.")
                
        except Exception as e:
            print(f"[DB MIGRATION] Ошибка при миграции: {e}")
            import traceback
            traceback.print_exc()
            # Не прерываем работу, если миграция не удалась
    
    await conn.run_sync(check_and_add_columns)
