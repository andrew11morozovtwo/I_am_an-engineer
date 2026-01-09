"""
Обработка событий канала: новые посты, комментарии к постам (обсуждение).
"""
from aiogram import Router, types, Bot
from app.application.services.moderation_service import check_message_for_blacklist
import asyncio

channel_router = Router()

@channel_router.channel_post()
async def new_channel_post_handler(message: types.Message, bot: Bot):
    """
    Обработчик новых постов в канале (Bot должен быть администратором).
    Отвечает первым комментарием к посту в связанной группе обсуждений.
    """
    # 1. Проверка на запрещёнку - оставить как есть
    if await check_message_for_blacklist(message.text):
        try:
            await message.delete()
        except Exception as e:
            print(f"Ошибка при удалении поста: {e}")
        return

    # 2. Оставить первый комментарий к посту в группе обсуждений
    try:
        # Получаем информацию о канале
        chat = await bot.get_chat(message.chat.id)
        
        # Проверяем, есть ли связанная группа для обсуждений
        if hasattr(chat, 'linked_chat') and chat.linked_chat:
            linked_chat_id = chat.linked_chat.id
        elif hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
            linked_chat_id = chat.linked_chat_id
        else:
            print("У канала нет связанной группы для обсуждений")
            return
        
        comment_text = f"Вижу новый пост - и первые 100 знаков этого поста: {message.text[:100] if message.text else ''}"
        
        # Ждем немного, чтобы Telegram успел создать сообщение в группе обсуждений
        await asyncio.sleep(2)
        
        # В Telegram, когда пост публикуется в канале с обсуждениями,
        # в связанной группе создается сообщение с тем же message_id
        # Используем send_message с reply_to_message_id для отправки комментария
        try:
            sent_message = await bot.send_message(
                chat_id=linked_chat_id,
                text=comment_text,
                reply_to_message_id=message.message_id
            )
            print(f"✅ Комментарий отправлен к посту {message.message_id}, ID комментария: {sent_message.message_id}")
        except Exception as e:
            print(f"❌ Ошибка при отправке комментария: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Ошибка при обработке поста: {e}")
        import traceback
        traceback.print_exc()

@channel_router.message()
async def discussion_message_handler(message: types.Message):
    """
    Обработка всех сообщений из чата-обсуждения канала.
    Отслеживает сообщения, представляющие посты из канала, и отвечает на них через reply_to.
    """
    # Проверяем, является ли это сообщением от канала в группе обсуждений
    if message.sender_chat and message.sender_chat.type == "channel":
        # Это сообщение представляет пост из канала
        # Ждем немного и отвечаем на него
        await asyncio.sleep(0.5)
        comment_text = f"Вижу новый пост - и первые 100 знаков этого поста: {message.text[:100] if message.text else ''}"
        try:
            # Используем reply_to как в вашем другом боте
            await message.reply(comment_text)
            print(f"✅ Комментарий отправлен к посту {message.message_id} через reply_to")
        except Exception as e:
            print(f"❌ Ошибка при отправке комментария через reply_to: {e}")
        return
    
    # Обрабатываем только сообщения из групп/супергрупп
    if message.chat.type not in ("supergroup", "group"):
        return

    if await check_message_for_blacklist(message.text):
        try:
            await message.delete()
        except Exception as e:
            print(f"Ошибка при удалении комментария: {e}")
        return

    # Ответить на комментарий пользователя (отладка)
    # Проверяем, что это комментарий к посту из канала (reply_to_message существует)
    if message.reply_to_message:
        try:
            reply_text = f"Вижу комментарий {message.from_user.id} - и 10 знаков комментария: {message.text[:10] if message.text else ''}"
            # Используем reply_to как в вашем другом боте
            await message.reply(reply_text)
        except Exception as e:
            print(f"Ошибка при ответе на комментарий: {e}")
