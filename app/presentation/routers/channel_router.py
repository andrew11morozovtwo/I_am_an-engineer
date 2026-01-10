"""
Обработка событий канала: новые посты, комментарии к постам (обсуждение).
С автоматической модерацией: проверка банов, варнов, blacklist
"""
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from app.application.services.moderation_service import check_message_for_blacklist
from app.application.services.user_service import get_user_ban, get_user_by_id, get_user_warns_count, ban_user, register_user
import asyncio

channel_router = Router()

@channel_router.channel_post()
async def new_channel_post_handler(message: types.Message, bot: Bot):
    """
    Обработчик новых постов в канале (Bot должен быть администратором).
    Отвечает первым комментарием к посту в связанной группе обсуждений.
    """
    # 1. Проверка на запрещёнку - удаляем пост (проверяем текст и подпись к медиа)
    post_text = (message.text or "") + " " + (message.caption or "")
    if await check_message_for_blacklist(post_text.strip()):
        try:
            await message.delete()
            print(f"✅ Пост {message.message_id} в канале удален из-за blacklist")
            # Логируем удаление
            from app.infrastructure.db.session import get_async_session
            from app.infrastructure.db.repositories import LogRepository
            from app.infrastructure.db.models import Log
            async with get_async_session() as session:
                await LogRepository.add(session, Log(
                    event_type="post_deleted",
                    message=f"Пост {message.message_id} удален из-за blacklist"
                ))
        except Exception as e:
            print(f"❌ Ошибка при удалении поста: {e}")
        return

    # 2. Оставить первый комментарий к посту в группе обсуждений
    try:
        chat = await bot.get_chat(message.chat.id)
        
        if hasattr(chat, 'linked_chat') and chat.linked_chat:
            linked_chat_id = chat.linked_chat.id
        elif hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
            linked_chat_id = chat.linked_chat_id
        else:
            return
        
        comment_text = f"Вижу новый пост - и первые 100 знаков этого поста: {message.text[:100] if message.text else ''}"
        await asyncio.sleep(2)
        
        try:
            sent_message = await bot.send_message(
                chat_id=linked_chat_id,
                text=comment_text,
                reply_to_message_id=message.message_id
            )
            print(f"✅ Комментарий отправлен к посту {message.message_id}")
        except Exception as send_error:
            print(f"⚠️ Ошибка при отправке комментария: {send_error}")
        
    except Exception as e:
        print(f"❌ Ошибка при обработке поста: {e}")

@channel_router.message()
async def discussion_message_handler(message: types.Message, bot: Bot):
    """
    Обработка всех сообщений из чата-обсуждения канала (кроме команд).
    Автоматическая модерация: проверка банов, варнов, blacklist
    """
    # КРИТИЧЕСКИ ВАЖНО: Пропускаем команды СРАЗУ (они обрабатываются в user_router и admin_router)
    # В aiogram 3.x порядок роутеров должен обеспечивать обработку команд первыми,
    # но эта проверка - дополнительная защита
    if message.text and message.text.strip().startswith("/"):
        return  # Пропускаем команды
    
    # Пропускаем сообщения от каналов (автопосты) - они обрабатываются в channel_post
    if message.sender_chat and message.sender_chat.type == "channel":
        # Это сообщение представляет пост из канала
        await asyncio.sleep(0.5)
        comment_text = f"Вижу новый пост - и первые 100 знаков этого поста: {message.text[:100] if message.text else ''}"
        try:
            await message.reply(comment_text)
            print(f"✅ Комментарий отправлен к посту {message.message_id} через reply_to")
        except Exception as e:
            print(f"❌ Ошибка при отправке комментария через reply_to: {e}")
        return None
    
    # Обрабатываем только сообщения из групп/супергрупп
    if message.chat.type not in ("supergroup", "group"):
        return None
    
    # Проверка 1: Пользователь забанен?
    if message.from_user:
        user_ban = await get_user_ban(message.from_user.id)
        if user_ban:
            try:
                await message.delete()
                await message.answer(f"❌ Ваше сообщение удалено. Вы заблокированы. Причина: {user_ban.reason or 'не указана'}")
                print(f"Сообщение от забаненного пользователя {message.from_user.id} удалено")
            except Exception as e:
                print(f"Ошибка при удалении сообщения забаненного пользователя: {e}")
            return
    
    # Проверка 2: Blacklist (проверяем текст и подпись к медиа)
    message_text = (message.text or "") + " " + (message.caption or "")
    if await check_message_for_blacklist(message_text.strip()):
        # ВАЖНО: Сначала обрабатываем пользователя и готовим уведомление, ПОТОМ удаляем сообщение
        username_display = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
        warn_count = 0
        sent_notification = None
        
        # Формируем username для сообщения
        if message.from_user.username:
            username = f"@{message.from_user.username}"
        elif message.from_user.full_name:
            username = message.from_user.full_name
        else:
            username = f"ID {message.from_user.id}"
        
        try:
            # Регистрируем пользователя, если его нет
            try:
                await register_user(
                    message.from_user.id,
                    username=message.from_user.username,
                    full_name=message.from_user.full_name
                )
            except Exception as reg_error:
                print(f"⚠️ Ошибка при регистрации пользователя {message.from_user.id}: {reg_error}")
                # Продолжаем работу, возможно пользователь уже есть
            
            # Выдаем варн за нарушение blacklist
            try:
                from app.application.services.user_service import add_warn
                await add_warn(
                    message.from_user.id,
                    reason="Использование запрещенных слов/выражений (blacklist)",
                    admin_id=None  # Автоматический варн
                )
                # Получаем обновленное количество варнов
                warn_count = await get_user_warns_count(message.from_user.id)
            except Exception as warn_error:
                print(f"⚠️ Ошибка при выдаче варна: {warn_error}")
                # Пытаемся получить текущее количество варнов
                try:
                    warn_count = await get_user_warns_count(message.from_user.id) or 0
                except:
                    warn_count = 1  # По умолчанию считаем, что выдали 1 варн
            
        except Exception as e:
            print(f"⚠️ Ошибка при обработке пользователя: {e}")
            import traceback
            traceback.print_exc()
            # Если не удалось получить warn_count, используем 1 по умолчанию
            if warn_count == 0:
                warn_count = 1
        
        # ВАЖНО: Формируем сообщение с НОВЫМ форматом (обновлено по запросу пользователя)
        # Старый формат был: "⚠️ Ваше сообщение удалено... Варнов: 2/3"
        # Новый формат: "@username, ⚠️ Ваше сообщение удалено... Предупреждений: 2/3\nПосле трех предупреждений..."
        warning_msg = (
            f"{username}, ⚠️ Ваше сообщение удалено из-за использования запрещенных слов/выражений.\n"
            f"Предупреждений: {warn_count}/3\n"
            f"После трех предупреждений Вам запретят на 24 часа комментировать посты."
        )
        
        # КРИТИЧЕСКИ ВАЖНО: Отправляем уведомление ДО удаления сообщения (чтобы reply работал)
        try:
            # Сначала пытаемся отправить reply к исходному сообщению
            sent_notification = await message.reply(warning_msg)
            print(f"✅ Уведомление отправлено пользователю {username_display}: {warning_msg[:60]}...")
        except Exception as reply_error:
            print(f"⚠️ Ошибка reply, пробуем send_message: {reply_error}")
            # Если reply не удался (нет прав), отправляем в чат без reply
            try:
                sent_notification = await bot.send_message(
                    chat_id=message.chat.id,
                    text=warning_msg
                )
                print(f"✅ Уведомление отправлено пользователю {username_display} (в чат): {warning_msg[:60]}...")
            except Exception as send_error:
                print(f"⚠️ Не удалось отправить уведомление в чат: {send_error}")
                sent_notification = None
        
        # ТЕПЕРЬ удаляем сообщение (после отправки уведомления)
        try:
            await message.delete()
            print(f"✅ Сообщение {message.message_id} от пользователя {message.from_user.id} удалено из-за blacklist")
        except Exception as delete_error:
            print(f"⚠️ Ошибка при удалении сообщения: {delete_error}")
            # Если не удалось удалить, отправляем дополнительное предупреждение
            if sent_notification:
                try:
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text=f"❌ Не удалось удалить сообщение, но пользователю {username_display} выдан варн ({warn_count}/3)"
                    )
                except:
                    pass
        
        # Логируем (если удастся)
        try:
            from app.infrastructure.db.session import get_async_session
            from app.infrastructure.db.repositories import LogRepository
            from app.infrastructure.db.models import Log
            async with get_async_session() as session:
                await LogRepository.add(session, Log(
                    event_type="message_deleted_blacklist",
                    user_id=message.from_user.id,
                    message=f"Сообщение {message.message_id} удалено из-за blacklist, выдан варн ({warn_count}/3)"
                ))
        except Exception as log_error:
            print(f"⚠️ Ошибка при логировании: {log_error}")
        
        # Если 3+ варнов → автоматический бан на 24 часа
        if warn_count >= 3:
            try:
                await ban_user(
                    message.from_user.id,
                    reason="Автоматический бан за 3+ варнов (нарушение blacklist)",
                    days=1,  # Бан на 24 часа (1 день)
                    admin_id=None
                )
                try:
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text=f"❌ Пользователь {username_display} автоматически забанен на 24 часа за превышение лимита предупреждений (3+ варнов)."
                    )
                except Exception as ban_notify_error:
                    print(f"⚠️ Не удалось отправить уведомление о бане: {ban_notify_error}")
            except Exception as ban_error:
                print(f"⚠️ Ошибка при автоматическом бане: {ban_error}")
        
        return
    
    # Ответить на комментарий пользователя (отладка)
    if message.reply_to_message and message.from_user:
        try:
            reply_text = f"Вижу комментарий {message.from_user.id} - и 10 знаков комментария: {message.text[:10] if message.text else ''}"
            await message.reply(reply_text)
        except Exception as e:
            print(f"Ошибка при ответе на комментарий: {e}")
