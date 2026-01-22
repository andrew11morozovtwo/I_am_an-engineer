"""
Админ-команды: /ban, /warn, /blacklist, /stats, /addadmin, /removeadmin, /admins, /myadmin, /setrole
Админ-панель: /admin - интерактивная панель управления
"""
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from app.config.settings import settings
from app.application.services.user_service import (
    ban_user, add_warn, get_user_by_id, get_user_warns_count, get_user_ban, register_user
)
from app.application.services.moderation_service import (
    add_to_blacklist, remove_from_blacklist, get_all_blacklist
)
from app.application.services.stats_service import get_stats
from app.application.services.admin_service import (
    is_admin, check_admin_permission, get_admin_role, can_add_admin, can_remove_admin,
    can_change_role, add_admin, remove_admin, change_admin_role, get_all_admins, get_admin_info
)
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import LogRepository
from app.infrastructure.db.models import Log
import datetime
from typing import Optional

admin_router = Router()


# ============================================================================
# CALLBACK DATA для админ-панели
# ============================================================================

class AdminPanelCallback(CallbackData, prefix="admin"):
    """Callback data для навигации по админ-панели"""
    action: str
    page: Optional[int] = None
    user_id: Optional[int] = None
    item_id: Optional[int] = None


# ============================================================================
# КЛАВИАТУРЫ АДМИН-ПАНЕЛИ
# ============================================================================

def get_main_admin_panel_keyboard(admin_role: str = None) -> InlineKeyboardMarkup:
    """Главное меню админ-панели с учетом роли"""
    buttons = [
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data=AdminPanelCallback(action="users_menu").pack()),
            InlineKeyboardButton(text="🚫 Blacklist", callback_data=AdminPanelCallback(action="blacklist_menu").pack())
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data=AdminPanelCallback(action="stats").pack()),
        ],
        [
            InlineKeyboardButton(text="📝 Логи", callback_data=AdminPanelCallback(action="logs_menu").pack()),
            InlineKeyboardButton(text="ℹ️ О себе", callback_data=AdminPanelCallback(action="my_info").pack())
        ],
    ]
    
    # Раздел "Администраторы" доступен только senior_admin и owner
    if admin_role in ["senior_admin", "owner"]:
        buttons.insert(2, [
            InlineKeyboardButton(text="👮 Администраторы", callback_data=AdminPanelCallback(action="admins_menu").pack())
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=AdminPanelCallback(action="main").pack())
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_users_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления пользователями"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Найти пользователя", callback_data=AdminPanelCallback(action="find_user").pack()),
        ],
        [
            InlineKeyboardButton(text="❌ Забанить", callback_data=AdminPanelCallback(action="ban_user_input").pack()),
            InlineKeyboardButton(text="⚠️ Выдать варн", callback_data=AdminPanelCallback(action="warn_user_input").pack())
        ],
        [
            InlineKeyboardButton(text="📋 Список забаненных", callback_data=AdminPanelCallback(action="banned_list", page=1).pack()),
            InlineKeyboardButton(text="📋 Список с варнами", callback_data=AdminPanelCallback(action="warned_list", page=1).pack())
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminPanelCallback(action="main").pack())
        ]
    ])
    return keyboard


def get_blacklist_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления blacklist"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить фразу", callback_data=AdminPanelCallback(action="blacklist_add_input").pack()),
            InlineKeyboardButton(text="➖ Удалить фразу", callback_data=AdminPanelCallback(action="blacklist_remove_input").pack())
        ],
        [
            InlineKeyboardButton(text="📋 Список фраз", callback_data=AdminPanelCallback(action="blacklist_list", page=1).pack())
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminPanelCallback(action="main").pack())
        ]
    ])
    return keyboard


def get_admins_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления администраторами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить админа", callback_data=AdminPanelCallback(action="admin_add_input").pack()),
            InlineKeyboardButton(text="➖ Удалить админа", callback_data=AdminPanelCallback(action="admin_remove_input").pack())
        ],
        [
            InlineKeyboardButton(text="🔄 Изменить роль", callback_data=AdminPanelCallback(action="admin_setrole_input").pack()),
            InlineKeyboardButton(text="📋 Список админов", callback_data=AdminPanelCallback(action="admins_list").pack())
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminPanelCallback(action="main").pack())
        ]
    ])
    return keyboard


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Кнопка "Назад в главное меню" """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data=AdminPanelCallback(action="main").pack())]
    ])
    return keyboard

@admin_router.message(Command("ban"))
async def ban_command_handler(message: types.Message, command: CommandObject, bot: Bot):
    """Команда /ban {user_id} {reason}"""
    if not await is_admin(message.from_user.id):
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
        
        # Баним пользователя (бессрочный бан по умолчанию)
        ban = await ban_user(target_user_id, reason=reason, admin_id=message.from_user.id)
        
        # Получаем информацию о пользователе для красивого сообщения
        user = await get_user_by_id(target_user_id)
        username = f"@{user.username}" if user and user.username else str(target_user_id)
        
        # Отправляем уведомление администратору
        admin_notification = f"❌ Пользователь {username} заблокирован. Причина: {reason}"
        await message.answer(admin_notification)
        
        # Отправляем уведомление нарушителю о бане
        try:
            if ban.until:
                # Бан с датой окончания
                until_date = ban.until.strftime("%d.%m.%Y %H:%M")
                ban_notification = (
                    f"❌ <b>Вы были заблокированы</b>\n\n"
                    f"Причина: {reason}\n\n"
                    f"Блокировка будет автоматически снята: {until_date} UTC"
                )
            else:
                # Бессрочный бан
                ban_notification = (
                    f"❌ <b>Вы были заблокированы</b>\n\n"
                    f"Причина: {reason}\n\n"
                    f"<i>Блокировка бессрочная.</i>"
                )
            await bot.send_message(chat_id=target_user_id, text=ban_notification, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка при отправке уведомления о бане пользователю {target_user_id}: {e}")
        
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
    if not await is_admin(message.from_user.id):
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
        
        # Отправляем уведомление администратору
        admin_notification = f"⚠️ Предупреждение {username} (причина: {reason}). Варнов: {warn_count}/3"
        
        # Если 3+ варнов → автоматический бан на 24 часа
        if warn_count >= 3:
            await ban_user(target_user_id, reason="Автоматический бан за 3+ варнов", days=1, admin_id=message.from_user.id)
            admin_notification += f"\n❌ Пользователь автоматически забанен на 24 часа за превышение лимита варнов."
            await message.answer(admin_notification)
            
            # Отправляем уведомление нарушителю о бане
            try:
                ban_notification = (
                    f"❌ <b>Вы были заблокированы на 24 часа</b>\n\n"
                    f"Причина: Автоматический бан за превышение лимита предупреждений (3/3)\n\n"
                    f"⚠️ Количество предупреждений: {warn_count}/3\n"
                    f"📝 Последнее предупреждение: {reason}\n\n"
                    f"Бан будет автоматически снят через 24 часа."
                )
                await bot.send_message(chat_id=target_user_id, text=ban_notification, parse_mode="HTML")
            except Exception as e:
                print(f"Ошибка при отправке уведомления о бане пользователю {target_user_id}: {e}")
        else:
            await message.answer(admin_notification)
            
            # Отправляем уведомление нарушителю о предупреждении
            try:
                warn_notification = (
                    f"⚠️ <b>Вам выдано предупреждение</b>\n\n"
                    f"Причина: {reason}\n"
                    f"Текущее количество предупреждений: {warn_count}/3\n\n"
                    f"<i>При получении 3 предупреждений вы будете автоматически заблокированы на 24 часа.</i>"
                )
                await bot.send_message(chat_id=target_user_id, text=warn_notification, parse_mode="HTML")
            except Exception as e:
                print(f"Ошибка при отправке уведомления о предупреждении пользователю {target_user_id}: {e}")
        
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Должно быть число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")

@admin_router.message(Command("blacklist"))
async def blacklist_command_handler(message: types.Message, command: CommandObject):
    """Команда /blacklist {add|remove|list} {phrase}"""
    if not await is_admin(message.from_user.id):
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
    if not await is_admin(message.from_user.id):
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

@admin_router.message(Command("addadmin"))
async def add_admin_handler(message: types.Message, command: CommandObject, bot: Bot):
    """
    Добавить нового администратора.
    Синтаксис: /addadmin {user_id} {role}
    
    Роли: moderator, senior_admin, owner
    Только owner может добавлять senior_admin и owner.
    Только senior_admin и owner могут добавлять moderator.
    """
    # Проверяем права доступа
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    args = command.args
    if not args:
        help_text = (
            "❌ <b>Использование:</b> /addadmin {user_id} {роль}\n\n"
            "📋 <b>Доступные роли:</b>\n"
            "• <code>moderator</code> - Модератор (базовые права)\n"
            "• <code>senior_admin</code> - Старший администратор\n"
            "• <code>owner</code> - Владелец (главный администратор)\n\n"
            "💡 <i>Чтобы узнать user_id пользователя, попросите его написать /myid в боте</i>\n\n"
            "📝 <b>Пример:</b> <code>/addadmin 123456789 moderator</code>"
        )
        await message.answer(help_text, parse_mode="HTML")
        return
    
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        help_text = (
            "❌ <b>Использование:</b> /addadmin {user_id} {роль}\n\n"
            "📋 <b>Доступные роли:</b>\n"
            "• <code>moderator</code> - Модератор (базовые права)\n"
            "• <code>senior_admin</code> - Старший администратор\n"
            "• <code>owner</code> - Владелец (главный администратор)\n\n"
            "💡 <i>Чтобы узнать user_id пользователя, попросите его написать /myid в боте</i>\n\n"
            "📝 <b>Пример:</b> <code>/addadmin 123456789 moderator</code>"
        )
        await message.answer(help_text, parse_mode="HTML")
        return
    
    try:
        target_user_id = int(parts[0])
        role = parts[1].lower().strip()
        
        # Валидация роли
        valid_roles = ["moderator", "senior_admin", "owner"]
        if role not in valid_roles:
            help_text = (
                f"❌ Неверная роль: <code>{role}</code>\n\n"
                "📋 <b>Доступные роли:</b>\n"
                "• <code>moderator</code> - Модератор (базовые права)\n"
                "• <code>senior_admin</code> - Старший администратор\n"
                "• <code>owner</code> - Владелец (главный администратор)\n\n"
                "📝 <b>Пример:</b> <code>/addadmin 123456789 moderator</code>"
            )
            await message.answer(help_text, parse_mode="HTML")
            return
        
        # Проверяем права на добавление
        if not await can_add_admin(message.from_user.id, role):
            await message.answer("❌ Недостаточно прав для добавления админа этой роли.")
            return
        
        # Регистрируем пользователя, если его нет
        try:
            await register_user(
                target_user_id,
                username=None,  # Будет обновлено позже
                full_name=None
            )
        except Exception as e:
            print(f"Ошибка при регистрации пользователя: {e}")
        
        # Получаем информацию о пользователе
        user = await get_user_by_id(target_user_id)
        
        # Добавляем администратора
        success, result_message = await add_admin(
            user_id=target_user_id,
            role=role,
            added_by=message.from_user.id,
            username=user.username if user else None,
            full_name=user.full_name if user else None
        )
        
        if success:
            await message.answer(result_message)
            
            # Отправляем уведомление новому админу в ЛС
            try:
                performer = await get_user_by_id(message.from_user.id)
                performer_name = performer.full_name or (f"@{performer.username}" if performer and performer.username else "Администратор")
                
                notification = (
                    "🎉 **Вы добавлены как администратор бота!**\n\n"
                    f"Ваша роль: {role}\n"
                    f"Добавлен: {datetime.datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC\n"
                    f"Добавил: {performer_name}\n\n"
                    "📚 **Доступные команды:**\n"
                    "/ban {user_id} {reason} — Заблокировать пользователя\n"
                    "/warn {user_id} {reason} — Выдать предупреждение\n"
                    "/blacklist add {phrase} — Добавить фразу в чёрный список\n"
                    "/stats — Показать статистику\n\n"
                    "ℹ️ Для помощи напишите /help"
                )
                await bot.send_message(chat_id=target_user_id, text=notification)
            except Exception as e:
                print(f"Ошибка при отправке уведомления новому админу: {e}")
        else:
            await message.answer(result_message)
    
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Должно быть число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")
        import traceback
        traceback.print_exc()

@admin_router.message(Command("removeadmin"))
async def remove_admin_handler(message: types.Message, command: CommandObject, bot: Bot):
    """
    Удалить администратора из системы.
    Синтаксис: /removeadmin {user_id}
    
    Правила:
    - owner может удалять всех
    - senior_admin может удалять moderator
    - moderator не может никого удалять
    - owner (главный) не может быть удалён
    """
    # Проверяем права доступа
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    args = command.args
    if not args:
        await message.answer("❌ Использование: /removeadmin {user_id}")
        return
    
    try:
        target_user_id = int(args.strip())
        
        # Проверяем права на удаление
        can_remove, error_message = await can_remove_admin(message.from_user.id, target_user_id)
        if not can_remove:
            await message.answer(error_message)
            return
        
        # Удаляем администратора
        success, result_message = await remove_admin(target_user_id, message.from_user.id)
        
        if success:
            await message.answer(result_message)
            
            # Отправляем уведомление удаляемому админу
            try:
                notification = (
                    "⚠️ **Вы удалены из списка администраторов бота.**\n\n"
                    "Ваши права администратора были отозваны."
                )
                await bot.send_message(chat_id=target_user_id, text=notification)
            except Exception as e:
                print(f"Ошибка при отправке уведомления удаляемому админу: {e}")
        else:
            await message.answer(result_message)
    
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Должно быть число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")
        import traceback
        traceback.print_exc()

@admin_router.message(Command("admins"))
async def list_admins_handler(message: types.Message):
    """
    Показать список всех администраторов.
    """
    # Проверяем права доступа
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    try:
        admins = await get_all_admins()
        
        if not admins:
            await message.answer("👮 Список администраторов пуст.")
            return
        
        # Группируем по ролям
        owners = [a for a in admins if a.role == "owner"]
        senior_admins = [a for a in admins if a.role == "senior_admin"]
        moderators = [a for a in admins if a.role == "moderator"]
        
        text = "👮 <b>Список администраторов:</b>\n\n"
        text += "💡 <i>Используйте user_id для команд /addadmin, /removeadmin, /setrole</i>\n\n"
        
        if owners:
            text += "👑 <b>Owner:</b>\n"
            for admin in owners:
                username_display = f"@{admin.username}" if admin.username else f"ID {admin.user_id}"
                full_name_display = f" — {admin.full_name}" if admin.full_name else ""
                text += f"• {username_display} <code>(user_id: {admin.user_id})</code>{full_name_display}\n"
            text += "\n"
        
        if senior_admins:
            text += "🔐 <b>Senior Admin:</b>\n"
            for admin in senior_admins:
                username_display = f"@{admin.username}" if admin.username else f"ID {admin.user_id}"
                full_name_display = f" — {admin.full_name}" if admin.full_name else ""
                text += f"• {username_display} <code>(user_id: {admin.user_id})</code>{full_name_display}\n"
            text += "\n"
        
        if moderators:
            text += "🟢 <b>Moderator:</b>\n"
            for admin in moderators:
                username_display = f"@{admin.username}" if admin.username else f"ID {admin.user_id}"
                full_name_display = f" — {admin.full_name}" if admin.full_name else ""
                text += f"• {username_display} <code>(user_id: {admin.user_id})</code>{full_name_display}\n"
        
        text += f"\n<b>Всего: {len(admins)} администратор(ов)</b>"
        
        await message.answer(text, parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении списка администраторов: {e}")
        import traceback
        traceback.print_exc()

@admin_router.message(Command("myadmin"))
async def my_admin_info_handler(message: types.Message):
    """
    Показать информацию о себе как администраторе.
    """
    try:
        admin_info = await get_admin_info(message.from_user.id)
        
        if not admin_info or not admin_info.is_active:
            await message.answer("❌ Вы не являетесь администратором.")
            return
        
        role_display = {
            "owner": "👑 Owner",
            "senior_admin": "🔐 Senior Admin",
            "moderator": "🟢 Moderator"
        }
        
        text = "👮 <b>Ваша информация как администратора:</b>\n\n"
        text += f"🆔 User ID: {admin_info.user_id}\n"
        username_display = f"@{admin_info.username}" if admin_info.username else "не указан"
        text += f"👤 Username: {username_display}\n"
        full_name_display = admin_info.full_name if admin_info.full_name else "не указано"
        text += f"📝 Имя: {full_name_display}\n"
        text += f"🎭 Роль: {role_display.get(admin_info.role, admin_info.role)}\n"
        text += f"📅 Добавлен: {admin_info.created_at.strftime('%d.%m.%Y %H:%M')} UTC\n"
        
        if admin_info.added_by:
            added_by_user = await get_user_by_id(admin_info.added_by)
            if added_by_user:
                added_by_name = added_by_user.full_name or (f"@{added_by_user.username}" if added_by_user.username else str(admin_info.added_by))
            else:
                added_by_name = str(admin_info.added_by)
            text += f"👤 Добавил: {added_by_name}\n"
        
        text += f"🔄 Обновлено: {admin_info.updated_at.strftime('%d.%m.%Y %H:%M')} UTC"
        
        await message.answer(text, parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении информации: {e}")
        import traceback
        traceback.print_exc()

@admin_router.message(Command("setrole"))
async def set_admin_role_handler(message: types.Message, command: CommandObject):
    """
    Изменить роль администратора.
    Синтаксис: /setrole {user_id} {new_role}
    
    Только owner может менять роли senior_admin и owner.
    Только senior_admin и owner могут менять роли moderator.
    """
    # Проверяем права доступа
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    args = command.args
    if not args:
        help_text = (
            "❌ <b>Использование:</b> /setrole {user_id} {новая_роль}\n\n"
            "📋 <b>Доступные роли:</b>\n"
            "• <code>moderator</code> - Модератор\n"
            "• <code>senior_admin</code> - Старший администратор\n"
            "• <code>owner</code> - Владелец\n\n"
            "📝 <b>Пример:</b> <code>/setrole 123456789 senior_admin</code>"
        )
        await message.answer(help_text, parse_mode="HTML")
        return
    
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        help_text = (
            "❌ <b>Использование:</b> /setrole {user_id} {новая_роль}\n\n"
            "📋 <b>Доступные роли:</b>\n"
            "• <code>moderator</code> - Модератор\n"
            "• <code>senior_admin</code> - Старший администратор\n"
            "• <code>owner</code> - Владелец\n\n"
            "📝 <b>Пример:</b> <code>/setrole 123456789 senior_admin</code>"
        )
        await message.answer(help_text, parse_mode="HTML")
        return
    
    try:
        target_user_id = int(parts[0])
        new_role = parts[1].lower().strip()
        
        # Валидация роли
        valid_roles = ["moderator", "senior_admin", "owner"]
        if new_role not in valid_roles:
            help_text = (
                f"❌ Неверная роль: <code>{new_role}</code>\n\n"
                "📋 <b>Доступные роли:</b>\n"
                "• <code>moderator</code> - Модератор\n"
                "• <code>senior_admin</code> - Старший администратор\n"
                "• <code>owner</code> - Владелец\n\n"
                "📝 <b>Пример:</b> <code>/setrole 123456789 senior_admin</code>"
            )
            await message.answer(help_text, parse_mode="HTML")
            return
        
        # Получаем текущую роль
        async with get_async_session() as session:
            from app.infrastructure.db.repositories import AdminRepository
            target_admin = await AdminRepository.get_admin(session, target_user_id)
            if not target_admin or not target_admin.is_active:
                await message.answer("❌ Пользователь не является администратором.")
                return
            
            target_role = target_admin.role
        
        # Проверяем права на изменение роли
        if not await can_change_role(message.from_user.id, target_role, new_role):
            await message.answer("❌ Недостаточно прав для изменения роли администратора.")
            return
        
        # Изменяем роль
        success, result_message = await change_admin_role(target_user_id, new_role, message.from_user.id)
        await message.answer(result_message)
    
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Должно быть число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")
        import traceback
        traceback.print_exc()
# ============================================================================
# АДМИН-ПАНЕЛЬ: Команда /admin
# ============================================================================

@admin_router.message(Command("admin"))
async def admin_panel_handler(message: types.Message):
    """Команда /admin - открывает интерактивную админ-панель"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Эта команда доступна только администраторам.")
        return
    
    try:
        admin_info = await get_admin_info(message.from_user.id)
        role_display = {
            "owner": "👑 Owner",
            "senior_admin": "🔐 Senior Admin",
            "moderator": "🟢 Moderator"
        }
        role = role_display.get(admin_info.role, admin_info.role) if admin_info else "Неизвестно"
        
        text = (
            f"👮 <b>Админ-панель</b>\n\n"
            f"👤 Ваша роль: {role}\n"
            f"🆔 User ID: {message.from_user.id}\n\n"
            f"Выберите раздел для управления:"
        )
        
        await message.answer(text, parse_mode="HTML", reply_markup=get_main_admin_panel_keyboard())
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при открытии админ-панели: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# АДМИН-ПАНЕЛЬ: Callback handlers
# ============================================================================

@admin_router.callback_query(AdminPanelCallback.filter())
async def admin_panel_callback_handler(callback: types.CallbackQuery, callback_data: AdminPanelCallback, bot: Bot):
    """Обработчик всех callback от админ-панели"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    action = callback_data.action
    
    try:
        if action == "main":
            # Главное меню
            admin_info = await get_admin_info(callback.from_user.id)
            role_display = {
                "owner": "👑 Owner",
                "senior_admin": "🔐 Senior Admin",
                "moderator": "🟢 Moderator"
            }
            role = role_display.get(admin_info.role, admin_info.role) if admin_info else "Неизвестно"
            
            text = (
                f"👮 <b>Админ-панель</b>\n\n"
                f"👤 Ваша роль: {role}\n"
                f"🆔 User ID: {callback.from_user.id}\n\n"
                f"Выберите раздел для управления:"
            )
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_admin_panel_keyboard())
            await callback.answer()
        
        elif action == "users_menu":
            # Меню пользователей
            text = (
                "👥 <b>Управление пользователями</b>\n\n"
                "Выберите действие:"
            )
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_users_menu_keyboard())
            await callback.answer()
        
        elif action == "blacklist_menu":
            # Меню blacklist
            blacklist = await get_all_blacklist()
            text = (
                f"🚫 <b>Управление Blacklist</b>\n\n"
                f"📊 Всего фраз в списке: {len(blacklist)}\n\n"
                "Выберите действие:"
            )
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_blacklist_menu_keyboard())
            await callback.answer()
        
        elif action == "admins_menu":
            # Меню администраторов
            admins = await get_all_admins()
            text = (
                f"👮 <b>Управление администраторами</b>\n\n"
                f"📊 Всего администраторов: {len(admins)}\n\n"
                "Выберите действие:"
            )
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admins_menu_keyboard())
            await callback.answer()
        
        elif action == "stats":
            # Статистика
            stats = await get_stats()
            text = (
                "📊 <b>Статистика бота</b>\n\n"
                f"👥 Всего пользователей: {stats['total_users']}\n"
                f"✅ Активных за 7 дней: {stats['active_users']}\n"
                f"❌ Забаненных: {stats['banned_users']}\n"
                f"⚠️ Варнов за 7 дней: {stats['warns_recent']}\n"
                f"🚫 Размер blacklist: {stats['blacklist_size']}\n\n"
                f"📝 <b>Последние 5 действий:</b>\n"
            )
            
            for log in stats['recent_logs']:
                log_time = log.created_at.strftime("%d.%m.%Y %H:%M")
                log_msg = (log.message or 'без сообщения')[:50]
                text += f"• {log_time} | {log.event_type} | {log_msg}\n"
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_to_main_keyboard())
            await callback.answer()
        
        elif action == "my_info":
            # Информация о себе
            admin_info = await get_admin_info(callback.from_user.id)
            if not admin_info or not admin_info.is_active:
                await callback.answer("❌ Вы не являетесь администратором", show_alert=True)
                return
            
            role_display = {
                "owner": "👑 Owner",
                "senior_admin": "🔐 Senior Admin",
                "moderator": "🟢 Moderator"
            }
            
            text = (
                "👮 <b>Ваша информация как администратора:</b>\n\n"
                f"🆔 User ID: {admin_info.user_id}\n"
            )
            username_display = f"@{admin_info.username}" if admin_info.username else "не указан"
            text += f"👤 Username: {username_display}\n"
            full_name_display = admin_info.full_name if admin_info.full_name else "не указано"
            text += f"📝 Имя: {full_name_display}\n"
            text += f"🎭 Роль: {role_display.get(admin_info.role, admin_info.role)}\n"
            text += f"📅 Добавлен: {admin_info.created_at.strftime('%d.%m.%Y %H:%M')} UTC\n"
            
            if admin_info.added_by:
                added_by_user = await get_user_by_id(admin_info.added_by)
                if added_by_user:
                    added_by_name = added_by_user.full_name or (f"@{added_by_user.username}" if added_by_user.username else str(admin_info.added_by))
                else:
                    added_by_name = str(admin_info.added_by)
                text += f"👤 Добавил: {added_by_name}\n"
            
            text += f"🔄 Обновлено: {admin_info.updated_at.strftime('%d.%m.%Y %H:%M')} UTC"
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_to_main_keyboard())
            await callback.answer()
        
        elif action == "blacklist_list":
            # Список blacklist
            page = callback_data.page or 1
            blacklist = await get_all_blacklist()
            
            if not blacklist:
                text = "📋 Черный список пуст"
                await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard())
                await callback.answer()
                return
            
            items_per_page = 10
            total_pages = (len(blacklist) + items_per_page - 1) // items_per_page
            page = max(1, min(page, total_pages))
            
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_items = blacklist[start_idx:end_idx]
            
            text = f"📋 <b>Черный список</b> (страница {page}/{total_pages}, всего: {len(blacklist)}):\n\n"
            for i, item in enumerate(page_items, start=start_idx + 1):
                text += f"{i}. {item.phrase}\n"
            
            # Кнопки навигации
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=AdminPanelCallback(action="blacklist_list", page=page-1).pack()))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=AdminPanelCallback(action="blacklist_list", page=page+1).pack()))
            
            keyboard_buttons = [nav_buttons] if nav_buttons else []
            keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminPanelCallback(action="blacklist_menu").pack())])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback.answer()
        
        elif action == "admins_list":
            # Список администраторов
            admins = await get_all_admins()
            
            if not admins:
                text = "👮 Список администраторов пуст."
                await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard())
                await callback.answer()
                return
            
            # Группируем по ролям
            owners = [a for a in admins if a.role == "owner"]
            senior_admins = [a for a in admins if a.role == "senior_admin"]
            moderators = [a for a in admins if a.role == "moderator"]
            
            text = "👮 <b>Список администраторов:</b>\n\n"
            text += "💡 <i>Используйте user_id для команд /addadmin, /removeadmin, /setrole</i>\n\n"
            
            if owners:
                text += "👑 <b>Owner:</b>\n"
                for admin in owners:
                    username_display = f"@{admin.username}" if admin.username else f"ID {admin.user_id}"
                    full_name_display = f" — {admin.full_name}" if admin.full_name else ""
                    text += f"• {username_display} <code>(user_id: {admin.user_id})</code>{full_name_display}\n"
                text += "\n"
            
            if senior_admins:
                text += "🔐 <b>Senior Admin:</b>\n"
                for admin in senior_admins:
                    username_display = f"@{admin.username}" if admin.username else f"ID {admin.user_id}"
                    full_name_display = f" — {admin.full_name}" if admin.full_name else ""
                    text += f"• {username_display} <code>(user_id: {admin.user_id})</code>{full_name_display}\n"
                text += "\n"
            
            if moderators:
                text += "🟢 <b>Moderator:</b>\n"
                for admin in moderators:
                    username_display = f"@{admin.username}" if admin.username else f"ID {admin.user_id}"
                    full_name_display = f" — {admin.full_name}" if admin.full_name else ""
                    text += f"• {username_display} <code>(user_id: {admin.user_id})</code>{full_name_display}\n"
            
            text += f"\n<b>Всего: {len(admins)} администратор(ов)</b>"
            
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_to_main_keyboard())
            await callback.answer()
        
        elif action in ["ban_user_input", "warn_user_input", "blacklist_add_input", "blacklist_remove_input", 
                        "admin_add_input", "admin_remove_input", "admin_setrole_input", "find_user"]:
            # Действия, требующие ввода данных - отправляем инструкцию
            action_messages = {
                "ban_user_input": "❌ <b>Забанить пользователя</b>\n\nИспользуйте команду:\n<code>/ban {user_id} {причина}</code>\n\nИли вернитесь в меню.",
                "warn_user_input": "⚠️ <b>Выдать варн</b>\n\nИспользуйте команду:\n<code>/warn {user_id} {причина}</code>\n\nИли вернитесь в меню.",
                "blacklist_add_input": "➕ <b>Добавить фразу в blacklist</b>\n\nИспользуйте команду:\n<code>/blacklist add {фраза}</code>\n\nИли вернитесь в меню.",
                "blacklist_remove_input": "➖ <b>Удалить фразу из blacklist</b>\n\nИспользуйте команду:\n<code>/blacklist remove {фраза}</code>\n\nИли вернитесь в меню.",
                "admin_add_input": "➕ <b>Добавить администратора</b>\n\nИспользуйте команду:\n<code>/addadmin {user_id} {роль}</code>\n\nРоли: moderator, senior_admin, owner\n\nИли вернитесь в меню.",
                "admin_remove_input": "➖ <b>Удалить администратора</b>\n\nИспользуйте команду:\n<code>/removeadmin {user_id}</code>\n\nИли вернитесь в меню.",
                "admin_setrole_input": "🔄 <b>Изменить роль администратора</b>\n\nИспользуйте команду:\n<code>/setrole {user_id} {новая_роль}</code>\n\nРоли: moderator, senior_admin, owner\n\nИли вернитесь в меню.",
                "find_user": "🔍 <b>Найти пользователя</b>\n\nИспользуйте команду:\n<code>/userinfo {user_id}</code>\n\nИли вернитесь в меню."
            }
            
            text = action_messages.get(action, "Используйте команды из меню /help")
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_to_main_keyboard())
            await callback.answer()
        
        elif action == "logs_menu":
            # Меню логов
            text = (
                "📝 <b>Просмотр логов</b>\n\n"
                "Для просмотра логов используйте скрипт:\n"
                "<code>python -m app.scripts.view_logs</code>\n\n"
                "Или вернитесь в меню."
            )
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_to_main_keyboard())
            await callback.answer()
        
        else:
            await callback.answer("❌ Неизвестное действие", show_alert=True)
    
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
        import traceback
        traceback.print_exc()