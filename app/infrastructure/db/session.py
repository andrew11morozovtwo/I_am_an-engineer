"""
Async SQLAlchemy engine/session setup for AdminBot (using SQLite).
Include table init util.
"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config.settings import settings
from app.infrastructure.db.models import Base

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
    Запустить 1 раз при старте проекта, миграций или сбросе БД.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[DB INIT] Все нужные таблицы созданы (если отсутствовали).")
