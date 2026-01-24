"""
User service: регистрация пользователей, варны, баны
"""
import logging
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import UserRepository, WarnRepository, BanRepository, LogRepository
from app.infrastructure.db.models import User, Warn, Ban, Log, UserStatus
from typing import Optional
from sqlalchemy import select, and_, update
import datetime
from app.common.error_handler import handle_error, ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)

async def register_user(user_id: int, username: str = None, full_name: str = None) -> User:
    """Регистрация нового пользователя или обновление информации существующего"""
    async with get_async_session() as session:
        user = await UserRepository.get_by_id(session, user_id)
        is_new_user = False
        
        if not user:
            # Новый пользователь
            user = User(
                id=user_id,
                username=username,
                full_name=full_name,
                status=UserStatus.ACTIVE
            )
            user = await UserRepository.add(session, user)
            is_new_user = True
            
            # Логируем регистрацию
            await LogRepository.add(session, Log(
                event_type="user_registered",
                user_id=user_id,
                message=f"Новый пользователь зарегистрирован: {full_name or username or user_id}"
            ))
        else:
            # Существующий пользователь - обновляем информацию, если она изменилась
            needs_update = False
            if username is not None and user.username != username:
                needs_update = True
            if full_name is not None and user.full_name != full_name:
                needs_update = True
            
            if needs_update:
                await UserRepository.update_user_info(session, user_id, username=username, full_name=full_name)
                # Обновляем объект user после изменения
                user = await UserRepository.get_by_id(session, user_id)
            
            # Логируем повторное использование команды /start
            await LogRepository.add(session, Log(
                event_type="user_started",
                user_id=user_id,
                message=f"Пользователь использовал /start: {full_name or username or user_id}"
            ))
        
        return user

async def add_warn(user_id: int, reason: str = None, admin_id: int = None) -> Warn:
    """Добавить варн пользователю"""
    async with get_async_session() as session:
        user = await UserRepository.get_by_id(session, user_id)
        if not user:
            # Создаем пользователя в текущей сессии
            user = User(
                id=user_id,
                status=UserStatus.ACTIVE
            )
            user = await UserRepository.add(session, user)
        
        warn = Warn(user_id=user_id, reason=reason)
        warn = await WarnRepository.add(session, warn)
        
        await UserRepository.increment_warn_count(session, user_id)
        
        await LogRepository.add(session, Log(
            event_type="warn_added",
            user_id=admin_id,
            message=f"Варн добавлен пользователю {user_id}. Причина: {reason or 'не указана'}"
        ))
        
        return warn

async def ban_user(user_id: int, reason: str = None, days: int = None, admin_id: int = None) -> Ban:
    """Забанить пользователя"""
    async with get_async_session() as session:
        user = await UserRepository.get_by_id(session, user_id)
        if not user:
            # Создаем пользователя в текущей сессии
            user = User(
                id=user_id,
                status=UserStatus.BANNED
            )
            user = await UserRepository.add(session, user)
        else:
            await UserRepository.update_status(session, user_id, UserStatus.BANNED)
        
        until = None
        if days:
            until = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        
        ban = Ban(user_id=user_id, reason=reason, until=until)
        ban = await BanRepository.add(session, ban)
        
        await LogRepository.add(session, Log(
            event_type="user_banned",
            user_id=admin_id,
            message=f"Пользователь {user_id} забанен. Причина: {reason or 'не указана'}"
        ))
        
        return ban

async def get_user_ban(user_id: int) -> Optional[Ban]:
    """Получить активный бан пользователя"""
    async with get_async_session() as session:
        return await BanRepository.get_active_by_user(session, user_id)

async def get_user_by_id(user_id: int) -> Optional[User]:
    """Получить пользователя по ID"""
    async with get_async_session() as session:
        return await UserRepository.get_by_id(session, user_id)

async def get_user_warns_count(user_id: int) -> int:
    """Получить количество варнов пользователя"""
    async with get_async_session() as session:
        user = await UserRepository.get_by_id(session, user_id)
        return user.warn_count if user else 0

async def unban_user(user_id: int) -> bool:
    """Снять бан с пользователя"""
    async with get_async_session() as session:
        user = await UserRepository.get_by_id(session, user_id)
        if not user:
            return False
        
        # Снимаем бан в таблице Ban
        await BanRepository.unban_user(session, user_id)
        
        # Обновляем статус пользователя
        await UserRepository.update_status(session, user_id, UserStatus.ACTIVE)
        
        # Логируем снятие бана
        await LogRepository.add(session, Log(
            event_type="user_unbanned",
            user_id=user_id,
            message=f"Бан снят с пользователя {user_id}"
        ))
        
        return True

async def unban_expired_users() -> int:
    """
    Автоматически снимает бан с пользователей, у которых истек срок бана.
    Возвращает количество разбаненных пользователей.
    """
    async with get_async_session() as session:
        now = datetime.datetime.utcnow()
        
        # Получаем все активные баны с истекшим сроком
        expired_bans_query = select(Ban).where(
            and_(
                Ban.until.isnot(None),
                Ban.until <= now
            )
        )
        
        result = await session.execute(expired_bans_query)
        expired_bans = result.scalars().all()
        
        unban_count = 0
        unbanned_user_ids = set()  # Чтобы не обрабатывать одного пользователя дважды
        
        for ban in expired_bans:
            if ban.user_id in unbanned_user_ids:
                continue  # Уже обработали этого пользователя
                
            try:
                # Снимаем конкретный истекший бан - устанавливаем until на текущее время
                # Это гарантирует, что бан больше не будет считаться активным
                await session.execute(
                    update(Ban).where(Ban.id == ban.id)
                    .values(until=now)
                )
                
                # Проверяем, есть ли у пользователя еще активные баны
                # Если нет - обновляем статус на ACTIVE
                active_ban = await BanRepository.get_active_by_user(session, ban.user_id)
                if not active_ban:
                    await UserRepository.update_status(session, ban.user_id, UserStatus.ACTIVE)
                
                # Логируем автоматическое снятие бана
                await LogRepository.add(session, Log(
                    event_type="user_unbanned_auto",
                    user_id=ban.user_id,
                    message=f"Автоматически снят бан с пользователя {ban.user_id} (истек срок)"
                ))
                
                unbanned_user_ids.add(ban.user_id)
                unban_count += 1
                logger.info(f"✅ Автоматически снят бан с пользователя {ban.user_id}")
            except Exception as e:
                await handle_error(
                    error=e,
                    context=ErrorContext(
                        operation="unban_expired_users.unban_user",
                        user_id=ban.user_id,
                        severity=ErrorSeverity.MEDIUM
                    )
                )
                continue
        
        if unban_count > 0:
            await session.commit()
        
        return unban_count
