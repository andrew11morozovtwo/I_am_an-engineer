"""
Handlers for user (public) commands: /start, /help, /faq etc.
"""
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.exceptions import TelegramNetworkError
from app.application.services.user_service import register_user, get_user_by_id
from app.config.settings import settings
import asyncio

user_router = Router()

@user_router.message(Command("start"))
async def start_handler(message: types.Message):
    """Команда /start - регистрация пользователя"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        
        # Проверяем, существует ли пользователь
        existing_user = await get_user_by_id(user_id)
        
        # Регистрируем или обновляем пользователя
        user = await register_user(
            user_id=user_id,
            username=username,
            full_name=full_name
        )
        
        # Формируем приветственное сообщение
        if not existing_user:
            # Новый пользователь
            greeting = "Привет! Ты зарегистрирован в системе 😊\n\n"
            greeting += "Используй /help для получения справки по командам."
        else:
            # Существующий пользователь
            greeting = "С возвращением! 👋\n\n"
            greeting += "Используй /help для получения справки по командам."
        
        await message.answer(greeting)
        
    except Exception as e:
        # Обработка ошибок
        error_message = f"❌ Произошла ошибка при регистрации. Попробуйте позже."
        print(f"Ошибка в команде /start для пользователя {message.from_user.id}: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(error_message)

@user_router.message(Command("help"))
async def help_handler(message: types.Message, bot: Bot):
    """Команда /help - справка по командам бота"""
    try:
        print(f"🔍 DEBUG: Обработчик /help вызван для пользователя {message.from_user.id}")
        # Проверяем, является ли пользователь администратором
        is_admin_user = message.from_user.id in settings.get_admin_ids_list()
        
        help_text = "📖 Справка по командам бота:\n\n"
        
        # Общие команды для всех пользователей
        help_text += "🔹 <b>Общие команды:</b>\n"
        help_text += "/start - Регистрация в системе\n"
        help_text += "/help - Показать эту справку\n\n"
        
        # Админ-команды (показываем только админам)
        if is_admin_user:
            help_text += "👑 <b>Админ-команды:</b>\n"
            help_text += "/ban {user_id} {причина} - Забанить пользователя\n"
            help_text += "/warn {user_id} {причина} - Выдать предупреждение (3 варна = бан)\n"
            help_text += "/blacklist add {фраза} - Добавить фразу в черный список\n"
            help_text += "/blacklist remove {фраза} - Удалить фразу из черного списка\n"
            help_text += "/blacklist list [страница] - Показать список запрещенных фраз\n"
            help_text += "/stats - Показать статистику бота\n\n"
        
        help_text += "ℹ️ <b>Примечание:</b>\n"
        help_text += "Бот автоматически модерирует сообщения:\n"
        help_text += "• Удаляет сообщения с запрещенными словами\n"
        help_text += "• Выдает предупреждения за нарушения\n"
        help_text += "• Автоматически банит при 3+ предупреждениях\n"
        
        # Пытаемся отправить сообщение с несколькими попытками при сетевых ошибках
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                await message.answer(help_text, parse_mode="HTML")
                print(f"✅ Сообщение /help успешно отправлено пользователю {message.from_user.id}")
                return
            except TelegramNetworkError as network_error:
                if attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 2  # Увеличиваем время ожидания: 2, 4, 6 секунд
                    print(f"⚠️ Сетевая ошибка при отправке /help (попытка {attempt + 1}/{max_attempts}): {network_error}. Повтор через {wait_time} сек...")
                    await asyncio.sleep(wait_time)
                else:
                    # Последняя попытка - пробуем через bot.send_message
                    try:
                        await bot.send_message(
                            chat_id=message.chat.id,
                            text=help_text,
                            parse_mode="HTML"
                        )
                        print(f"✅ Сообщение /help отправлено через bot.send_message пользователю {message.from_user.id}")
                        return
                    except Exception as e:
                        print(f"❌ Не удалось отправить /help через bot.send_message: {e}")
                        raise
            except Exception as e:
                print(f"❌ Неожиданная ошибка при отправке /help: {e}")
                raise
                
    except Exception as e:
        print(f"❌ Критическая ошибка в команде /help для пользователя {message.from_user.id}: {e}")
        import traceback
        traceback.print_exc()
        # Пытаемся отправить простое сообщение об ошибке
        try:
            await message.answer("❌ Произошла ошибка при обработке команды. Попробуйте позже.")
        except:
            pass  # Если и это не работает, просто пропускаем
