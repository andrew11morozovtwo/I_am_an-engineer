"""
Репозитории для доступа к БД через SQLAlchemy ORM (асинхронно).
UserRepository, BanRepository, WarnRepository, BlacklistRepository, LogRepository.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from .models import User, Ban, Warn, BlacklistItem, Log
from sqlalchemy import delete, update

# UserRepository
class UserRepository:
    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
        q = await session.execute(select(User).where(User.id == user_id))
        return q.scalar_one_or_none()

    @staticmethod
    async def add(session: AsyncSession, user: User) -> User:
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def update_username(session: AsyncSession, user_id: int, username: str):
        await session.execute(
            update(User).where(User.id == user_id).values(username=username)
        )
        await session.commit()

# BanRepository
class BanRepository:
    @staticmethod
    async def add(session: AsyncSession, ban: Ban):
        session.add(ban)
        await session.commit()
        await session.refresh(ban)
        return ban

    @staticmethod
    async def get_active_by_user(session: AsyncSession, user_id: int) -> Optional[Ban]:
        q = await session.execute(
            select(Ban).where(Ban.user_id == user_id)
            # тут можно добавить where Ban.until > now или иное для "актуального" бана
        )
        return q.scalar_one_or_none()

# WarnRepository
class WarnRepository:
    @staticmethod
    async def add(session: AsyncSession, warn: Warn):
        session.add(warn)
        await session.commit()
        await session.refresh(warn)
        return warn

    @staticmethod
    async def get_for_user(session: AsyncSession, user_id: int) -> List[Warn]:
        q = await session.execute(select(Warn).where(Warn.user_id == user_id))
        return q.scalars().all()

# BlacklistRepository
class BlacklistRepository:
    @staticmethod
    async def add(session: AsyncSession, item: BlacklistItem):
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    @staticmethod
    async def get_all(session: AsyncSession) -> List[BlacklistItem]:
        q = await session.execute(select(BlacklistItem))
        return q.scalars().all()

    @staticmethod
    async def delete_by_id(session: AsyncSession, item_id: int):
        await session.execute(delete(BlacklistItem).where(BlacklistItem.id == item_id))
        await session.commit()

# LogRepository
class LogRepository:
    @staticmethod
    async def add(session: AsyncSession, log: Log):
        session.add(log)
        await session.commit()

    @staticmethod
    async def get_by_type(session: AsyncSession, event_type: str, limit: int = 50) -> List[Log]:
        q = await session.execute(
            select(Log).where(Log.event_type == event_type).order_by(Log.created_at.desc()).limit(limit)
        )
        return q.scalars().all()
