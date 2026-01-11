"""
Admin service: управление администраторами, проверка прав доступа
"""
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import AdminRepository, UserRepository, LogRepository
from app.infrastructure.db.models import Log, Admin
from typing import Optional, List
from sqlalchemy import update
from app.config.settings import settings

# Иерархия ролей
ROLE_HIERARCHY = {
    "moderator": 1,
    "senior_admin": 2,
    "owner": 3
}

async def check_admin_permission(user_id: int, required_role: str = "moderator") -> bool:
    """
    Проверить, является ли пользователь администратором нужной роли.
    
    Args:
        user_id: user_id для проверки
        required_role: минимально требуемая роль
                      ("moderator" < "senior_admin" < "owner")
    
    Returns:
        True если админ имеет нужную роль
    """
    async with get_async_session() as session:
        admin = await AdminRepository.get_admin(session, user_id)
        if not admin or not admin.is_active:
            return False
        
        admin_level = ROLE_HIERARCHY.get(admin.role, 0)
        required_level = ROLE_HIERARCHY.get(required_role, 0)
        return admin_level >= required_level

async def get_admin_role(user_id: int) -> Optional[str]:
    """Получить роль администратора."""
    async with get_async_session() as session:
        return await AdminRepository.get_admin_role(session, user_id)

async def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором."""
    async with get_async_session() as session:
        return await AdminRepository.is_admin(session, user_id)

async def can_add_admin(performer_id: int, target_role: str) -> bool:
    """
    Проверить, может ли пользователь добавить администратора с указанной ролью.
    
    Правила:
    - owner может добавлять всех
    - senior_admin может добавлять moderator
    - moderator не может никого добавлять
    """
    performer_role = await get_admin_role(performer_id)
    if not performer_role:
        return False
    
    performer_level = ROLE_HIERARCHY.get(performer_role, 0)
    target_level = ROLE_HIERARCHY.get(target_role, 0)
    
    if performer_role == "owner":
        return True
    elif performer_role == "senior_admin":
        return target_role == "moderator"
    else:
        return False

async def can_remove_admin(performer_id: int, target_user_id: int) -> tuple[bool, str]:
    """
    Проверить, может ли пользователь удалить указанного администратора.
    
    Returns:
        (can_remove: bool, error_message: str)
    """
    # Owner не может быть удален (кроме случая, если это сам owner удаляет себя через код)
    if target_user_id == settings.OWNER_ID:
        return False, "❌ Вы не можете удалить главного администратора (owner)"
    
    performer_role = await get_admin_role(performer_id)
    if not performer_role:
        return False, "❌ У вас нет прав администратора"
    
    async with get_async_session() as session:
        target_admin = await AdminRepository.get_admin(session, target_user_id)
        if not target_admin or not target_admin.is_active:
            return False, "❌ Пользователь не является администратором"
        
        target_role = target_admin.role
    
    if performer_role == "owner":
        return True, ""
    elif performer_role == "senior_admin":
        if target_role == "moderator":
            return True, ""
        else:
            return False, "❌ Недостаточно прав. Senior admin может удалять только moderator"
    else:
        return False, "❌ Недостаточно прав. Только owner и senior_admin могут удалять администраторов"

async def can_change_role(performer_id: int, target_role: str, new_role: str) -> bool:
    """
    Проверить, может ли пользователь изменить роль администратора.
    
    Правила:
    - owner может менять все роли
    - senior_admin может менять роли moderator
    - moderator не может менять роли
    """
    performer_role = await get_admin_role(performer_id)
    if not performer_role:
        return False
    
    if performer_role == "owner":
        return True
    elif performer_role == "senior_admin":
        return target_role == "moderator" and new_role == "moderator"
    else:
        return False

async def add_admin(
    user_id: int,
    role: str = "moderator",
    added_by: int | None = None,
    username: str | None = None,
    full_name: str | None = None
) -> tuple[bool, str]:
    """
    Добавить администратора.
    
    Returns:
        (success: bool, message: str)
    """
    async with get_async_session() as session:
        # Проверяем, существует ли пользователь в системе
        user = await UserRepository.get_by_id(session, user_id)
        if not user:
            return False, "Ошибка: пользователь не найден в системе"
        
        # Проверяем, не админ ли уже
        existing_admin = await AdminRepository.get_admin(session, user_id)
        if existing_admin and existing_admin.is_active:
            return False, "Ошибка: пользователь уже администратор"
        
        # Если был деактивирован, активируем заново
        if existing_admin and not existing_admin.is_active:
            # Обновляем существующую запись
            await session.execute(
                update(Admin).where(Admin.user_id == user_id).values(
                    is_active=True,
                    role=role,
                    username=username or user.username,
                    full_name=full_name or user.full_name,
                    added_by=added_by
                )
            )
            await session.commit()
            admin = await AdminRepository.get_admin(session, user_id)
        else:
            # Добавляем нового админа
            admin = await AdminRepository.add_admin(
                session,
                user_id=user_id,
                username=username or user.username,
                full_name=full_name or user.full_name,
                role=role,
                added_by=added_by
            )
        
        # Логируем
        try:
            performer = await AdminRepository.get_admin(session, added_by) if added_by else None
            performer_name = performer.username if performer and performer.username else str(added_by)
            await LogRepository.add(session, Log(
                event_type="admin_added",
                user_id=user_id,
                message=f"Пользователь @{admin.username or user_id} добавлен как администратор (роль: {role}) пользователем @{performer_name}"
            ))
        except Exception as e:
            print(f"Ошибка при логировании добавления админа: {e}")
        
        username_display = f"@{admin.username}" if admin.username else str(user_id)
        return True, f"👤 Пользователь {username_display} добавлен как администратор (роль: {role})"

async def remove_admin(user_id: int, removed_by: int) -> tuple[bool, str]:
    """
    Удалить администратора.
    
    Returns:
        (success: bool, message: str)
    """
    async with get_async_session() as session:
        admin = await AdminRepository.get_admin(session, user_id)
        if not admin or not admin.is_active:
            return False, "Ошибка: пользователь не является администратором"
        
        # Мягкое удаление
        success = await AdminRepository.remove_admin(session, user_id)
        if not success:
            return False, "Ошибка: не удалось удалить администратора"
        
        # Логируем
        try:
            performer = await AdminRepository.get_admin(session, removed_by)
            performer_name = performer.username if performer and performer.username else str(removed_by)
            await LogRepository.add(session, Log(
                event_type="admin_removed",
                user_id=user_id,
                message=f"Администратор @{admin.username or user_id} удален пользователем @{performer_name}"
            ))
        except Exception as e:
            print(f"Ошибка при логировании удаления админа: {e}")
        
        username_display = f"@{admin.username}" if admin.username else str(user_id)
        return True, f"✅ Администратор {username_display} удален"

async def change_admin_role(user_id: int, new_role: str, changed_by: int) -> tuple[bool, str]:
    """
    Изменить роль администратора.
    
    Returns:
        (success: bool, message: str)
    """
    async with get_async_session() as session:
        admin = await AdminRepository.get_admin(session, user_id)
        if not admin or not admin.is_active:
            return False, "Ошибка: пользователь не является администратором"
        
        old_role = admin.role
        success = await AdminRepository.update_admin_role(session, user_id, new_role)
        if not success:
            return False, "Ошибка: не удалось изменить роль"
        
        # Логируем
        try:
            performer = await AdminRepository.get_admin(session, changed_by)
            performer_name = performer.username if performer and performer.username else str(changed_by)
            await LogRepository.add(session, Log(
                event_type="admin_role_changed",
                user_id=user_id,
                message=f"Роль администратора @{admin.username or user_id} изменена с {old_role} на {new_role} пользователем @{performer_name}"
            ))
        except Exception as e:
            print(f"Ошибка при логировании изменения роли: {e}")
        
        username_display = f"@{admin.username}" if admin.username else str(user_id)
        return True, f"✅ Роль администратора {username_display} изменена с {old_role} на {new_role}"

async def get_all_admins() -> List:
    """Получить всех активных администраторов."""
    async with get_async_session() as session:
        return await AdminRepository.get_all_admins(session)

async def get_admin_info(user_id: int):
    """Получить информацию об администраторе."""
    async with get_async_session() as session:
        return await AdminRepository.get_admin(session, user_id)
