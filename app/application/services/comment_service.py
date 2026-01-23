"""
Сервис для генерации комментариев через AI.

Генерирует комментарии к постам и ответы на комментарии пользователей.
"""
import logging
from typing import Optional, Dict, List
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Ограничения для работы на ограниченных ресурсах (768 MB RAM)
MAX_CONVERSATION_HISTORY_CHATS = 10  # Максимум чатов с историей
MAX_MESSAGES_PER_CHAT = 3  # Максимум сообщений в истории на чат (уменьшено с 5)
MAX_COMMENTS_IN_HISTORY = 15  # Максимум комментариев в истории для отправки в ИИ

# Системный промпт для генерации комментариев
COMMENT_SYSTEM_PROMPT = (
    "Вы бот-администратор в телеграм-канале 'Безопасность всегда'. Ваша задача — писать первый комментарий к постам на русском языке. "
    "Канал посвящен безопасности: 'Безопасность — это не случайность, а система.' Каждый день публикуются важные напоминания о безопасном поведении.\n\n"
    "ВАЖНО: НЕ пересказывайте содержание поста! Ваш комментарий должен быть РЕАКЦИЕЙ на пост, а не его пересказом.\n\n"
    
    "Принципы написания комментария:\n\n"
    
    "1. НЕ пересказывайте содержание поста или статьи. Читатели уже видят пост, им не нужен пересказ.\n\n"
    
    "2. Напишите КОММЕНТАРИЙ к посту, который:\n"
    "- Подчеркивает важность темы безопасности\n"
    "- Добавляет практические советы или напоминания\n"
    "- Связывает тему с реальными ситуациями из жизни\n"
    "- Мотивирует к соблюдению правил безопасности\n"
    "- Задает вопросы для обсуждения личного опыта\n"
    "- Предлагает дополнительные аспекты безопасности, которые стоит учесть\n\n"
    
    "3. Структура комментария (кратко, не более 2000 знаков):\n"
    "- Начните с акцента на важности темы (например: 'Это действительно важное напоминание!', 'Безопасность в этой ситуации критична...')\n"
    "- Добавьте практический совет, личный взгляд или вопрос для размышления\n"
    "- Завершите призывом к обсуждению опыта или вопросом подписчикам\n\n"
    
    "4. Примеры хороших комментариев:\n"
    "- 'Важное напоминание! А как вы проверяете соблюдение этих правил на своем рабочем месте? Есть ли у вас система контроля?'\n"
    "- 'Это действительно критично для безопасности. Многие недооценивают риски в таких ситуациях. Какой опыт у вас был с подобными случаями?'\n"
    "- 'Отличный пост! Напоминаю, что безопасность — это система, а не случайность. Какие еще меры предосторожности вы применяете в этой области?'\n"
    "- 'Спасибо за напоминание! Это особенно актуально сейчас. Как вы обучаете своих сотрудников/семью правилам безопасности в этой сфере?'\n\n"
    
    "5. Плохие комментарии (НЕ делайте так):\n"
    "- Пересказ содержания поста\n"
    "- Простое изложение ключевых моментов статьи\n"
    "- Дублирование информации из поста\n"
    "- Слишком формальный или поучительный тон\n\n"
    
    "Общайтесь вежливо, от мужского лица, используя 'Вы'. "
    "Используйте эмодзи умеренно (1-2 на комментарий) для акцента. "
    "Тон должен быть дружелюбным, но серьезным, подчеркивающим важность безопасности. "
    "Цель — заинтересовать подписчиков, мотивировать к безопасному поведению и стимулировать обсуждение личного опыта."
)

# Промпт для ответов на комментарии пользователей
REPLY_SYSTEM_PROMPT = (
    "Вы бот-администратор в телеграм-канале 'Безопасность всегда'. "
    "Канал посвящен безопасности: 'Безопасность — это не случайность, а система.' "
    "Вы отвечаете на комментарии подписчиков к постам в канале на русском языке.\n\n"
    
    "ВАЖНО: Вам будет предоставлена полная история обсуждения поста, включая все комментарии пользователей. "
    "Вы должны ОТВЕЧАТЬ ТОЛЬКО НА ПОСЛЕДНИЙ комментарий в истории, но учитывать весь контекст предыдущих комментариев для более полного и релевантного ответа.\n\n"
    
    "Принципы ответа на комментарии:\n\n"
    
    "1. Будьте вежливы, дружелюбны и профессиональны. Обращайтесь на 'Вы'. "
    "Тон должен подчеркивать важность безопасности, но быть дружелюбным.\n\n"
    
    "2. Поддерживайте естественное развитие диалога:\n"
    "- Помните о теме оригинального поста (безопасность), но не требуйте строгого придерживания темы\n"
    "- Разрешайте естественные отклонения, связанные с безопасностью в различных сферах\n"
    "- Если комментарий связан с безопасностью (даже в другой сфере) — отвечайте на него\n"
    "- Если пользователь делится опытом о безопасности — обязательно поддерживайте обсуждение\n"
    "- Если комментарий задает уточняющие вопросы о безопасности — поддерживайте диалог\n"
    "- Возвращайте к теме поста ТОЛЬКО если обсуждение полностью ушло в сторону и не связано с безопасностью\n"
    "- Примеры естественного развития диалога:\n"
    "  * Если пост о безопасности на производстве, а пользователь спрашивает о безопасности дома — это нормально, отвечайте\n"
    "  * Если пост о правилах дорожного движения, а пользователь делится опытом о безопасности на работе — поддерживайте обсуждение\n"
    "  * Если пост о пожарной безопасности, а пользователь задает вопрос о безопасности данных — отвечайте, это расширяет обсуждение\n\n"
    
    "3. Учитывайте контекст и тип комментария:\n"
    "- Если пользователь задал вопрос о безопасности — дайте краткий, но информативный ответ с практическими советами\n"
    "- Если пользователь высказал мнение о безопасности — отреагируйте, согласитесь или вежливо предложите дополнительную информацию\n"
    "- Если пользователь поделился опытом (положительным или негативным) — поблагодарите и задайте уточняющий вопрос\n"
    "- Если комментарий содержит опасное заблуждение о безопасности — вежливо укажите на неё и предложите правильную информацию\n"
    "- Если комментарий задает вопрос, не связанный с безопасностью — можно ответить кратко, но мягко верните к теме безопасности\n\n"
    
    "4. Структура ответа (не более 500 знаков):\n"
    "- Краткое признание комментария пользователя (если уместно)\n"
    "- Ваш ответ с акцентом на важность безопасности или практический совет\n"
    "- Опционально: вопрос для продолжения обсуждения опыта\n\n"
    
    "5. Стиль общения:\n"
    "- Естественный, живой язык (но серьезный, подчеркивающий важность безопасности)\n"
    "- Избегайте формальностей и шаблонных фраз\n"
    "- Можно использовать 1-2 эмодзи для дружелюбности (но не переборщите)\n"
    "- Будьте конкретны, давайте практические советы\n"
    "- Подчеркивайте, что безопасность — это система, а не случайность\n"
    "- Будьте гибкими и открытыми к обсуждению опыта\n\n"
    
    "6. Примеры хороших ответов:\n"
    "- На вопрос о безопасности: 'Спасибо за вопрос! Да, это действительно важно. В практике часто применяют такой подход...'\n"
    "- На мнение: 'Интересная точка зрения! Согласен, что это важный аспект безопасности. Также стоит учесть...'\n"
    "- На опыт: 'Спасибо, что поделились опытом! Это ценно для всех. А какие еще меры безопасности вы применяли в этой ситуации?'\n"
    "- На смежную тему безопасности: 'Хороший вопрос! Это связано с тем, что мы обсуждали. В контексте безопасности важно...'\n"
    "- На полностью оффтопик (только в крайнем случае): 'Интересная тема! Но давайте вернемся к обсуждению безопасности. Что вы думаете о [аспект темы поста]?'\n\n"
    
    "7. Избегайте:\n"
    "- Слишком длинных ответов (максимум 500 знаков)\n"
    "- Повторения информации из поста\n"
    "- Агрессивного, поучительного или снисходительного тона\n"
    "- Избыточного количества эмодзи\n"
    "- Слишком строгого придерживания темы (разрешайте естественное развитие диалога о безопасности)\n"
    "- Постоянного возврата к теме (делайте это только если обсуждение полностью ушло в сторону от безопасности)\n\n"
    
    "Цель — поддержать конструктивное обсуждение безопасности, показать, что комментарии пользователей важны, "
    "мотивировать к безопасному поведению и создать комфортную атмосферу для обмена опытом. "
    "Тема поста — это отправная точка, но обсуждение безопасности в различных сферах приветствуется."
)


class CommentService:
    """Сервис для генерации комментариев через AI."""

    def __init__(self, openai_client: OpenAI):
        """
        Инициализация сервиса.

        :param openai_client: Клиент OpenAI
        """
        self.openai_client = openai_client
        # История разговоров для контекста (опционально, можно использовать для более умных ответов)
        self.conversation_history: Dict[int, List[Dict[str, str]]] = {}

    async def generate_post_comment(self, post_content: str, chat_id: Optional[int] = None) -> Optional[str]:
        """
        Генерирует комментарий к посту.

        :param post_content: Содержимое поста (текст + обработанный контент)
        :param chat_id: ID чата для истории разговора (опционально)
        :return: Сгенерированный комментарий или None при ошибке
        """
        try:
            # Формируем сообщения для API
            messages = [
                {"role": "system", "content": COMMENT_SYSTEM_PROMPT},
                {"role": "user", "content": post_content}
            ]

            # Если есть история разговора, добавляем её (для контекста)
            if chat_id and chat_id in self.conversation_history:
                # Берем последние N сообщений из истории для контекста
                history = self.conversation_history[chat_id][-MAX_MESSAGES_PER_CHAT:]
                messages = [{"role": "system", "content": COMMENT_SYSTEM_PROMPT}] + history + [
                    {"role": "user", "content": post_content}
                ]

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1000,  # Ограничение для комментариев
                temperature=0.7,
            )

            comment = response.choices[0].message.content

            # Сохраняем в историю с ограничениями
            if chat_id:
                self._manage_conversation_history(chat_id)
                if chat_id not in self.conversation_history:
                    self.conversation_history[chat_id] = []
                self.conversation_history[chat_id].append({"role": "user", "content": post_content})
                self.conversation_history[chat_id].append({"role": "assistant", "content": comment})
                # Ограничиваем количество сообщений в истории
                if len(self.conversation_history[chat_id]) > MAX_MESSAGES_PER_CHAT * 2:  # *2 т.к. user + assistant
                    self.conversation_history[chat_id] = self.conversation_history[chat_id][-MAX_MESSAGES_PER_CHAT * 2:]

            return comment
        except Exception as e:
            logger.error(f"Ошибка при генерации комментария к посту: {e}")
            return None

    async def prepare_conversation_history(
        self,
        session: AsyncSession,
        post_message_id: int,
        original_post_content: str
    ) -> Optional[str]:
        """
        Подготавливает полную историю комментариев к посту для отправки в ИИ.
        
        Формат:
        1. В телеграм канале был опубликован пост - [текст поста]
        2. Бот прокомментировал этот пост - [текст первого комментария бота]
        3. Пользователь [id] ответил [тип контента], содержащим следующую информацию - [контент]
        4. ... (и так далее для каждого комментария)
        
        :param session: Сессия БД
        :param post_message_id: ID поста в канале
        :param original_post_content: Полный контент оригинального поста
        :return: Сформированная история комментариев или None при ошибке
        """
        try:
            from app.infrastructure.db.repositories import PostCommentRepository
            from app.infrastructure.db.models import PostComment
            
            # Получаем все комментарии к посту (последние MAX_COMMENTS_IN_HISTORY)
            comments = await PostCommentRepository.get_by_post_message_id(
                session, post_message_id, limit=MAX_COMMENTS_IN_HISTORY
            )
            
            if not comments:
                logger.warning(f"Не найдено комментариев для поста {post_message_id}")
                return None
            
            # Начинаем формировать историю
            history_parts = [
                f"1. В телеграм канале был опубликован пост - {original_post_content}"
            ]
            
            # Находим первый комментарий бота
            bot_comment = await PostCommentRepository.get_bot_comment_by_post(session, post_message_id)
            if bot_comment:
                history_parts.append(f"2. Бот прокомментировал этот пост - {bot_comment.content}")
                comment_number = 3
            else:
                comment_number = 2
            
            # Добавляем комментарии пользователей
            user_comments = [c for c in comments if not c.is_bot_comment]  # Только комментарии пользователей
            
            # Если нет комментариев пользователей, возвращаем None (будет использован старый формат)
            if not user_comments:
                logger.debug(f"Нет комментариев пользователей для поста {post_message_id}, используем старый формат")
                return None
            
            for idx, comment in enumerate(user_comments):
                # Определяем тип контента
                content_type_desc = comment.content_type or "текстом"
                if content_type_desc == "photo":
                    content_type_desc = "фото с подписью"
                elif content_type_desc == "document":
                    content_type_desc = "документом"
                elif content_type_desc == "pdf":
                    content_type_desc = "PDF документом"
                elif content_type_desc in ["voice", "audio"]:
                    content_type_desc = "звуковым файлом"
                else:
                    content_type_desc = "текстом"
                
                user_id_str = str(comment.user_id) if comment.user_id else "неизвестный пользователь"
                
                # Последний комментарий помечаем специально
                is_last = (idx == len(user_comments) - 1)
                if is_last:
                    history_parts.append(
                        f"{comment_number}. [ПОСЛЕДНИЙ КОММЕНТАРИЙ - ОТВЕТЬТЕ НА ЭТОТ] Пользователь {user_id_str} ответил {content_type_desc}, "
                        f"содержащим следующую информацию - {comment.content}"
                    )
                else:
                    history_parts.append(
                        f"{comment_number}. Пользователь {user_id_str} ответил {content_type_desc}, "
                        f"содержащим следующую информацию - {comment.content}"
                    )
                comment_number += 1
            
            # Добавляем финальную инструкцию
            if user_comments:
                history_parts.append(
                    "\nВАЖНО: Вы должны ответить ТОЛЬКО на последний комментарий (помечен как '[ПОСЛЕДНИЙ КОММЕНТАРИЙ - ОТВЕТЬТЕ НА ЭТОТ]'), "
                    "но учитывайте весь контекст предыдущих комментариев для более полного и релевантного ответа."
                )
            
            result = "\n\n".join(history_parts)
            logger.info(f"Подготовлена история комментариев для поста {post_message_id}: {len(comments)} комментариев, из них {len(user_comments)} от пользователей")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке истории комментариев: {e}", exc_info=True)
            return None

    async def generate_reply_to_comment(
        self,
        user_comment: str,
        original_post_content: Optional[str] = None,
        conversation_history: Optional[str] = None,
        chat_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Генерирует ответ на комментарий пользователя.

        :param user_comment: Комментарий пользователя
        :param original_post_content: Содержимое оригинального поста (для контекста, используется если нет conversation_history)
        :param conversation_history: Полная история комментариев к посту (приоритет над user_comment и original_post_content)
        :param chat_id: ID чата для истории разговора (опционально)
        :return: Сгенерированный ответ или None при ошибке
        """
        try:
            # Формируем контекст для ответа
            if conversation_history:
                # Используем полную историю комментариев
                user_message = conversation_history
            else:
                # Используем старый формат (для обратной совместимости)
                user_message = user_comment
                if original_post_content:
                    user_message = f"Пост: {original_post_content}\n\nКомментарий пользователя: {user_comment}"

            messages = [
                {"role": "system", "content": REPLY_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=300,  # Более короткие ответы на комментарии
                temperature=0.7,
            )

            reply = response.choices[0].message.content

            # Сохраняем в историю с ограничениями
            if chat_id:
                self._manage_conversation_history(chat_id)
                if chat_id not in self.conversation_history:
                    self.conversation_history[chat_id] = []
                self.conversation_history[chat_id].append({"role": "user", "content": user_comment})
                self.conversation_history[chat_id].append({"role": "assistant", "content": reply})
                # Ограничиваем количество сообщений в истории
                if len(self.conversation_history[chat_id]) > MAX_MESSAGES_PER_CHAT * 2:  # *2 т.к. user + assistant
                    self.conversation_history[chat_id] = self.conversation_history[chat_id][-MAX_MESSAGES_PER_CHAT * 2:]

            return reply
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа на комментарий: {e}")
            return None

    def _manage_conversation_history(self, chat_id: int):
        """
        Управляет историей разговоров: ограничивает количество чатов и очищает старые.
        
        :param chat_id: ID текущего чата
        """
        # Если превышен лимит чатов, удаляем самый старый (FIFO)
        if len(self.conversation_history) >= MAX_CONVERSATION_HISTORY_CHATS:
            if chat_id not in self.conversation_history:
                # Удаляем первый (самый старый) чат
                oldest_chat_id = next(iter(self.conversation_history))
                del self.conversation_history[oldest_chat_id]
                logger.debug(f"Удалена история для чата {oldest_chat_id} (превышен лимит {MAX_CONVERSATION_HISTORY_CHATS} чатов)")

    def clear_history(self, chat_id: int):
        """
        Очищает историю разговора для конкретного чата.

        :param chat_id: ID чата
        """
        if chat_id in self.conversation_history:
            del self.conversation_history[chat_id]

    def clear_all_history(self):
        """Очищает всю историю разговоров."""
        self.conversation_history.clear()
