"""
Админ-команды: /ban, /warn, /blacklist, /stats
"""
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from app.config.settings import settings
from app.application.services.user_service import (
    ban_user, add_warn, get_user_by_id, get_user_warns_count, get_user_ban
)
from app.application.services.moderation_service import (
    add_to_blacklist, remove_from_blacklist, get_all_blacklist
)
from app.application.services.stats_service import get_stats
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import LogRepository
from app.infrastructure.db.models import Log

admin_router = Router()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in settings.get_admin_ids_list()

@admin_router.message(Command("ban"))
async def ban_command_handler(message: types.Message, command: CommandObject, bot: Bot):
    """Команда /ban {user_id} {reason}"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    args = command.args
    if not args:
        await message.answer("❌ Использование: /ban {user_id} {причина}")
        return
    
    parts = args.split(maxsplit=1)
    if len(parts) < 1:
        await message.answer("❌ Использование: /ban {user_id} {причина}")
        return
    
    try:
        target_user_id = int(parts[0])
        reason = parts[1] if len(parts) > 1 else "Нарушение правил"
        
        # Проверяем, не забанен ли уже
        existing_ban = await get_user_ban(target_user_id)
        if existing_ban:
            await message.answer(f"⚠️ Пользователь {target_user_id} уже забанен.")
            return
        
        # Баним пользователя
        ban = await ban_user(target_user_id, reason=reason, admin_id=message.from_user.id)
        
        # Получаем информацию о пользователе для красивого сообщения
        user = await get_user_by_id(target_user_id)
        username = f"@{user.username}" if user and user.username else str(target_user_id)
        
        # Отправляем уведомление
        notification = f"❌ Пользователь {username} заблокирован. Причина: {reason}"
        await message.answer(notification)
        
        # Пытаемся удалить сообщения пользователя из группы обсуждений (если есть)
        if message.chat.type in ("group", "supergroup"):
            try:
                # Можно добавить логику удаления всех сообщений пользователя
                pass
            except Exception as e:
                print(f"Ошибка при удалении сообщений: {e}")
        
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Должно быть число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")

@admin_router.message(Command("warn"))
async def warn_command_handler(message: types.Message, command: CommandObject, bot: Bot):
    """Команда /warn {user_id} {reason}"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    args = command.args
    if not args:
        await message.answer("❌ Использование: /warn {user_id} {причина}")
        return
    
    parts = args.split(maxsplit=1)
    if len(parts) < 1:
        await message.answer("❌ Использование: /warn {user_id} {причина}")
        return
    
    try:
        target_user_id = int(parts[0])
        reason = parts[1] if len(parts) > 1 else "Нарушение правил"
        
        # Добавляем варн
        warn = await add_warn(target_user_id, reason=reason, admin_id=message.from_user.id)
        
        # Получаем текущее количество варнов
        warn_count = await get_user_warns_count(target_user_id)
        user = await get_user_by_id(target_user_id)
        username = f"@{user.username}" if user and user.username else str(target_user_id)
        
        # Если 3+ варнов → автоматический бан на 24 часа
        if warn_count >= 3:
            await ban_user(target_user_id, reason="Автоматический бан за 3+ варнов", days=1, admin_id=message.from_user.id)
            await message.answer(
                f"⚠️ Предупреждение {username} (причина: {reason}). Варнов: {warn_count}/3\n"
                f"❌ Пользователь автоматически забанен на 24 часа за превышение лимита варнов."
            )
        else:
            await message.answer(
                f"⚠️ Предупреждение {username} (причина: {reason}). Варнов: {warn_count}/3"
            )
        
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Должно быть число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")

@admin_router.message(Command("blacklist"))
async def blacklist_command_handler(message: types.Message, command: CommandObject):
    """Команда /blacklist {add|remove|list} {phrase}"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    args = command.args
    if not args:
        await message.answer("❌ Использование:\n/blacklist add {фраза}\n/blacklist remove {фраза}\n/blacklist list")
        return
    
    parts = args.split(maxsplit=1)
    action = parts[0].lower()
    
    if action == "add":
        if len(parts) < 2:
            await message.answer("❌ Использование: /blacklist add {фраза}")
            return
        
        phrase = parts[1]
        success = await add_to_blacklist(phrase, admin_id=message.from_user.id)
        if success:
            await message.answer(f"✅ Фраза '{phrase}' добавлена в черный список")
        else:
            await message.answer(f"⚠️ Фраза '{phrase}' уже есть в черном списке")
    
    elif action == "remove":
        if len(parts) < 2:
            await message.answer("❌ Использование: /blacklist remove {фраза}")
            return
        
        phrase = parts[1]
        await remove_from_blacklist(phrase, admin_id=message.from_user.id)
        await message.answer(f"✅ Фраза '{phrase}' удалена из черного списка")
    
    elif action == "list":
        blacklist = await get_all_blacklist()
        if not blacklist:
            await message.answer("📋 Черный список пуст")
            return
        
        # Постраничный вывод (10 фраз на страницу)
        page = 0
        if len(parts) > 1:
            try:
                page = int(parts[1]) - 1
            except ValueError:
                page = 0
        
        items_per_page = 10
        total_pages = (len(blacklist) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages - 1))
        
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_items = blacklist[start_idx:end_idx]
        
        text = f"📋 Черный список (страница {page + 1}/{total_pages}, всего: {len(blacklist)}):\n\n"
        for i, item in enumerate(page_items, start=start_idx + 1):
            text += f"{i}. {item.phrase}\n"
        
        if total_pages > 1:
            text += f"\nИспользуйте: /blacklist list {page + 2} для следующей страницы"
        
        await message.answer(text)
    
    else:
        await message.answer("❌ Неизвестное действие. Используйте: add, remove или list")

@admin_router.message(Command("stats"))
async def stats_command_handler(message: types.Message):
    """Команда /stats - статистика бота"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    try:
        stats = await get_stats()
        
        text = "📊 Статистика бота:\n\n"
        text += f"👥 Всего пользователей: {stats['total_users']}\n"
        text += f"✅ Активных за 7 дней: {stats['active_users']}\n"
        text += f"❌ Забаненных: {stats['banned_users']}\n"
        text += f"⚠️ Варнов за 7 дней: {stats['warns_recent']}\n"
        text += f"🚫 Размер черного списка: {stats['blacklist_size']}\n\n"
        text += "📝 Последние 5 действий:\n"
        
        for log in stats['recent_logs']:
            log_time = log.created_at.strftime("%d.%m.%Y %H:%M")
            text += f"• {log_time} | {log.event_type} | {log.message or 'без сообщения'}\n"
        
        await message.answer(text)
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении статистики: {e}")
