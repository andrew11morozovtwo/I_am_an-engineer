"""
Entry point for the Telegram bot project.
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config.settings import settings
from app.presentation.routers.user_router import user_router
from app.presentation.routers.admin_router import admin_router
from app.presentation.routers.channel_router import channel_router
from app.infrastructure.db.session import async_init_db, get_async_session
from app.infrastructure.db.repositories import AdminRepository, LogRepository, PostCommentRepository
from app.application.services.user_service import unban_expired_users, register_user
from app.infrastructure.ai_clients import init_ai_clients
from app.application.services.comment_service import CommentService
from app.application.services import set_comment_service, set_ai_clients
from app.common.logger import setup_logging
from app.common.error_handler import handle_error, ErrorContext, ErrorSeverity

# Настраиваем логирование
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

async def check_expired_bans_periodically():
    """Фоновая задача для периодической проверки и снятия истекших банов"""
    while True:
        try:
            # Проверяем и снимаем истекшие баны каждый час
            await asyncio.sleep(3600)  # 1 час = 3600 секунд
            unban_count = await unban_expired_users()
            if unban_count > 0:
                logger.info(f"✅ Автоматически снято банов: {unban_count}")
        except asyncio.CancelledError:
            # Задача была отменена - это нормально при остановке бота
            break
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext(
                    operation="check_expired_bans_periodically",
                    severity=ErrorSeverity.MEDIUM
                )
            )
            # Ждем перед следующей попыткой даже при ошибке
            await asyncio.sleep(60)  # 1 минута при ошибке

async def cleanup_old_logs_periodically():
    """Фоновая задача для периодической очистки старых логов (для экономии места на диске)"""
    while True:
        try:
            # Очищаем логи каждые 24 часа
            await asyncio.sleep(86400)  # 24 часа = 86400 секунд
            
            async with get_async_session() as session:
                # Проверяем количество логов
                logs_count = await LogRepository.get_logs_count(session)
                
                # Если логов больше 10000, оставляем только последние 10000
                if logs_count > 10000:
                    deleted_count = await LogRepository.keep_recent_logs(session, max_logs=10000)
                    logger.info(f"🧹 Очищено старых логов: {deleted_count} (осталось 10000)")
                else:
                    # Иначе удаляем логи старше 30 дней
                    deleted_count = await LogRepository.delete_old_logs(session, days=30)
                    if deleted_count > 0:
                        logger.info(f"🧹 Удалено логов старше 30 дней: {deleted_count}")
        except asyncio.CancelledError:
            # Задача была отменена - это нормально при остановке бота
            break
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext(
                    operation="cleanup_old_logs_periodically",
                    severity=ErrorSeverity.MEDIUM
                )
            )
            # Ждем перед следующей попыткой даже при ошибке
            await asyncio.sleep(3600)  # 1 час при ошибке

async def cleanup_old_comments_periodically():
    """Фоновая задача для периодической очистки старых комментариев (старше 30 дней)"""
    while True:
        try:
            # Очищаем комментарии каждые 24 часа
            await asyncio.sleep(86400)  # 24 часа = 86400 секунд
            
            async with get_async_session() as session:
                deleted_count = await PostCommentRepository.delete_old_comments(session, days=30)
                if deleted_count > 0:
                    logger.info(f"🧹 Удалено комментариев старше 30 дней: {deleted_count}")
        except asyncio.CancelledError:
            # Задача была отменена - это нормально при остановке бота
            break
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext(
                    operation="cleanup_old_comments_periodically",
                    severity=ErrorSeverity.MEDIUM
                )
            )
            # Ждем перед следующей попыткой даже при ошибке
            await asyncio.sleep(3600)  # 1 час при ошибке

async def initialize_admins():
    """
    Загрузить начальных администраторов из .env в БД (если БД пуста).
    Это нужно для первого запуска.
    
    Первый администратор из ADMIN_IDS всегда получает роль "owner".
    Остальные администраторы получают роль "moderator".
    """
    async with get_async_session() as session:
        existing_admins = await AdminRepository.get_all_admins(session)
        
        if not existing_admins and settings.ADMIN_IDS:
            admin_ids = settings.ADMIN_IDS.split(",")
            logger.info("[ADMIN INIT] Начальная инициализация администраторов из .env...")
            
            # Получаем список валидных admin_id
            valid_admin_ids = []
            for admin_id_str in admin_ids:
                try:
                    admin_id = int(admin_id_str.strip())
                    if admin_id > 0:
                        valid_admin_ids.append(admin_id)
                except ValueError:
                    logger.warning(f"[ADMIN INIT] Пропущен неверный admin_id: {admin_id_str}")
            
            for idx, admin_id in enumerate(valid_admin_ids):
                try:
                    # Определяем роль:
                    # 1. Первый администратор из списка (idx == 0) всегда получает роль "owner"
                    # 2. Если это OWNER_ID - всегда "owner"
                    # 3. Иначе - "moderator"
                    if idx == 0:  # Первый администратор всегда owner
                        role = "owner"
                    elif admin_id == settings.OWNER_ID and settings.OWNER_ID > 0:
                        role = "owner"
                    else:
                        role = "moderator"
                    
                    # Регистрируем пользователя, если его нет
                    try:
                        await register_user(user_id=admin_id, username=None, full_name=None)
                    except Exception as e:
                        await handle_error(
                            error=e,
                            context=ErrorContext(
                                operation="initialize_admins.register_user",
                                user_id=admin_id,
                                severity=ErrorSeverity.LOW
                            )
                        )
                    
                    # Добавляем администратора
                    try:
                        await AdminRepository.add_admin(
                            session,
                            user_id=admin_id,
                            username=None,  # Будет обновлено при первом использовании
                            full_name=None,
                            role=role,
                            added_by=None  # Первичная инициализация
                        )
                        role_display = "👑 owner" if role == "owner" else "🟢 moderator"
                        logger.info(f"[ADMIN INIT] ✅ Администратор {admin_id} добавлен (роль: {role_display})")
                    except Exception as e:
                        await handle_error(
                            error=e,
                            context=ErrorContext(
                                operation="initialize_admins.add_admin",
                                user_id=admin_id,
                                severity=ErrorSeverity.MEDIUM
                            )
                        )
                except Exception as e:
                    await handle_error(
                        error=e,
                        context=ErrorContext(
                            operation="initialize_admins",
                            user_id=admin_id,
                            severity=ErrorSeverity.MEDIUM
                        )
                    )
            
            logger.info("[ADMIN INIT] Инициализация администраторов завершена.")

async def main():
    # Инициализируем БД при старте
    await async_init_db()
    
    # Инициализируем администраторов из .env (если БД пуста)
    await initialize_admins()
    
    # Инициализируем AI клиенты и сервис комментариев
    try:
        ai_clients = init_ai_clients()
        set_ai_clients(ai_clients)  # Сохраняем глобально
        comment_service = CommentService(ai_clients.openai)
        set_comment_service(comment_service)  # Сохраняем глобально
        logger.info("✅ AI клиенты и сервис комментариев инициализированы")
    except Exception as e:
        await handle_error(
            error=e,
            context=ErrorContext(
                operation="main.init_ai_clients",
                severity=ErrorSeverity.HIGH
            )
        )
        logger.warning("⚠️ Бот будет работать без AI функций (комментирование постов будет отключено)")
        comment_service = None
    
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Register routers (важен порядок - команды обрабатываются первыми)
    dp.include_router(admin_router)  # Админ-команды
    dp.include_router(user_router)   # Пользовательские команды (/start, /help)
    dp.include_router(channel_router)  # Обработка сообщений из канала (в последнюю очередь)

    # Надежно удаляем вебхук (если был установлен), чтобы использовать polling
    logger.info("🔄 Проверяем статус вебхука...")
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                logger.warning(f"⚠️  Обнаружен вебхук: {webhook_info.url} (попытка {attempt + 1}/{max_attempts})")
                await bot.delete_webhook(drop_pending_updates=True)
                # Ждем, чтобы Telegram успел обработать удаление
                await asyncio.sleep(2)
                # Проверяем, что вебхук действительно удален
                webhook_info_after = await bot.get_webhook_info()
                if not webhook_info_after.url:
                    logger.info("✅ Вебхук успешно удален")
                    break
                else:
                    logger.warning(f"⚠️  Вебхук все еще активен, повторная попытка...")
                    if attempt == max_attempts - 1:
                        logger.error("❌ Не удалось удалить вебхук после нескольких попыток")
            else:
                logger.info("✅ Вебхук не установлен, используем polling")
                break
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext(
                    operation="main.check_webhook",
                    additional_data={"attempt": attempt + 1, "max_attempts": max_attempts},
                    severity=ErrorSeverity.MEDIUM
                )
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(2)
            else:
                logger.warning("⚠️  Продолжаем запуск несмотря на ошибки...")

    logger.info("Bot initialized. Ready to start polling.")
    
    # Даем время для завершения всех операций с вебхуком
    await asyncio.sleep(1)
    
    # Запускаем фоновые задачи
    ban_check_task = None
    logs_cleanup_task = None
    comments_cleanup_task = None
    try:
        ban_check_task = asyncio.create_task(check_expired_bans_periodically())
        logger.info("✅ Запущена фоновая задача для проверки истекших банов (каждый час)")
        
        logs_cleanup_task = asyncio.create_task(cleanup_old_logs_periodically())
        logger.info("✅ Запущена фоновая задача для очистки старых логов (каждые 24 часа)")
        
        comments_cleanup_task = asyncio.create_task(cleanup_old_comments_periodically())
        logger.info("✅ Запущена фоновая задача для очистки старых комментариев (каждые 24 часа)")
        
        await dp.start_polling(bot, drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Получен сигнал остановки (Ctrl+C)...")
    except asyncio.CancelledError:
        # Нормальная ситуация при остановке
        logger.info("\n⚠️  Получен сигнал остановки...")
    except Exception as e:
        await handle_error(
            error=e,
            context=ErrorContext(
                operation="main.start_polling",
                severity=ErrorSeverity.CRITICAL
            )
        )
    finally:
        # Отменяем фоновые задачи
        if ban_check_task:
            try:
                ban_check_task.cancel()
                try:
                    await ban_check_task
                except asyncio.CancelledError:
                    pass  # Нормально - задача отменена
                logger.info("✅ Фоновая задача проверки банов остановлена")
            except Exception as e:
                await handle_error(
                    error=e,
                    context=ErrorContext(
                        operation="main.stop_ban_check_task",
                        severity=ErrorSeverity.LOW
                    )
                )
        
        if logs_cleanup_task:
            try:
                logs_cleanup_task.cancel()
                try:
                    await logs_cleanup_task
                except asyncio.CancelledError:
                    pass  # Нормально - задача отменена
                logger.info("✅ Фоновая задача очистки логов остановлена")
            except Exception as e:
                await handle_error(
                    error=e,
                    context=ErrorContext(
                        operation="main.stop_logs_cleanup_task",
                        severity=ErrorSeverity.LOW
                    )
                )
        
        if comments_cleanup_task:
            try:
                comments_cleanup_task.cancel()
                try:
                    await comments_cleanup_task
                except asyncio.CancelledError:
                    pass  # Нормально - задача отменена
                logger.info("✅ Фоновая задача очистки комментариев остановлена")
            except Exception as e:
                await handle_error(
                    error=e,
                    context=ErrorContext(
                        operation="main.stop_comments_cleanup_task",
                        severity=ErrorSeverity.LOW
                    )
                )
        
        # Корректно закрываем сессию бота
        try:
            await bot.session.close()
            logger.info("✅ Сессия бота закрыта")
        except Exception as e:
            await handle_error(
                error=e,
                context=ErrorContext(
                    operation="main.close_bot_session",
                    severity=ErrorSeverity.LOW
                )
            )

if __name__ == "__main__":
    asyncio.run(main())
