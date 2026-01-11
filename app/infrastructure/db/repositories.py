"""
Репозитории для доступа к БД через SQLAlchemy ORM (асинхронно).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from .models import User, Ban, Warn, BlacklistItem, Log, UserStatus, Admin
from sqlalchemy import delete, update, func
import datetime

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
    async def update_status(session: AsyncSession, user_id: int, status: UserStatus):
        await session.execute(
            update(User).where(User.id == user_id).values(
                status=status, 
                is_banned=(status == UserStatus.BANNED)
            )
        )
        await session.commit()

    @staticmethod
    async def update_user_info(session: AsyncSession, user_id: int, username: str = None, full_name: str = None):
        """Обновить информацию о пользователе (username, full_name)"""
        values = {}
        if username is not None:
            values['username'] = username
        if full_name is not None:
            values['full_name'] = full_name
        
        if values:
            await session.execute(
                update(User).where(User.id == user_id).values(**values)
            )
            await session.commit()

    @staticmethod
    async def increment_warn_count(session: AsyncSession, user_id: int):
        user = await UserRepository.get_by_id(session, user_id)
        if user:
            user.warn_count = (user.warn_count or 0) + 1
            await session.commit()
            await session.refresh(user)

    @staticmethod
    async def get_all(session: AsyncSession) -> List[User]:
        q = await session.execute(select(User))
        return q.scalars().all()

    @staticmethod
    async def count_all(session: AsyncSession) -> int:
        q = await session.execute(select(func.count(User.id)))
        return q.scalar() or 0

    @staticmethod
    async def count_banned(session: AsyncSession) -> int:
        q = await session.execute(select(func.count(User.id)).where(User.status == UserStatus.BANNED))
        return q.scalar() or 0

    @staticmethod
    async def get_active_users(session: AsyncSession, days: int = 7) -> List[User]:
        """Получить активных пользователей за последние N дней (есть логи)"""
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        subquery = select(Log.user_id).where(Log.created_at >= cutoff_date).distinct()
        q = await session.execute(select(User).where(User.id.in_(subquery)))
        return q.scalars().all()

class BanRepository:
    @staticmethod
    async def add(session: AsyncSession, ban: Ban) -> Ban:
        session.add(ban)
        await session.commit()
        await session.refresh(ban)
        return ban

    @staticmethod
    async def get_active_by_user(session: AsyncSession, user_id: int) -> Optional[Ban]:
        now = datetime.datetime.utcnow()
        q = await session.execute(
            select(Ban).where(Ban.user_id == user_id)
            .where((Ban.until.is_(None)) | (Ban.until > now))
            .order_by(Ban.created_at.desc())
        )
        return q.scalar_one_or_none()

    @staticmethod
    async def unban_user(session: AsyncSession, user_id: int):
        now = datetime.datetime.utcnow()
        await session.execute(
            update(Ban).where(Ban.user_id == user_id)
            .where((Ban.until.is_(None)) | (Ban.until > now))
            .values(until=now)
        )
        await session.commit()

class WarnRepository:
    @staticmethod
    async def add(session: AsyncSession, warn: Warn) -> Warn:
        session.add(warn)
        await session.commit()
        await session.refresh(warn)
        return warn

    @staticmethod
    async def get_for_user(session: AsyncSession, user_id: int) -> List[Warn]:
        q = await session.execute(select(Warn).where(Warn.user_id == user_id).order_by(Warn.created_at.desc()))
        return q.scalars().all()

    @staticmethod
    async def count_recent(session: AsyncSession, days: int = 7) -> int:
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        q = await session.execute(select(func.count(Warn.id)).where(Warn.created_at >= cutoff_date))
        return q.scalar() or 0

class BlacklistRepository:
    @staticmethod
    async def add(session: AsyncSession, item: BlacklistItem) -> BlacklistItem:
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    @staticmethod
    async def get_all(session: AsyncSession) -> List[BlacklistItem]:
        q = await session.execute(select(BlacklistItem).order_by(BlacklistItem.created_at.desc()))
        return q.scalars().all()

    @staticmethod
    async def get_by_phrase(session: AsyncSession, phrase: str) -> Optional[BlacklistItem]:
        q = await session.execute(select(BlacklistItem).where(BlacklistItem.phrase == phrase))
        return q.scalar_one_or_none()

    @staticmethod
    async def delete_by_phrase(session: AsyncSession, phrase: str):
        await session.execute(delete(BlacklistItem).where(BlacklistItem.phrase == phrase))
        await session.commit()

    @staticmethod
    async def count_all(session: AsyncSession) -> int:
        q = await session.execute(select(func.count(BlacklistItem.id)))
        return q.scalar() or 0

class LogRepository:
    @staticmethod
    async def add(session: AsyncSession, log: Log) -> Log:
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log

    @staticmethod
    async def get_recent(session: AsyncSession, limit: int = 5) -> List[Log]:
        q = await session.execute(select(Log).order_by(Log.created_at.desc()).limit(limit))
        return q.scalars().all()

class AdminRepository:
    """Репозиторий для управления администраторами."""
    
    @staticmethod
    async def add_admin(
        session: AsyncSession,
        user_id: int,
        username: str | None = None,
        full_name: str | None = None,
        role: str = "moderator",
        added_by: int | None = None
    ) -> Admin:
        """Добавить администратора."""
        admin = Admin(
            user_id=user_id,
            username=username,
            full_name=full_name,
            role=role,
            is_active=True,
            added_by=added_by
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin
    
    @staticmethod
    async def remove_admin(session: AsyncSession, user_id: int) -> bool:
        """Удалить администратора (мягкое удаление — is_active=False)."""
        result = await session.execute(
            update(Admin).where(Admin.user_id == user_id).values(is_active=False)
        )
        await session.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def get_admin(session: AsyncSession, user_id: int) -> Optional[Admin]:
        """Получить администратора по user_id."""
        q = await session.execute(select(Admin).where(Admin.user_id == user_id))
        return q.scalar_one_or_none()
    
    @staticmethod
    async def get_all_admins(session: AsyncSession) -> List[Admin]:
        """Получить всех активных администраторов."""
        q = await session.execute(
            select(Admin).where(Admin.is_active == True).order_by(Admin.created_at)
        )
        return q.scalars().all()
    
    @staticmethod
    async def is_admin(session: AsyncSession, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором."""
        admin = await AdminRepository.get_admin(session, user_id)
        return admin is not None and admin.is_active
    
    @staticmethod
    async def get_admin_role(session: AsyncSession, user_id: int) -> Optional[str]:
        """Получить роль администратора."""
        admin = await AdminRepository.get_admin(session, user_id)
        return admin.role if admin and admin.is_active else None
    
    @staticmethod
    async def update_admin_role(
        session: AsyncSession,
        user_id: int,
        new_role: str
    ) -> bool:
        """Изменить роль администратора."""
        result = await session.execute(
            update(Admin).where(Admin.user_id == user_id).values(role=new_role)
        )
        await session.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def update_admin_info(
        session: AsyncSession,
        user_id: int,
        username: str | None = None,
        full_name: str | None = None
    ) -> bool:
        """Обновить информацию об администраторе (username, full_name)."""
        values = {}
        if username is not None:
            values['username'] = username
        if full_name is not None:
            values['full_name'] = full_name
        
        if values:
            result = await session.execute(
                update(Admin).where(Admin.user_id == user_id).values(**values)
            )
            await session.commit()
            return result.rowcount > 0
        return False
