"""
Entry point for the AdminBot project.
"""
import asyncio
from aiogram import Bot, Dispatcher
from app.config.settings import settings
from app.presentation.routers.user_router import user_router
from app.presentation.routers.admin_router import admin_router
from app.presentation.routers.channel_router import channel_router
from app.infrastructure.db.session import async_init_db
from app.application.services.user_service import unban_expired_users

async def check_expired_bans_periodically():
    """Фоновая задача для периодической проверки и снятия истекших банов"""
    while True:
        try:
            # Проверяем и снимаем истекшие баны каждые 5 минут
            await asyncio.sleep(300)  # 5 минут = 300 секунд
            unban_count = await unban_expired_users()
            if unban_count > 0:
                print(f"✅ Автоматически снято банов: {unban_count}")
        except Exception as e:
            print(f"⚠️ Ошибка при проверке истекших банов: {e}")
            import traceback
            traceback.print_exc()
            # Ждем перед следующей попыткой даже при ошибке
            await asyncio.sleep(60)  # 1 минута при ошибке

async def main():
    # Инициализируем БД при старте
    await async_init_db()
    
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Register routers (важен порядок - команды обрабатываются первыми)
    dp.include_router(admin_router)  # Админ-команды
    dp.include_router(user_router)   # Пользовательские команды (/start, /help)
    dp.include_router(channel_router)  # Обработка сообщений из канала (в последнюю очередь)

    # Надежно удаляем вебхук (если был установлен), чтобы использовать polling
    print("🔄 Проверяем статус вебхука...")
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                print(f"⚠️  Обнаружен вебхук: {webhook_info.url} (попытка {attempt + 1}/{max_attempts})")
                await bot.delete_webhook(drop_pending_updates=True)
                # Ждем, чтобы Telegram успел обработать удаление
                await asyncio.sleep(2)
                # Проверяем, что вебхук действительно удален
                webhook_info_after = await bot.get_webhook_info()
                if not webhook_info_after.url:
                    print("✅ Вебхук успешно удален")
                    break
                else:
                    print(f"⚠️  Вебхук все еще активен, повторная попытка...")
                    if attempt == max_attempts - 1:
                        print("❌ Не удалось удалить вебхук после нескольких попыток")
            else:
                print("✅ Вебхук не установлен, используем polling")
                break
        except Exception as e:
            print(f"⚠️  Ошибка при проверке/удалении вебхука (попытка {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(2)
            else:
                print("⚠️  Продолжаем запуск несмотря на ошибки...")

    print("Bot initialized. Ready to start polling.")
    
    # Даем время для завершения всех операций с вебхуком
    await asyncio.sleep(1)
    
    # Запускаем фоновую задачу для проверки истекших банов
    ban_check_task = None
    try:
        ban_check_task = asyncio.create_task(check_expired_bans_periodically())
        print("✅ Запущена фоновая задача для проверки истекших банов (каждые 5 минут)")
        
        await dp.start_polling(bot, drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\n⚠️  Получен сигнал остановки (Ctrl+C)...")
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске polling: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Отменяем фоновую задачу
        if ban_check_task:
            try:
                ban_check_task.cancel()
                await ban_check_task
                print("✅ Фоновая задача проверки банов остановлена")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"⚠️ Ошибка при остановке фоновой задачи: {e}")
        
        # Корректно закрываем сессию бота
        try:
            await bot.session.close()
            print("✅ Сессия бота закрыта")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
