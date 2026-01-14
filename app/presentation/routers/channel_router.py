"""
Обработка событий канала: новые посты, комментарии к постам (обсуждение).
С автоматической модерацией: проверка банов, варнов, blacklist
С AI-комментированием постов и ответами на комментарии пользователей.
"""
from aiogram import Router, types, Bot
from aiogram.filters import Command
from app.application.services.moderation_service import check_message_for_blacklist
from app.application.services.user_service import get_user_ban, get_user_by_id, get_user_warns_count, ban_user, register_user, add_warn
from app.application.services.content_service import prepare_message_content
from app.application.services.comment_service import CommentService
from app.application.services import get_comment_service, get_ai_clients
import asyncio
import logging

logger = logging.getLogger(__name__)

channel_router = Router()


async def check_and_handle_blacklist_violation(
    bot: Bot,
    message: types.Message,
    violation_type: str,
    content_for_check: str
) -> bool:
    """
    Проверяет контент на blacklist и обрабатывает нарушение (удаляет сообщение, выдает варн).
    
    :param bot: Экземпляр бота
    :param message: Сообщение для проверки
    :param violation_type: Тип нарушения (для логирования и уведомления)
    :param content_for_check: Контент для проверки на blacklist
    :return: True если найдено нарушение и сообщение удалено, False если все ОК
    """
    logger.info(f"🔍 Проверяем blacklist для {violation_type}: контент='{content_for_check[:100]}...'")
    is_violation = await check_message_for_blacklist(content_for_check.strip())
    if not is_violation:
        logger.info(f"✅ Проверка blacklist пройдена для {violation_type}")
        return False  # Нарушения нет
    
    logger.warning(f"⚠️ НАРУШЕНИЕ BLACKLIST ОБНАРУЖЕНО! {violation_type} содержит запрещенную лексику, удаляем комментарий")
    
    logger.warning(f"⚠️ {violation_type} содержит запрещенную лексику, удаляем комментарий")
    
    username_display = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
    warn_count = 0
    
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
                user_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
        except Exception as reg_error:
            logger.warning(f"⚠️ Ошибка при регистрации пользователя {message.from_user.id}: {reg_error}")
        
        # Выдаем варн за нарушение blacklist
        await add_warn(
            user_id=message.from_user.id,
            reason=f"Использование запрещенных слов/выражений ({violation_type})",
            admin_id=None
        )
        warn_count = await get_user_warns_count(message.from_user.id)
    except Exception as e:
        logger.error(f"⚠️ Ошибка при обработке пользователя: {e}", exc_info=True)
        if warn_count == 0:
            warn_count = 1
    
    # Отправляем уведомление
    warning_msg = (
        f"{username}, ⚠️ Ваше сообщение удалено из-за использования запрещенных слов/выражений ({violation_type}).\n"
        f"Предупреждений: {warn_count}/3\n"
        f"После трех предупреждений Вам запретят на 24 часа комментировать посты."
    )
    
    try:
        await message.reply(warning_msg)
        logger.info(f"✅ Уведомление отправлено пользователю {username_display}")
    except Exception as reply_error:
        try:
            await bot.send_message(
                chat_id=message.chat.id,
                text=warning_msg
            )
        except Exception:
            pass
    
    # Удаляем сообщение
    try:
        await message.delete()
        logger.info(f"✅ Комментарий {message.message_id} с запрещенной лексикой удален")
    except Exception as delete_error:
        logger.error(f"⚠️ Ошибка при удалении сообщения: {delete_error}")
    
    # Если 3+ варнов → автоматический бан
    if warn_count >= 3:
        try:
            await ban_user(
                user_id=message.from_user.id,
                reason=f"Автоматический бан за 3+ варнов (нарушение blacklist: {violation_type})",
                days=1,
                admin_id=None
            )
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"❌ Пользователь {username_display} автоматически забанен на 24 часа за превышение лимита предупреждений (3+ варнов)."
            )
        except Exception as ban_error:
            logger.error(f"⚠️ Ошибка при автоматическом бане: {ban_error}")
    
    return True  # Нарушение найдено и обработано


@channel_router.channel_post()
async def new_channel_post_handler(message: types.Message, bot: Bot):
    """
    Обработчик новых постов в канале (Bot должен быть администратором).
    Генерирует и публикует первый комментарий к посту в связанной группе обсуждений.
    """
    # 1. Проверка на запрещёнку - удаляем пост (проверяем текст и подпись к медиа)
    post_text = (message.text or "") + " " + (message.caption or "")
    if await check_message_for_blacklist(post_text.strip()):
        try:
            await message.delete()
            logger.info(f"✅ Пост {message.message_id} в канале удален из-за blacklist")
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
            logger.error(f"❌ Ошибка при удалении поста: {e}")
        return

    # 2. Генерируем и публикуем первый комментарий к посту в группе обсуждений
    try:
        chat = await bot.get_chat(message.chat.id)
        
        if hasattr(chat, 'linked_chat') and chat.linked_chat:
            linked_chat_id = chat.linked_chat.id
        elif hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
            linked_chat_id = chat.linked_chat_id
        else:
            logger.warning(f"У канала {message.chat.id} нет связанной группы обсуждений")
            return
        
        # Получаем сервис комментариев
        comment_service = get_comment_service()
        if not comment_service:
            logger.warning("Сервис комментариев недоступен, пропускаем генерацию комментария")
            return
        
        # Подготавливаем контент поста для обработки AI
        try:
            ai_clients = get_ai_clients()
            if not ai_clients:
                logger.warning("AI клиенты недоступны, используем базовый текст")
                post_content = message.text or message.caption or "Пост без текста"
            else:
                post_content = await prepare_message_content(bot, message, ai_clients.openai)
        except Exception as e:
            logger.error(f"Ошибка при подготовке контента поста: {e}")
            # Используем базовый текст, если обработка не удалась
            post_content = message.text or message.caption or "Пост без текста"
        
        # Генерируем комментарий через AI
        comment_text = await comment_service.generate_post_comment(
            post_content=post_content,
            chat_id=linked_chat_id
        )
        
        if not comment_text:
            logger.warning("Не удалось сгенерировать комментарий к посту")
            return
        
        # Небольшая задержка перед отправкой комментария
        await asyncio.sleep(2)
        
        # Пытаемся отправить комментарий с retry механизмом
        max_retries = 3
        retry_delay = 2.0
        for attempt in range(max_retries):
            try:
                # Используем таймаут для отправки сообщения
                sent_message = await asyncio.wait_for(
                    bot.send_message(
                        chat_id=linked_chat_id,
                        text=comment_text,
                        reply_to_message_id=message.message_id
                    ),
                    timeout=30.0
                )
                logger.info(f"✅ AI комментарий отправлен к посту {message.message_id}")
                break  # Успешно отправлено, выходим из цикла
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Таймаут при отправке комментария (попытка {attempt + 1}/{max_retries}), повтор через {retry_delay} сек...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"⚠️ Таймаут при отправке комментария к посту {message.message_id} после {max_retries} попыток")
            except Exception as send_error:
                error_msg = str(send_error)
                # Проверяем, это ли известная проблема Windows с семафором
                if "WinError 121" in error_msg or "таймаут семафора" in error_msg.lower():
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Проблема с сетью Windows (попытка {attempt + 1}/{max_retries}), повтор через {retry_delay} сек...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"⚠️ Не удалось отправить комментарий к посту {message.message_id} после {max_retries} попыток (проблема с сетью Windows)")
                else:
                    logger.error(f"⚠️ Ошибка при отправке комментария: {send_error}", exc_info=True)
                    break  # Для других ошибок не повторяем
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке поста: {e}", exc_info=True)


@channel_router.message()
async def discussion_message_handler(message: types.Message, bot: Bot):
    """
    Обработка всех сообщений из чата-обсуждения канала (кроме команд).
    Автоматическая модерация: проверка банов, варнов, blacklist
    AI-ответы на комментарии пользователей.
    """
    # КРИТИЧЕСКИ ВАЖНО: Пропускаем команды СРАЗУ (они обрабатываются в user_router и admin_router)
    # В aiogram 3.x порядок роутеров должен обеспечивать обработку команд первыми,
    # но эта проверка - дополнительная защита
    if message.text and message.text.strip().startswith("/"):
        return  # Пропускаем команды
    
    # Пропускаем сообщения от каналов (автопосты) - они обрабатываются в channel_post
    if message.sender_chat and message.sender_chat.type == "channel":
        # Это сообщение представляет пост из канала
        # Обрабатываем его как новый пост (генерируем комментарий)
        comment_service = get_comment_service()
        if comment_service:
            try:
                ai_clients = get_ai_clients()
                if ai_clients:
                    post_content = await prepare_message_content(bot, message, ai_clients.openai)
                else:
                    post_content = message.text or message.caption or "Пост без текста"
                comment_text = await comment_service.generate_post_comment(
                    post_content=post_content,
                    chat_id=message.chat.id
                )
                if comment_text:
                    await asyncio.sleep(0.5)
                    await message.reply(comment_text)
                    logger.info(f"✅ AI комментарий отправлен к посту {message.message_id} через reply_to")
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке комментария через reply_to: {e}")
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
                logger.info(f"Сообщение от забаненного пользователя {message.from_user.id} удалено")
            except Exception as e:
                logger.error(f"Ошибка при удалении сообщения забаненного пользователя: {e}")
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
                logger.warning(f"⚠️ Ошибка при регистрации пользователя {message.from_user.id}: {reg_error}")
                # Продолжаем работу, возможно пользователь уже есть
            
            # Выдаем варн за нарушение blacklist
            try:
                await add_warn(
                    message.from_user.id,
                    reason="Использование запрещенных слов/выражений (blacklist)",
                    admin_id=None  # Автоматический варн
                )
                # Получаем обновленное количество варнов
                warn_count = await get_user_warns_count(message.from_user.id)
            except Exception as warn_error:
                logger.warning(f"⚠️ Ошибка при выдаче варна: {warn_error}")
                # Пытаемся получить текущее количество варнов
                try:
                    warn_count = await get_user_warns_count(message.from_user.id) or 0
                except:
                    warn_count = 1  # По умолчанию считаем, что выдали 1 варн
            
        except Exception as e:
            logger.error(f"⚠️ Ошибка при обработке пользователя: {e}")
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
            logger.info(f"✅ Уведомление отправлено пользователю {username_display}: {warning_msg[:60]}...")
        except Exception as reply_error:
            logger.warning(f"⚠️ Ошибка reply, пробуем send_message: {reply_error}")
            # Если reply не удался (нет прав), отправляем в чат без reply
            try:
                sent_notification = await bot.send_message(
                    chat_id=message.chat.id,
                    text=warning_msg
                )
                logger.info(f"✅ Уведомление отправлено пользователю {username_display} (в чат): {warning_msg[:60]}...")
            except Exception as send_error:
                logger.error(f"⚠️ Не удалось отправить уведомление в чат: {send_error}")
                sent_notification = None
        
        # ТЕПЕРЬ удаляем сообщение (после отправки уведомления)
        try:
            await message.delete()
            logger.info(f"✅ Сообщение {message.message_id} от пользователя {message.from_user.id} удалено из-за blacklist")
        except Exception as delete_error:
            logger.error(f"⚠️ Ошибка при удалении сообщения: {delete_error}")
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
            logger.error(f"⚠️ Ошибка при логировании: {log_error}")
        
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
                    logger.warning(f"⚠️ Не удалось отправить уведомление о бане: {ban_notify_error}")
            except Exception as ban_error:
                logger.error(f"⚠️ Ошибка при автоматическом бане: {ban_error}")
        
        return
    
    # Проверка 2.5: Blacklist для медиа-контента (фото, PDF, документы, аудио)
    # Проверяем медиа-контент ДО генерации ответа, чтобы не тратить ресурсы на AI если есть нарушение
    # ВАЖНО: Проверка выполняется для ВСЕХ сообщений, не только для ответов
    ai_clients = get_ai_clients()
    if ai_clients and ai_clients.openai:
        try:
            # Подготавливаем полный контент для проверки
            full_content = await prepare_message_content(bot, message, ai_clients.openai)
            logger.info(f"Полный контент для проверки blacklist: {full_content[:200]}...")
            
            # Проверяем описание фотографии (фото с подписью или текстом)
            # ВАЖНО: Проверяем для фото ОБЯЗАТЕЛЬНО
            if message.photo:
                logger.info(f"Обнаружено фото в сообщении, проверяем описание на blacklist")
                # Ищем описание изображения в полном контенте
                if "Описание изображения:" in full_content:
                    parts = full_content.split("Описание изображения:")
                    if len(parts) > 1:
                        image_description = parts[1].strip()
                        logger.info(f"Описание изображения найдено: {image_description[:100]}...")
                        caption = message.caption or ""
                        text_message = message.text or ""
                        image_content_for_check = f"{text_message} {caption} {image_description}".strip()
                        logger.info(f"Проверяем blacklist для: текст='{text_message}', подпись='{caption}', описание='{image_description[:50]}...'")
                        
                        if await check_and_handle_blacklist_violation(
                            bot, message, "в описании фотографии или тексте/подписи", image_content_for_check
                        ):
                            logger.info(f"✅ Нарушение blacklist найдено в описании фотографии, сообщение удалено")
                            return  # Сообщение удалено, прерываем обработку
                        else:
                            logger.info(f"✅ Описание фотографии прошло проверку blacklist")
                else:
                    # Если описание не найдено, но есть фото - проверяем только текст/подпись
                    logger.warning(f"⚠️ Фото обнаружено, но описание не найдено в контенте. Проверяем только текст/подпись.")
                    caption = message.caption or ""
                    text_message = message.text or ""
                    if text_message or caption:
                        image_content_for_check = f"{text_message} {caption}".strip()
                        if await check_and_handle_blacklist_violation(
                            bot, message, "в тексте/подписи к фотографии", image_content_for_check
                        ):
                            logger.info(f"✅ Нарушение blacklist найдено в тексте/подписи к фотографии, сообщение удалено")
                            return  # Сообщение удалено, прерываем обработку
            
            # Проверяем PDF документ (PDF с подписью или текстом)
            # ВАЖНО: Проверяем для PDF документов ОБЯЗАТЕЛЬНО
            if message.document and message.document.file_name and message.document.file_name.lower().endswith('.pdf'):
                logger.info(f"Обнаружен PDF документ в сообщении, проверяем текст на blacklist")
                # Ищем текст из PDF в полном контенте
                if "Текст из PDF документа:" in full_content:
                    parts = full_content.split("Текст из PDF документа:")
                    if len(parts) > 1:
                        pdf_text_content = parts[1].strip()
                        logger.info(f"Текст из PDF найден: {len(pdf_text_content)} символов")
                        caption = message.caption or ""
                        text_message = message.text or ""
                        pdf_content_for_check = f"{text_message} {caption} {pdf_text_content}".strip()
                        logger.info(f"Проверяем blacklist для: текст='{text_message}', подпись='{caption}', PDF текст='{pdf_text_content[:50]}...'")
                        
                        if await check_and_handle_blacklist_violation(
                            bot, message, "в PDF документе или тексте/подписи", pdf_content_for_check
                        ):
                            logger.info(f"✅ Нарушение blacklist найдено в PDF документе, сообщение удалено")
                            return  # Сообщение удалено, прерываем обработку
                        else:
                            logger.info(f"✅ Текст из PDF документа прошел проверку blacklist")
                else:
                    # Если текст не найден, но есть PDF - проверяем только текст/подпись
                    logger.warning(f"⚠️ PDF документ обнаружен, но текст не найден в контенте. Проверяем только текст/подпись.")
                    caption = message.caption or ""
                    text_message = message.text or ""
                    if text_message or caption:
                        pdf_content_for_check = f"{text_message} {caption}".strip()
                        if await check_and_handle_blacklist_violation(
                            bot, message, "в тексте/подписи к PDF документу", pdf_content_for_check
                        ):
                            logger.info(f"✅ Нарушение blacklist найдено в тексте/подписи к PDF документу, сообщение удалено")
                            return  # Сообщение удалено, прерываем обработку
            
            # Проверяем другие документы (txt, docx, xlsx, pptx, odt) с подписью или текстом
            # ВАЖНО: Проверяем для документов ОБЯЗАТЕЛЬНО
            if message.document and message.document.file_name:
                file_name_lower = message.document.file_name.lower()
                supported_extensions = ['.txt', '.docx', '.xlsx', '.pptx', '.odt']
                document_extension = None
                for ext in supported_extensions:
                    if file_name_lower.endswith(ext):
                        document_extension = ext
                        break
                
                if document_extension:
                    logger.info(f"Обнаружен документ {document_extension} в сообщении, проверяем текст на blacklist")
                    # Ищем текст из документа в полном контенте
                    if f"Текст из документа {document_extension}:" in full_content:
                        parts = full_content.split(f"Текст из документа {document_extension}:")
                        if len(parts) > 1:
                            document_text_content = parts[1].strip()
                            logger.info(f"Текст из документа {document_extension} найден: {len(document_text_content)} символов")
                            caption = message.caption or ""
                            text_message = message.text or ""
                            document_content_for_check = f"{text_message} {caption} {document_text_content}".strip()
                            logger.info(f"Проверяем blacklist для: текст='{text_message}', подпись='{caption}', текст документа='{document_text_content[:50]}...'")
                            
                            if await check_and_handle_blacklist_violation(
                                bot, message, f"в документе {document_extension} или тексте/подписи", document_content_for_check
                            ):
                                logger.info(f"✅ Нарушение blacklist найдено в документе {document_extension}, сообщение удалено")
                                return  # Сообщение удалено, прерываем обработку
                            else:
                                logger.info(f"✅ Текст из документа {document_extension} прошел проверку blacklist")
                    else:
                        # Если текст не найден, но есть документ - проверяем только текст/подпись
                        logger.warning(f"⚠️ Документ {document_extension} обнаружен, но текст не найден в контенте. Проверяем только текст/подпись.")
                        caption = message.caption or ""
                        text_message = message.text or ""
                        if text_message or caption:
                            document_content_for_check = f"{text_message} {caption}".strip()
                            if await check_and_handle_blacklist_violation(
                                bot, message, f"в тексте/подписи к документу {document_extension}", document_content_for_check
                            ):
                                logger.info(f"✅ Нарушение blacklist найдено в тексте/подписи к документу {document_extension}, сообщение удалено")
                                return  # Сообщение удалено, прерываем обработку
            
            # Проверяем транскрипцию аудио (голосовые сообщения и аудио файлы)
            # ВАЖНО: Проверяем для голосовых сообщений и аудио файлов ОБЯЗАТЕЛЬНО
            if message.voice or message.audio:
                logger.info(f"Обнаружено голосовое/аудио сообщение, проверяем транскрипцию на blacklist")
                # Ищем транскрипцию в полном контенте
                if "Транскрипция аудио:" in full_content:
                    parts = full_content.split("Транскрипция аудио:")
                    if len(parts) > 1:
                        transcription_content = parts[1].strip()
                        logger.info(f"Транскрипция найдена: {transcription_content[:100]}...")
                        caption = message.caption or ""
                        text_message = message.text or ""
                        audio_content_for_check = f"{text_message} {caption} {transcription_content}".strip()
                        logger.info(f"Проверяем blacklist для: текст='{text_message}', подпись='{caption}', транскрипция='{transcription_content[:50]}...'")
                        
                        if await check_and_handle_blacklist_violation(
                            bot, message, "в транскрипции аудио или тексте/подписи", audio_content_for_check
                        ):
                            logger.info(f"✅ Нарушение blacklist найдено в транскрипции аудио, сообщение удалено")
                            return  # Сообщение удалено, прерываем обработку
                        else:
                            logger.info(f"✅ Транскрипция аудио прошла проверку blacklist")
                else:
                    # Если транскрипция не найдена, но есть голосовое сообщение - проверяем только текст/подпись
                    logger.warning(f"⚠️ Голосовое/аудио сообщение обнаружено, но транскрипция не найдена в контенте. Проверяем только текст/подпись.")
                    caption = message.caption or ""
                    text_message = message.text or ""
                    if text_message or caption:
                        audio_content_for_check = f"{text_message} {caption}".strip()
                        if await check_and_handle_blacklist_violation(
                            bot, message, "в тексте/подписи голосового сообщения", audio_content_for_check
                        ):
                            logger.info(f"✅ Нарушение blacklist найдено в тексте/подписи голосового сообщения, сообщение удалено")
                            return  # Сообщение удалено, прерываем обработку
                        
        except Exception as e:
            logger.error(f"Ошибка при проверке blacklist для медиа-контента: {e}", exc_info=True)
            # Продолжаем обработку, если проверка медиа не удалась
    
    # 3. AI-ответ на комментарий пользователя
    # ВАЖНО: Проверка blacklist для всех медиа уже выполнена выше (строка 411)
    # Здесь только подготавливаем контент и генерируем ответ
    if message.reply_to_message and message.from_user:
        comment_service = get_comment_service()
        if comment_service:
            try:
                # Получаем полный контент комментария пользователя (текст/подпись + описание фото/PDF/документы/аудио)
                # ВАЖНО: Если AI клиенты доступны, используем уже подготовленный контент из проверки выше
                # Если нет - подготавливаем заново
                ai_clients = get_ai_clients()
                if not ai_clients or not ai_clients.openai:
                    logger.warning("AI клиенты недоступны, используем только текст/подпись")
                    user_comment = message.text or message.caption or ""
                    if not user_comment:
                        return  # Пропускаем сообщения без текста
                else:
                    # Обрабатываем комментарий через prepare_message_content
                    # ВАЖНО: Это повторный вызов, но он нужен для генерации ответа
                    # Можно оптимизировать, сохранив full_content из проверки выше, но для простоты оставим так
                    try:
                        user_comment_full = await prepare_message_content(
                            bot, message, ai_clients.openai
                        )
                        logger.info(f"Полный контент комментария пользователя для генерации ответа: {user_comment_full[:200]}...")
                        
                        # УДАЛЕНО: Все проверки blacklist (уже выполнены выше, строка 411)
                        # Используем полный контент для формирования ответа
                        user_comment = user_comment_full
                    except Exception as e:
                        logger.error(f"Ошибка при обработке контента комментария пользователя: {e}", exc_info=True)
                        # Используем базовый текст, если обработка не удалась
                        user_comment = message.text or message.caption or ""
                        if not user_comment:
                            return  # Пропускаем сообщения без текста
                
                # Получаем контент оригинального поста (если есть)
                original_post_content = None
                if message.reply_to_message:
                    try:
                        if ai_clients and ai_clients.openai:
                            original_post_content = await prepare_message_content(
                                bot, message.reply_to_message, ai_clients.openai
                            )
                    except Exception as e:
                        logger.warning(f"Не удалось подготовить контент оригинального поста: {e}")
                
                # Генерируем ответ через AI
                reply_text = await comment_service.generate_reply_to_comment(
                    user_comment=user_comment,
                    original_post_content=original_post_content,
                    chat_id=message.chat.id
                )
                
                if reply_text:
                    # Пытаемся отправить ответ с retry механизмом
                    max_retries = 3
                    retry_delay = 2.0
                    for attempt in range(max_retries):
                        try:
                            # Используем таймаут для отправки ответа
                            await asyncio.wait_for(
                                message.reply(reply_text),
                                timeout=30.0
                            )
                            logger.info(f"✅ AI ответ отправлен на комментарий пользователя {message.from_user.id}")
                            break  # Успешно отправлено, выходим из цикла
                        except asyncio.TimeoutError:
                            if attempt < max_retries - 1:
                                logger.warning(f"⚠️ Таймаут при отправке ответа (попытка {attempt + 1}/{max_retries}), повтор через {retry_delay} сек...")
                                await asyncio.sleep(retry_delay)
                            else:
                                logger.error(f"⚠️ Таймаут при отправке ответа на комментарий пользователя {message.from_user.id} после {max_retries} попыток")
                        except Exception as reply_error:
                            error_msg = str(reply_error)
                            # Проверяем, это ли известная проблема Windows с семафором
                            if "WinError 121" in error_msg or "таймаут семафора" in error_msg.lower():
                                if attempt < max_retries - 1:
                                    logger.warning(f"⚠️ Проблема с сетью Windows (попытка {attempt + 1}/{max_retries}), повтор через {retry_delay} сек...")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"⚠️ Не удалось отправить ответ на комментарий пользователя {message.from_user.id} после {max_retries} попыток (проблема с сетью Windows)")
                            else:
                                logger.error(f"Ошибка при отправке ответа на комментарий: {reply_error}", exc_info=True)
                                break  # Для других ошибок не повторяем
            except Exception as e:
                logger.error(f"Ошибка при генерации ответа на комментарий: {e}", exc_info=True)
